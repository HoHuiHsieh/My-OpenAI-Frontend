"""
Stream processing utilities for Triton Inference Server responses.
This module provides shared functionality for handling streaming responses,
token processing, and error handling.
"""

import time
import traceback
import uuid
import asyncio
import re
from typing import List, Optional, Callable, Tuple, Dict, Any, AsyncGenerator, Union
from logger import get_logger
import tritonclient.grpc as grpcclient
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

# Set up logger for this module
logger = get_logger(__name__)


class StreamingResponseCallback:
    """
    Callback class for handling streaming responses from Triton Inference Server.
    This class manages the response queue and error handling.
    """

    def __init__(self):
        self.response_queue = asyncio.Queue()
        self.error = None
        self.completed = False
        self._received_chunks = []
        self._max_queue_size = 100  # Prevent memory issues with very large responses

    async def get_queue(self):
        """Returns the response queue for async processing."""
        return self.response_queue

    def is_completed(self):
        """Checks if streaming process is completed."""
        return self.completed

    def reset(self):
        """Reset the callback state for reuse."""
        self.error = None
        self.completed = False
        self._received_chunks = []
        # Create a new queue to avoid any leftover items
        self.response_queue = asyncio.Queue()

    def get_collected_response(self):
        """Returns the combined text from all received chunks."""
        return "".join(self._received_chunks) if self._received_chunks else ""

    def __call__(self, result, error):
        """Callback method invoked by Triton client when data is received."""
        if error:
            self.error = error
            self.completed = True
            # Signal completion with error
            self.response_queue.put_nowait(None)
            return

        try:
            # Extract the output tensor data
            if result is None:
                print("Received None result, signaling completion")
                self.completed = True
                # End of stream signal
                self.response_queue.put_nowait("".join(self._received_chunks))
                return

            # Get the output tensor named "text_output"
            output_tensor_text = result.as_numpy("text_output")
            if output_tensor_text is None or len(output_tensor_text) == 0 or (len(self._received_chunks) > 0 and output_tensor_text[0] == b''):
                # Close streaming on empty byte string
                self.completed = True
                self.response_queue.put_nowait(None)
                return
            
            # - Decode the output tensor to a string
            response_text = [txt.decode("utf-8", errors="replace") for txt in output_tensor_text if isinstance(txt, bytes)]
            response_text = "".join(response_text)

            # - Add to our accumulated chunks if we're collecting a complete response
            if len(self._received_chunks) < self._max_queue_size:
                self._received_chunks.append(response_text)

            # - Put the chunk in the queue for immediate processing
            self.response_queue.put_nowait(response_text)

        except Exception as e:
            self.error = f"Error processing response: {str(e)}"
            self.completed = True
            self.response_queue.put_nowait(None)


def get_token_from_text(text: str) -> Optional[Tuple[int, str]]:
    """
    Find a token number from input text with pattern: t'token_number'.
    If found, return the token number as an integer and any prefix text.
    If not found, return None.
    
    Args:
        text: The text to search for tokens
        
    Returns:
        Tuple of (token_number, prefix_text) or (None, None) if not found
    """
    try:
        # Find the token number in the text using the specified encoding
        match = re.search(r"t'(\d+)'", text)
        if match:
            # If the string contains text before the token pattern, extract and add it
            start_match = re.search(r"^(.*?)t'\d+'", text)
            prefix_text = ""
            if start_match and start_match.group(1):
                prefix_text = start_match.group(1)
            return int(match.group(1)), prefix_text
        else:
            return None, None
    except (IndexError, ValueError):
        # If the format is incorrect or conversion fails, return None
        return None, None


async def setup_triton_stream(
        triton_client: grpcclient.InferenceServerClient,
        model_name: str,
        inputs: List[grpcclient.InferInput],
        outputs: List[grpcclient.InferRequestedOutput],
        request_id=None
) -> StreamingResponseCallback:
    """
    Set up a stream with Triton client and start inference.

    This helper function handles the common stream setup logic for both streaming and non-streaming cases.

    Args:
        triton_client: The Triton client
        model_name: Name of the model
        inputs: The prepared inputs for Triton
        outputs: The requested outputs from Triton
        request_id: Optional request ID (defaults to a new UUID)

    Returns:
        A StreamingResponseCallback that can be used to collect responses
    """
    stream_callback = StreamingResponseCallback()
    stream_callback.reset()

    try:
        triton_client.start_stream(callback=stream_callback)
        triton_client.async_stream_infer(
            model_name=model_name,
            inputs=inputs,
            outputs=outputs,
            request_id=request_id or str(uuid.uuid4())
        )
        return stream_callback
    except Exception as e:
        triton_client.stop_stream()
        logger.error(f"Failed to start streaming: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process streaming request: {str(e)}"
        )


