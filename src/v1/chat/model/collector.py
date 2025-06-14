"""
Stream collection utilities for Triton Inference Server.
This module handles collecting complete responses from the streaming server.
"""

import time
import traceback
from typing import List, Optional
from logger import get_logger
import tritonclient.grpc as grpcclient
from .stream_processor import StreamingResponseCallback, StreamProcessor

# Set up logger for this module
logger = get_logger(__name__)


class StreamCollector(StreamProcessor):
    """
    Collector for streaming responses from Triton Inference Server.
    This class collects all chunks from a stream and returns a complete text response.
    """
    
    def __init__(
        self,
        stream_callback: StreamingResponseCallback,
        triton_client: grpcclient.InferenceServerClient,
        tokenizor_client: grpcclient.InferenceServerClient,
        timeout: int = 60,
        stop_dict: List[str] = None,
        max_tokens: Optional[int] = None,
        request_id: Optional[str] = None
    ):
        """
        Initialize the stream collector.
        
        Args:
            stream_callback: The callback for handling streaming responses
            triton_client: The Triton client
            tokenizor_client: Client for tokenizing and detokenizing tokens
            timeout: Maximum time to wait for response completion
            stop_dict: List of stop sequences that signal the end of generation
            max_tokens: Maximum number of tokens to generate
            request_id: The ID of the request for tracking
        """
        super().__init__(
            stream_callback=stream_callback,
            triton_client=triton_client,
            tokenizor_client=tokenizor_client,
            timeout=timeout,
            stop_dict=stop_dict,
            max_tokens=max_tokens
        )
        self.request_id = request_id
    
    async def collect(self) -> Optional[str]:
        """
        Collect all chunks from the streaming response and return the complete text.
        
        Returns:
            The complete text response or None on error
        """
        complete_text = []
        start_time = time.time()
        tokens_buffer = []  # Buffer for incomplete UTF-8 characters

        try:
            response_queue = await self.stream_callback.get_queue()
            count = 0

            while time.time() - start_time < self.timeout:
                # Get the next chunk
                current_word, should_break = await self._wait_for_chunk(response_queue, start_time, count)
                
                # Break if indicated (max tokens reached, stop sequence, etc.)
                if should_break:
                    break
                    
                # Skip if timeout occurred
                if current_word is None:
                    continue
                
                # Process the token
                processed_word, is_buffered = await self._process_token(current_word, tokens_buffer)
                
                # If we got a processed word (not just buffered), add it to the response
                if processed_word:
                    complete_text.append(processed_word)
                
                # Increment token count
                count += 1

            # Check for timeout
            if not complete_text and time.time() - start_time >= self.timeout:
                logger.warning(f"Response collection timed out after {self.timeout}s")

            # Check for errors
            if self.stream_callback.error:
                logger.error(f"Error collecting stream response: {self.stream_callback.error}")
                return None

            # Return the combined text
            return "".join(complete_text) or self.stream_callback.get_collected_response()

        except Exception as e:
            logger.error(f"Error in collect_stream_response: {str(e)}\n{traceback.format_exc()}")
            return None
            
        finally:
            self.cleanup_resources()


async def collect_stream_response(
    stream_callback: StreamingResponseCallback,
    triton_client: grpcclient.InferenceServerClient,
    tokenizor_client: grpcclient.InferenceServerClient,
    timeout=60,
    stop_dict=[],
    max_tokens: Optional[int] = None,
    request_id: Optional[str] = None
) -> Optional[str]:
    """
    Collects all chunks from a streaming response and returns the complete text.
    
    This function maintains backward compatibility with the original API.

    Args:
        stream_callback: The StreamingResponseCallback instance
        triton_client: The Triton inference client
        tokenizor_client: Client for tokenization
        timeout: Maximum seconds to wait for response
        stop_dict: List of stop sequences
        max_tokens: Maximum number of tokens to generate
        request_id: The ID of the request to use for tracking

    Returns:
        The complete text response or None on error
    """
    collector = StreamCollector(
        stream_callback=stream_callback,
        triton_client=triton_client,
        tokenizor_client=tokenizor_client,
        timeout=timeout,
        stop_dict=stop_dict,
        max_tokens=max_tokens,
        request_id=request_id
    )
    
    try:
        return await collector.collect()
    except Exception as e:
        logger.error(f"Error in collect_stream_response: {e}")
        # Ensure resources are cleaned up even if an error occurs
        collector.cleanup_resources()
        return None
