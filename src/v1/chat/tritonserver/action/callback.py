import asyncio
from typing import List, Union
from tritonclient.grpc import InferenceServerClient, InferInput, InferRequestedOutput


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
        self._stop: List[str] = []

    async def get_queue(self):
        """Returns the response queue for async processing."""
        return self.response_queue

    def is_completed(self):
        """Checks if streaming process is completed."""
        return self.completed

    def set_stop(self, stop: List[str]):
        """Set the stop sequences for the callback."""
        self._stop = stop

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

            # Get the output tensor named "text_output"
            output_tensor_text = result.as_numpy("text_output")
            is_empty_text = output_tensor_text is None
            is_empty_text = is_empty_text or len(output_tensor_text) == 0
            is_empty_text = is_empty_text or (len(self._received_chunks) > 0
                                              and output_tensor_text[0] == b'')
            if is_empty_text:
                # Close streaming on empty byte string
                self.completed = True
                self.response_queue.put_nowait(None)
                return

            # - Decode the output tensor to a string
            response_text = [txt.decode("utf-8", errors="replace")
                             for txt in output_tensor_text if isinstance(txt, bytes)]
            response_text = "".join(response_text)


            # - Add to our accumulated chunks if we're collecting a complete response
            if len(self._received_chunks) < self._max_queue_size:
                self._received_chunks.append(response_text)

            # - Put the chunk in the queue for immediate processing
            self.response_queue.put_nowait(response_text)

            # - Check for stop sequences
            if self._stop and any(stop in response_text for stop in self._stop):
                self.completed = True
                return

        except Exception as e:
            self.error = f"Error processing response: {str(e)}"
            self.completed = True
            self.response_queue.put_nowait(None)
