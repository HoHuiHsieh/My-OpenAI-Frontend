"""Chat API module."""
import traceback
from fastapi import FastAPI, HTTPException, Security, Request
from tritonclient.utils import InferenceServerException
import tritonclient.grpc as grpcclient

from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST

from logger import get_logger
from config import get_config
from oauth2 import get_current_active_user, User
from .typedef import CreateChatCompletionResponse, CreateChatCompletionRequest
from .llama3 import is_llama3_model, format_messages_for_llama3
from .triton_client import prepare_triton_inputs
from .handle_streaming import handle_streaming_response
from .handle_non_streaming import handle_non_streaming_response
from .response_processing import process_triton_response


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)

app = FastAPI(
    title="Chat API",
    description="FastAPI application for chat endpoints",
    version="1.0.0"
)


@app.post("/completion", response_model=CreateChatCompletionResponse, summary="Creates a model response for the given chat conversation.")
async def chat_completion(
    request: Request,
    body: CreateChatCompletionRequest,
    current_user: User = Security(
        get_current_active_user, scopes=["chat:read"])
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
        models_config = config.get("models", {})
        if not models_config:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No model servers configured in the system."
            )

        model_config = models_config.get(body.model)
        if not model_config:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Model {body.model} is not configured in the system."
            )

        host, port, model_name = model_config.get("host", "localhost"), model_config.get(
            "port", 8001), model_config.get("name", body.model)
        logger.info(
            f"Using gRPC model server at {host}:{port} for model {model_name}")
            
        # Get model types from config to determine if vision is supported
        model_types = model_config.get("type", ["chat"])
        
        # Call formatter with model types to handle content based on capabilities
        format_result = format_messages_for_llama3(
            body.messages, body.tools, body.response_format, model_types) if is_llama3_model(body.model) else (None, None)
            
        if not format_result or not format_result[0]:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"No specific formatter defined for model {body.model}."
            )
            
        text_input, encoded_files = format_result
        input_data_bytes = text_input.encode('utf-8')
        triton_client = grpcclient.InferenceServerClient(
            url=f"{host}:{port}", verbose=False)

        if not triton_client.is_server_ready():
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Model server is not ready"
            )

        inputs = prepare_triton_inputs(body, input_data_bytes, encoded_files)
        outputs = [
            grpcclient.InferRequestedOutput("text_output"),
        ]
        
        # Check if this is a streaming request
        if body.stream:
            # For streaming with n>1, warn that only one completion will be streamed
            if body.n > 1:
                logger.warning("Streaming with n>1 is not fully supported; only the first completion will be streamed")
            return await handle_streaming_response(triton_client, model_name, inputs, outputs, body.model, body, user_id=current_user.full_name,)
        else:
            return await handle_non_streaming_response(model_name, outputs, body, input_data_bytes, encoded_files, user_id=current_user.full_name)


    except InferenceServerException as e:
        logger.error(f"Inference server error: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference server error: {str(e)}"
        )
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Unexpected error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )
