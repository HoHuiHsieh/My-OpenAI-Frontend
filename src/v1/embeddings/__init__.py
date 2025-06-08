# -*- coding: utf-8 -*-
import base64
import numpy as np
from typing import List
import tritonclient.grpc as grpcclient
from tritonclient.utils import InferenceServerException
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from .nv_embed_v2 import is_nv_embed_v2_model
from .typedef import CreateEmbeddingRequest, CreateEmbeddingResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from oauth2 import get_current_active_user, User, SecurityScopes
from config import get_config
from logger import get_logger, UsageLogger

# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)


# Define the FastAPI application
app = FastAPI(
    title="Embeddings API",
    description="FastAPI application for embeddings endpoints",
    version="1.0.0",
    # Disable automatic redirection for trailing slashes
    redirect_slashes=False
)


@app.post("/", response_model=CreateEmbeddingResponse, summary="Creates a model response for the given queries or passages.")
@app.post("", response_model=CreateEmbeddingResponse, summary="Creates a model response for the given queries or passages.")
async def embeddings(
    request: Request,
    body: CreateEmbeddingRequest,
    current_user: User = Security(
        get_current_active_user, scopes=["embeddings:read"])
) -> CreateEmbeddingResponse:
    """
    Endpoint to create embeddings by forwarding requests to a Triton Inference Server.

    Args:
        request: The incoming FastAPI request
        body: The request body containing the embedding parameters

    Returns:
        A response with embedding data from the model server

    Raises:
        HTTPException: If the model server fails to respond
    """
    logger.info(
        f"Received request for embeddings with model: {body.model}")

    try:
        # Get the model server configurations from the config
        models_config = config.get("models", {})
        if not models_config:
            logger.error("No model servers configured in the system.")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No model servers configured in the system."
            )

        # Get model configuration
        model_config = models_config.get(body.model)
        if not model_config:
            logger.warning(
                f"Model {body.model} is not configured in the system.")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Model {body.model} is not configured in the system."
            )

        # Get server details
        host = model_config.get("host", "localhost")
        port = model_config.get("port", 8001)  # Default gRPC port is 8001
        model_name = model_config.get("name", body.model)

        logger.info(
            f"Using gRPC model server at {host}:{port} for model {model_name}")

        # Prepare text_input from body.input
        # Process input based on model type
        if not isinstance(body.input, list):
            text_input = [body.input]
        else:
            text_input = body.input

        # Validate model support
        if not is_nv_embed_v2_model(body.model):
            logger.error(
                f"Model {body.model} is not supported for embeddings.")
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Model {body.model} is not supported for embeddings."
            )

        logger.debug(f"Using {body.model} for embedding generation.")

        # Log the formatted input (truncated for large prompts)
        truncated_input = ", ".join(
            [t[:100] + "..." if len(t) > 100 else t for t in text_input])[:1000]
        logger.debug(f"Formatted input for {body.model}: {truncated_input}")

        # Convert input data to the format expected by Triton
        input_data_bytes = [t.encode('utf-8') for t in text_input]

        # Set up gRPC client
        triton_client = grpcclient.InferenceServerClient(
            url=f"{host}:{port}",
            verbose=False
        )

        # Check server readiness
        if not triton_client.is_server_ready():
            logger.error(f"Triton gRPC server at {host}:{port} is not ready")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Model server is not ready"
            )

        # Prepare inputs for the model with improved type checking and error handling
        inputs: List[grpcclient.InferInput] = []

        # Add required text input (the formatted prompt)
        buf = grpcclient.InferInput("input_text", 
                                    [1, len(input_data_bytes)], "BYTES")
        buf.set_data_from_numpy(np.array([input_data_bytes], dtype=np.object_))
        inputs.append(buf)

        # Add optional input type (query or passage)
        input_type = None
        if body.type:
            input_type = body.type
            buf = grpcclient.InferInput("input_type", [1, 1], "BYTES")
            buf.set_data_from_numpy(np.array([[input_type]], dtype=np.object_))
            inputs.append(buf)

        # Log all the input parameters for debugging
        logger.debug(
            f"Model input parameters: input_text={truncated_input}, input_type={input_type}")

        # Prepare outputs
        outputs = []
        outputs.append(grpcclient.InferRequestedOutput("embeddings"))
        outputs.append(grpcclient.InferRequestedOutput("prompt_tokens"))

        # Perform inference
        logger.info(
            f"Sending request to Triton server at {host}:{port} for model {model_name}")
        response = triton_client.infer(
            model_name=model_name,
            inputs=inputs,
            outputs=outputs
        )
        logger.info(
            f"Received response from Triton server at {host}:{port} for model {model_name}")

        # Extract the embedding data from the response
        embedding_data = response.as_numpy("embeddings")
        if embedding_data is None:
            logger.error(
                f"Failed to get embedding data from Triton server at {host}:{port} for model {model_name}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get embedding data from model server"
            )

        # Verify embedding data format
        if not isinstance(embedding_data, np.ndarray):
            logger.error(
                f"Invalid embedding data format received from Triton server: {type(embedding_data)}")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid embedding data format"
            )

        if embedding_data.dtype != np.float32:
            logger.warning(
                f"Unexpected embedding data type: {embedding_data.dtype}, expected np.float32. Attempting to convert.")
            try:
                embedding_data = embedding_data.astype(np.float32)
            except Exception as e:
                logger.error(f"Error converting embedding data type: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Invalid embedding data type: {embedding_data.dtype}"
                )

        logger.debug(
            f"Embedding data shape: {embedding_data.shape}, type: {embedding_data.dtype}")

        # Store original embedding data for response construction
        embedding_data = embedding_data[0]

        # Convert the embedding data to base64 if requested
        if body.encoding_format == "base64":
            try:
                embedding_data = [base64.b64encode(b.tobytes()).decode('utf-8') for b in embedding_data]
                logger.debug("Base64 encoded embedding data successfully")
            except Exception as e:
                logger.error(
                    f"Error encoding embedding data to base64: {str(e)}")
                raise HTTPException(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error encoding embedding data to base64: {str(e)}"
                )

        # Calculate token usage (approximate, based on input length)
        # TODO: Implement a more accurate token counting mechanism
        prompt_tokens =  response.as_numpy("prompt_tokens")[0]
        input_token_count = prompt_tokens
        total_tokens = prompt_tokens

        # Create the response object with proper data structure
        response_data = CreateEmbeddingResponse(
            object="list",
            data=[
                {
                    "object": "embedding",
                    "embedding": emb,
                    "index": i
                } for i, emb in enumerate(embedding_data)
            ],
            model=model_name,
            usage={
                "prompt_tokens": input_token_count,
                "total_tokens": total_tokens
            }
        )

        # Log usage information for the current user
        UsageLogger.log_embeddings_usage(
            user_id=current_user.id,
            model=model_name,
            prompt_tokens=input_token_count,
            total_tokens=total_tokens,
            input_count=len(text_input),
            request_id=str(request.state.request_id) if hasattr(request.state, "request_id") else None,
            extra={"endpoint": "/v1/embeddings", "encoding_format": body.encoding_format}
        )

        # Log success (without logging the full response which could be large)
        logger.info(
            f"Successfully created embedding response for model {model_name}")
        return response_data

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        # Catch all other unexpected errors
        logger.error(
            f"Unexpected error in embeddings endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )
