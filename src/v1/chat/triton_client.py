"""Triton client interactions for chat completions."""
import asyncio
import time
import uuid
import traceback
import numpy as np
from typing import List, Optional, Any, Tuple, Dict

import tritonclient.grpc as grpcclient
from tritonclient.utils import InferenceServerException
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from logger import get_logger

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
                self.completed = True
                # End of stream signal
                self.response_queue.put_nowait("".join(self._received_chunks))
                return

            output_tensor = result.as_numpy("text_output")
            if output_tensor is None or output_tensor[0] == b'':
                # Close streaming on empty byte string
                self.completed = True
                self.response_queue.put_nowait(None)
                return

            # prompt_tokens_tensor = result.as_numpy("prompt_tokens")
            # print(prompt_tokens_tensor[0])

            # Process the output tensor data
            response_text = str(output_tensor[0].decode(
                "utf-8", errors="replace"))

            # Add to our accumulated chunks if we're collecting a complete response
            if len(self._received_chunks) < self._max_queue_size:
                self._received_chunks.append(response_text)

            # Put the chunk in the queue for immediate processing
            self.response_queue.put_nowait(response_text)

        except Exception as e:
            self.error = f"Error processing response: {str(e)}"
            self.completed = True
            self.response_queue.put_nowait(None)


def prepare_triton_inputs(body, input_data_bytes, encoded_files=None):
    """
    Prepare Triton inputs based on the request body.
    
    Args:
        body: The request body
        input_data_bytes: The input data bytes
        encoded_files: Optional list of encoded file data for vision models
        
    Returns:
        A list of prepared inputs for Triton
    """
    inputs = []

    buf = grpcclient.InferInput("text_input", [1, 1], "BYTES")
    buf.set_data_from_numpy(np.array([[input_data_bytes]], dtype=np.object_))
    inputs.append(buf)
    
    # Add encoded file inputs if provided
    if encoded_files:
        # Pack all file data into a single array for the model
        encoded_file_data = []
        for file_info in encoded_files:
            encoded_file_data.append(file_info["data"].encode('utf-8') if isinstance(file_info["data"], str) else file_info["data"])
            
        if encoded_file_data:
            buf = grpcclient.InferInput("encoded_files", [len(encoded_file_data), 1], "BYTES")
            buf.set_data_from_numpy(np.array([encoded_file_data], dtype=np.object_))
            inputs.append(buf)

    max_tokens = body.max_completion_tokens or 1024
    buf = grpcclient.InferInput("max_tokens", [1, 1], "INT32")
    buf.set_data_from_numpy(np.array([[max_tokens]], dtype=np.int32))
    inputs.append(buf)

    stop_sequences_bytes = [s.encode('utf-8') for s in (
        body.stop if isinstance(body.stop, list) else [body.stop])] if body.stop else []
    if stop_sequences_bytes:
        buf = grpcclient.InferInput(
            "stop_words", [1, len(stop_sequences_bytes)], "BYTES")
        buf.set_data_from_numpy(
            np.array([stop_sequences_bytes], dtype=np.object_))
        inputs.append(buf)

    for param, dtype, bounds in [("top_p", "FP32", (0.0, 1.0)), ("temperature", "FP32", (0.0, 2.0)),
                                 ("presence_penalty", "FP32", (-2.0, 2.0)), ("frequency_penalty", "FP32", (-2.0, 2.0))]:
        value = max(bounds[0], min(
            float(getattr(body, param, 0.0) or 0.0), bounds[1]))
        buf = grpcclient.InferInput(param, [1, 1], dtype)
        buf.set_data_from_numpy(np.array([[value]], dtype=np.float32))
        inputs.append(buf)

    buf = grpcclient.InferInput("random_seed", [1, 1], "UINT64")
    buf.set_data_from_numpy(np.array([[int(time.time())]], dtype=np.uint64))
    inputs.append(buf)

    buf = grpcclient.InferInput("stream", [1, 1], "BOOL")
    buf.set_data_from_numpy(np.array([[True]], dtype=np.bool_))
    inputs.append(buf)

    return inputs


def prepare_triton_inputs_with_seed(body, input_data_bytes, seed, encoded_files=None):
    """
    Prepare Triton inputs based on the request body with a specified random seed.
    
    Args:
        body: The request body
        input_data_bytes: The input data bytes
        seed: The random seed to use
        encoded_files: Optional list of encoded file data for vision models
        
    Returns:
        A list of prepared inputs for Triton
    """
    inputs = prepare_triton_inputs(body, input_data_bytes, encoded_files)
    
    # Override the random seed with the specified value
    for inp in inputs:
        if inp.name() == "random_seed":
            inp.set_data_from_numpy(np.array([[seed]], dtype=np.uint64))
            break
            
    return inputs


async def _setup_triton_stream(triton_client, model_name, inputs, outputs, request_id=None):
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


async def collect_stream_response(stream_callback, triton_client, timeout=60):
    """
    Collects all chunks from a streaming response and returns the complete text.

    Args:
        stream_callback: The StreamingResponseCallback instance
        triton_client: The Triton inference client
        timeout: Maximum seconds to wait for response

    Returns:
        The complete text response or None on error
    """
    complete_text = []
    start_time = time.time()

    try:
        response_queue = await stream_callback.get_queue()

        while time.time() - start_time < timeout:
            try:
                text = await asyncio.wait_for(response_queue.get(), 1.0)
                if text is None:
                    break
                complete_text.append(text)
            except asyncio.TimeoutError:
                if stream_callback.is_completed():
                    break
                if time.time() - start_time > timeout / 2 and not complete_text:
                    logger.warning(
                        f"Still waiting for response after {time.time() - start_time:.1f}s")

        if not complete_text and time.time() - start_time >= timeout:
            logger.warning(f"Response collection timed out after {timeout}s")

        if stream_callback.error:
            logger.error(
                f"Error collecting stream response: {stream_callback.error}")
            return None

        return "".join(complete_text) or stream_callback.get_collected_response()

    except Exception as e:
        logger.error(
            f"Error in collect_stream_response: {str(e)}\n{traceback.format_exc()}")
        return None
    finally:
        try:
            triton_client.stop_stream()
        except Exception as e:
            logger.debug(f"Error stopping stream: {e}")