class StreamProcessor:
    """
    Base class for processing streams from Triton Inference Server.
    This class handles common functionality for both collecting and streaming responses.
    """
    
    def __init__(
        self,
        stream_callback: StreamingResponseCallback,
        triton_client: grpcclient.InferenceServerClient,
        tokenizor_client: grpcclient.InferenceServerClient,
        timeout: int = 300,
        stop_dict: List[str] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None
    ):
        """
        Initialize the stream processor.
        
        Args:
            stream_callback: The callback for handling streaming responses
            triton_client: The Triton client
            tokenizor_client: Client for tokenizing and detokenizing tokens
            timeout: Maximum time to wait for response completion
            stop_dict: List of stop sequences that signal the end of generation
            max_tokens: Maximum number of tokens to generate
            request_id: The ID of the request for tracking
        """
        self.stream_callback = stream_callback
        self.triton_client = triton_client
        self.tokenizor_client = tokenizor_client
        self.timeout = timeout
        self.stop_dict = stop_dict or []
        self.max_tokens = max_tokens
        self.request_id = request_id
        self.tokenizor = tokenizor_client.get_client().tokenizor
        self.accumulated_content = ""
        
        # Ensure stop_dict is properly formatted
        if isinstance(self.stop_dict, str):
            self.stop_dict = [self.stop_dict]
        if not isinstance(self.stop_dict, list):
            self.stop_dict = []
    
    async def _process_token(self, current_word: str, tokens_buffer: List[int], prefix_buffer: List[str] = None) -> Tuple[str, bool]:
        """
        Process a token, handling incomplete UTF-8 characters.
        
        Args:
            current_word: The current word/token to process
            tokens_buffer: Buffer to store incomplete tokens
            prefix_buffer: Buffer to store prefixes (for streaming only)
            
        Returns:
            Tuple of (processed_word, is_buffered)
        """
        # Check if current_word might contain an incomplete UTF-8 character
        token, prefix = get_token_from_text(current_word)
        
        if token is not None:
            logger.debug(f"Found incomplete UTF-8 character, buffering: {repr(current_word)}")
            tokens_buffer.append(token)
            
            # If prefix_buffer is provided, store prefix there
            if prefix and prefix_buffer is not None:
                prefix_buffer.append(prefix)
            
            return prefix if prefix else "", True
        
        # If we have buffered tokens, decode them
        elif len(tokens_buffer) > 0:
            processed_word = ""
            
            # Handle prefix for streaming case
            if prefix_buffer and len(prefix_buffer) > 0:
                processed_word = prefix_buffer.pop(0)
            
            # Add the tokenized output
            processed_word += self.tokenizor(tokens_buffer)
            
            # Clear the buffer
            tokens_buffer.clear()
            return processed_word, False
        
        # Return the word as is
        return current_word, False
    
    async def _wait_for_chunk(self, response_queue, start_time: float, count: int) -> Tuple[Optional[str], bool]:
        """
        Wait for the next chunk from the response queue with timeout handling.
        
        Args:
            response_queue: The queue to get chunks from
            start_time: The start time of processing
            count: Current token count
            
        Returns:
            Tuple of (current_word, should_break)
        """
        # Check if we've reached max tokens
        if self.max_tokens is not None and count >= self.max_tokens:
            logger.info(f"Reached max_tokens limit: {self.max_tokens}, stopping stream")
            return None, True
        
        try:
            # Check accumulated_content include stop sequences
            if self.stop_dict and any(stop in self.accumulated_content for stop in self.stop_dict):
                logger.debug(f"Detected stop sequence in accumulated content, stopped by {self.stop_dict}")
                return None, True
            
            # Wait for the next chunk with a timeout
            current_word = await asyncio.wait_for(response_queue.get(), 1.0)
            
            # Check for stop conditions
            if current_word is None:
                return None, True
            
            # Add the current word to accumulated content
            self.accumulated_content += current_word
                
            return current_word, False
            
        except asyncio.TimeoutError:
            # Check if streaming is completed
            if self.stream_callback.is_completed():
                response_queue.task_done()
                return None, True
                
            # Log warning if waiting too long
            if time.time() - start_time > self.timeout / 2:
                logger.warning(f"Still waiting for response after {time.time() - start_time:.1f}s")
            
            # Return a special value for timeout
            return None, False
    
    def cleanup_resources(self):
        """
        Clean up resources used by the stream processor.
        This safely closes all client connections to prevent resource leaks.
        """
        # Close triton_client
        if hasattr(self, 'triton_client') and self.triton_client:
            try:
                # Stop the stream first if it's running
                self.triton_client.stop_stream()
                logger.debug("Stopped stream for triton_client")
            except Exception as e:
                logger.debug(f"Error stopping stream for triton_client: {e}")
                
            try:
                # Then close the client connection
                self.triton_client.close()
                logger.debug("Closed triton_client connection")
            except Exception as e:
                logger.debug(f"Error closing triton_client connection: {e}")
                
        # Close tokenizor_client
        if hasattr(self, 'tokenizor_client') and self.tokenizor_client:
            try:
                # Only need to close this client, no stream to stop
                self.tokenizor_client.close()
                logger.debug("Closed tokenizor_client connection")
            except Exception as e:
                logger.debug(f"Error closing tokenizor_client connection: {e}")
                
        # Set clients to None to help garbage collection
        self.triton_client = None
        self.tokenizor_client = None
