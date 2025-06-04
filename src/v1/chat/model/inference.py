"""

"""

import time
import traceback
import uuid
import asyncio
import tritonclient.grpc as grpcclient
from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from typing import List
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


async def setup_triton_stream(
        triton_client: grpcclient.InferenceServerClient,
        model_name: str,
        inputs: List[grpcclient.InferInput],
        outputs: List[grpcclient.InferRequestedOutput],
        request_id=None
):
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


async def collect_stream_response(
        stream_callback: StreamingResponseCallback,
        triton_client: grpcclient.InferenceServerClient,
        timeout=60,
        stop_dict=[]
):
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
        if not isinstance(stop_dict, list):
            stop_dict = []

        response_queue = await stream_callback.get_queue()

        while time.time() - start_time < timeout:
            try:
                text: str = await asyncio.wait_for(response_queue.get(), 1.0)
                if text is None or text.strip() in stop_dict:
                    break
                complete_text.append(text)
            except asyncio.TimeoutError:
                if stream_callback.is_completed():
                    response_queue.task_done()
                    break
                if time.time() - start_time > timeout / 2 and not complete_text:
                    logger.warning(
                        f"Still waiting for response after {time.time() - start_time:.1f}s")

        if not complete_text and time.time() - start_time >= timeout:
            logger.warning(
                f"Response collection timed out after {timeout}s")

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
