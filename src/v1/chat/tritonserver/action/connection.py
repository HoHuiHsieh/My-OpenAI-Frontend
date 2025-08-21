import asyncio
import uuid
import numpy as np
from functools import partial
from typing import List, Union
from tritonclient.utils import InferenceServerException
from tritonclient.grpc import InferenceServerClient, InferInput, InferRequestedOutput
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from logger import get_logger
from .callback import StreamingResponseCallback


# Set up logger for this module
logger = get_logger(__name__)


class TritonClient:
    def __init__(self, host: str, port: int, api_key: str):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.client: InferenceServerClient = None
        # self.text_input: str = None
        # self.encoded_files: bytes = None
        self.inputs: List[InferInput] = []
        self.outputs: List[InferRequestedOutput] = []
        # self.model_type: str = None  # Model type to determine capabilities
        self.stream_callback: StreamingResponseCallback = StreamingResponseCallback()

    @property
    def url(self):
        return f"{self.host}:{self.port}"

    def get_client(self) -> 'TritonClient':
        """
        Create a gRPC client for the Triton server.
        """
        # Create a gRPC client for Triton server
        url = self.url
        client = InferenceServerClient(url=url, verbose=False)

        # Check if the server is ready
        if not client.is_server_ready():
            logger.error(f"Triton server at {url} is not ready")
            raise InferenceServerException(
                f"Triton server at {url} is not ready"
            )

        self.client = client
        logger.info(f"Connected to Triton server at {url}")
        return self

    def set_input(self,
                  input_name: str,
                  input_data: List[Union[str, int, float, bool]],
                  input_type: str,
                  input_size: List[int] = None
                  ) -> 'TritonClient':
        """
        Set the input data for the Triton inference request.

        Args:
            input_name (str): Name of the input tensor.
            input_data (List[str]): List of input strings to be encoded.
        """
        # Prepare inputs to the format expected by Triton
        if not isinstance(input_data, list):
            raise ValueError("Input data must be a list")
        if not input_data:
            raise ValueError("Input data cannot be empty")

        # Check for empty input
        if input_size is None:
            input_size = list(np.shape([input_data]))

        # Reshape input data if necessary
        input_data = np.reshape(input_data, input_size)

        # Determine input type based on the first element
        if input_type == "BYTES":
            input_data_buffer = np.array(input_data, dtype=np.object_)
        elif input_type == "INT32":
            input_data_buffer = np.array(input_data, dtype=np.int32)
        elif input_type == "UINT64":
            input_data_buffer = np.array(input_data, dtype=np.uint64)
        elif input_type == "FP32" :
            input_data_buffer = np.array(input_data, dtype=np.float32)
        elif input_type == "BOOL":
            input_data_buffer = np.array(input_data, dtype=np.bool_)
        else:
            raise ValueError(
                "Unsupported input data type. Must be str, int, or float.")

        # Create InferInput object
        input = InferInput(input_name, input_size, input_type)
        input.set_data_from_numpy(input_data_buffer)
        self.inputs.append(input)
        return self

    def set_output(self, output_name: str) -> 'TritonClient':
        """
        Set the output tensor for the Triton inference request.

        Args:
            output_name (str): Name of the output tensor.
        """
        # Create InferRequestedOutput object
        output = InferRequestedOutput(output_name)
        self.outputs.append(output)
        return self

    async def infer(self, model_name: str, request_id:str = "") -> str:
        """
        Perform inference on the Triton server with the prepared inputs and outputs.
        This method is designed to be used with asynchronous streaming responses.
        It uses a callback to handle the streaming response.
        """
        result_output = []
        error_occurred = None

        def callback(stream_callback, result, error):
            """
            Callback function to handle the streaming response.
            """
            nonlocal result_output, error_occurred
            if error:
                logger.error(f"Error during inference: {error}")
                error_occurred = error
            else:
                try:
                    result_data = result.as_numpy("text_output")
                    output = result_data[0].decode('utf-8') if result_data is not None and len(result_data) > 0 else ""
                    logger.debug(f"Received result: {output}")
                    result_output.append(output)
                except Exception as e:
                    logger.error(f"Error processing result: {e}")
                    error_occurred = e

        logger.debug(f"Starting inference for model {model_name}")

        # Reset the stream callback to ensure it starts fresh
        self.stream_callback.reset()

        # Start the streaming response
        self.client.start_stream(
            callback=partial(callback, self.stream_callback),   
            stream_timeout=60
        )
        
        # Perform the inference request
        self.client.async_stream_infer(
            model_name=model_name,
            inputs=self.inputs,
            outputs=self.outputs,
            request_id=request_id or uuid.uuid4().hex[:8]
        )

        # Wait for the streaming to complete
        timeout = 60
        start_time = asyncio.get_event_loop().time()
        
        while not result_output and not error_occurred:
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.client.stop_stream()
                raise InferenceServerException("Inference timeout")
            await asyncio.sleep(0.02)

        self.client.stop_stream()

        if error_occurred:
            raise InferenceServerException(f"Error during inference: {error_occurred}")

        return "".join(result_output) 


    async def async_infer(self, model_name: str, request_id: str = "") -> StreamingResponseCallback:
        """
        Perform asynchronous inference on the Triton server with the prepared inputs and outputs.
        This method starts streaming inference and returns immediately, allowing access to the stream callback.
        """
        logger.debug(f"Starting async inference for model {model_name}")

        # Reset the stream callback to ensure it starts fresh
        self.stream_callback.reset()

        # Start the streaming response
        self.client.start_stream(
            callback=self.stream_callback,
            stream_timeout=60
        )
        
        # Perform the inference request
        self.client.async_stream_infer(
            model_name=model_name,
            inputs=self.inputs,
            outputs=self.outputs,
            request_id=request_id or uuid.uuid4().hex[:8]
        )

        logger.debug(f"Async inference started for model {model_name}")

        return self.stream_callback
