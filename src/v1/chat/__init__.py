"""Chat API module."""
import traceback
from fastapi import FastAPI, HTTPException, Security, Request
from tritonclient.utils import InferenceServerException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN
from typing import Any
from logger import get_logger
from config import get_config
from oauth2 import get_current_active_user, User
from oauth2.scopes import chat_completion_scopes
from .typedef import CreateChatCompletionResponse, CreateChatCompletionRequest
from .model import TritonConnection


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)

app = FastAPI(
    title="Chat API",
    description="FastAPI application for chat endpoints",
    version="1.0.0"
)


@app.post("/completions", response_model=CreateChatCompletionResponse, summary="Creates a model response for the given chat conversation.")
async def chat_completion(
    request: Request,
    body: CreateChatCompletionRequest,
    current_user: User = Security(get_current_active_user)
):
    """
    Endpoint to create a chat completion.

    Args:
        request: The FastAPI request
        body: The request body containing the chat conversation parameters

    Returns:
        A response model containing the chat completion or a streaming response
    """
    logger.info(
        f"Received request for chat completion with model: {body.model}")
    
    try:
        # Extract the API key from the request headers
        api_key = request.headers.get("Authorization", "").split(" ")[-1] 

        # Modify the model name to match the Triton server configuration
        models_config = config.get("models", {})
        if not models_config:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No model servers configured in the system."
            )
        body.model = body.model.split("/")[-1]

        # Extract the model configuration from the loaded config
        model_config = models_config.get(body.model)
        if not model_config:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Model {body.model} is not configured in the system."
            )
        
        # Check if the user has permission to access this model
        if "admin" not in current_user.scopes:
            if not set(model_config.get('type', [])).intersection(current_user.scopes):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail=f"User {current_user.username} does not have required scopes for model {body.model}."
                )

        # Extract host and port from model configuration
        host = model_config.get("host", "localhost")
        port = model_config.get("port", 8001)
        logger.info(
            f"Connecting to model server at {host}:{port} for model {body.model}")

        # Check if this is a streaming request
        if body.stream:
            # For streaming with n>1, warn that only one completion will be streamed
            if body.n > 1:
                logger.warning("Streaming with n>1 is not fully supported; only the first completion will be streamed")
            # return await handle_streaming_response(triton_client, model_name, inputs, outputs, body.model, body, user_id=current_user.full_name,)
            return await TritonConnection.async_infer(
                host=host,
                port=port,
                body=body,
                user_id=current_user.id,
                api_key=api_key,
            )

        else:
            # return await handle_non_streaming_response(model_name, outputs, body, input_data_bytes, encoded_files, user_id=current_user.full_name)
            return await TritonConnection.infer(
                host=host,
                port=port,
                body=body,
                user_id=current_user.id,
                api_key=api_key,
            )

    except InferenceServerException as e:
        logger.error(f"Inference server error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference server error: {str(e)}"
        )
    except HTTPException as e:
        logger.error(f"HTTP error in chat completion: {str(e)}")
        # Re-raise HTTPException to preserve status code and detail
        raise e
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unexpected error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
