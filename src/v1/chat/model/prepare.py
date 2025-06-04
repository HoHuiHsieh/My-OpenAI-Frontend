"""Prepare Triton inputs for chat model inference."""
import time
from typing import List, Optional
import numpy as np
import tritonclient.grpc as grpcclient
from ..typedef import CreateChatCompletionRequest
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def prepare_triton_inputs(
        body: CreateChatCompletionRequest,
        text_input: str,
        encoded_files: bytes = None
) -> List[grpcclient.InferInput]:
    """
    Prepare Triton inputs based on the request body.

    Args:
        body: The request body
        text_input: The input text data as a string
        encoded_files: Optional encoded file data for vision models

    Returns:
        A list of prepared inputs for Triton
    """
    inputs = []

    input_data_bytes = text_input.encode('utf-8')
    buf = grpcclient.InferInput("text_input", [1, 1], "BYTES")
    buf.set_data_from_numpy(np.array([[input_data_bytes]], dtype=np.object_))
    inputs.append(buf)

    # Add encoded file inputs if provided
    if encoded_files:
        # Pack all file data into a single array for the model
        encoded_file_data = []
        for file_info in encoded_files:
            encoded_file_data.append(file_info["data"].encode(
                'utf-8') if isinstance(file_info["data"], str) else file_info["data"])

        if encoded_file_data:
            buf = grpcclient.InferInput(
                "encoded_files", [len(encoded_file_data), 1], "BYTES")
            buf.set_data_from_numpy(
                np.array([encoded_file_data], dtype=np.object_))
            inputs.append(buf)

    max_tokens = 1024  # Default value
    if hasattr(body, 'max_completion_tokens') and isinstance(body.max_completion_tokens, int) and body.max_completion_tokens > 0:
        max_tokens = body.max_completion_tokens
    buf = grpcclient.InferInput("max_tokens", [1, 1], "INT32")
    buf.set_data_from_numpy(np.array([[max_tokens]], dtype=np.int32))
    inputs.append(buf)

    # Handle stop sequences
    stop_sequences_bytes = []
    if hasattr(body, 'stop') and body.stop:
        if isinstance(body.stop, str):
            stop_sequences_bytes = [body.stop.encode('utf-8')]
        elif isinstance(body.stop, list):
            stop_sequences_bytes = [s.encode('utf-8') for s in body.stop]
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


def prepare_triton_inputs_with_seed(
        body: CreateChatCompletionRequest,
        text_input: str,
        seed: int,
        encoded_files=None
):
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
    inputs = prepare_triton_inputs(body, text_input, encoded_files)

    # Override the random seed with the specified value
    for inp in inputs:
        if inp.name() == "random_seed":
            inp.set_data_from_numpy(np.array([[seed]], dtype=np.uint64))
            break

    return inputs
