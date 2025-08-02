# -*- coding: utf-8 -*-
import traceback
import base64
import uuid
import numpy as np
from typing import List
import tritonclient.grpc as grpcclient
from tritonclient.utils import InferenceServerException
from logger import get_logger
from config import get_config
from .models import EmbeddingsRequest, EmbeddingsResponse, Usage, EmbeddingData
from .util import log_embeddings_usage


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration
try:
    config = get_config()
    embedding_models = config.get_models_by_type("embeddings:base")
except Exception as e:
    logger.error(f"Failed to load available models: {e}")
    raise RuntimeError("Configuration loading failed") from e


async def query_embeddings(data: EmbeddingsRequest, user_id=None) -> EmbeddingsResponse:
    """
    Query embeddings from the configured Triton server.
    """
    # Check if the model exists in the configuration
    # Get the last part of the model name
    model_name = data.model.split("/")[-1]
    target_model = embedding_models.get(model_name)
    if not target_model:
        logger.error(f"Model {data.model} not found in configuration")
        raise ValueError(f"Model {data.model} not found in configuration")

    # Prepare input data
    if not isinstance(data.input, list):
        text_input = [data.input]
    else:
        text_input = data.input

    # Prepare inputs to the format expected by Triton
    input_data_bytes = [t.encode('utf-8') for t in text_input]
    inputs: List[grpcclient.InferInput] = []
    buf = grpcclient.InferInput(
        "input_text", [1, len(input_data_bytes)], "BYTES")
    buf.set_data_from_numpy(np.array([input_data_bytes], dtype=np.object_))
    inputs.append(buf)

    logger.debug(
        f"Embeddings input={input_data_bytes}")

    # Prepare outputs to the format expected by Triton
    outputs = []
    outputs.append(grpcclient.InferRequestedOutput("embeddings"))
    outputs.append(grpcclient.InferRequestedOutput("prompt_tokens"))

    # Prepare Triton client
    host = target_model.host
    port = target_model.port
    triton_client = grpcclient.InferenceServerClient(
        url=f"{host}:{port}",
        verbose=False
    )

    logger.debug(
        f"Using gRPC model server at {host}:{port} for model {model_name}")
    
    # Prepare request ID for the inference
    request_id = f"req_{uuid.uuid4().hex}"

    # Send inference request
    response = triton_client.infer(
        model_name=model_name,
        inputs=inputs,
        outputs=outputs,
        request_id=request_id
    )
    logger.debug(
        f"Received response from Triton server at {host}:{port} for model {model_name}")

    # Extract the embedding data from the response
    embedding_data = response.as_numpy("embeddings")
    if embedding_data is None:
        logger.error(
            f"Failed to get embedding data from Triton server at {host}:{port} for model {model_name}")
        raise ValueError(
            f"Failed to get embedding data from Triton server for model {model_name}")

    # Verify embedding data format
    if not isinstance(embedding_data, np.ndarray):
        logger.error(
            f"Invalid embedding data format received from Triton server: {type(embedding_data)}")
        raise ValueError(
            f"Invalid embedding data format received from Triton server for model {model_name}")

    if embedding_data.dtype != np.float32:
        logger.warning(
            f"Unexpected embedding data type: {embedding_data.dtype}, expected np.float32. Attempting to convert.")
        try:
            embedding_data = embedding_data.astype(np.float32)
        except Exception as e:
            logger.error(f"Error converting embedding data type: {str(e)}")
            raise ValueError(
                f"Failed to convert embedding data type for model {model_name}") from e

    logger.debug(
        f"Embedding data shape: {embedding_data.shape}, type: {embedding_data.dtype}")

    # Store original embedding data for response construction
    embedding_data = embedding_data[0]

    # Convert the embedding data to base64 if requested
    if data.encoding_format == "base64":
        try:
            embedding_data = [base64.b64encode(b.tobytes()).decode(
                'utf-8') for b in embedding_data]
            logger.debug("Base64 encoded embedding data successfully")
        except Exception as e:
            logger.error(
                f"Error encoding embedding data to base64: {str(e)}")
            raise ValueError(
                f"Failed to encode embedding data to base64 for model {model_name}") from e

    # Compute usage
    prompt_tokens = response.as_numpy("prompt_tokens")[0]
    prompt_tokens = int(prompt_tokens)
    total_tokens = prompt_tokens

    # Prepare the response
    response_data = EmbeddingsResponse(
        object="list",
        data=[
            EmbeddingData(
                object="embedding",
                embedding=embed,
                index=i
            ) for i, embed in enumerate(embedding_data)
        ],
        model=data.model,
        usage=Usage(
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens
        )
    )

    # Usage logging
    log_embeddings_usage(
        request_id=request_id,
        user_id=user_id,
        model=data.model,
        input_count=len(text_input),
        prompt_tokens=prompt_tokens,
    )

    # Return with logging
    logger.info(
        f"Processed embedding request for model {data.model} with {prompt_tokens} prompt tokens and {total_tokens} total tokens")
    return response_data
