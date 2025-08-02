import json
from typing import List, Union
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Request, Depends, Security
from ..chat import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse, query_chat_completion, query_streaming_chat_completion
from apikey import validate_api_key, ApiKeyData
from logger import get_logger


# Set up logger for this module
logger = get_logger(__name__)

# Create router
chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post("/completions", response_model=Union[ChatCompletionResponse, ChatCompletionStreamResponse])
async def chat_completion(
    request: Request,
    body: ChatCompletionRequest,
    apiKeyData: ApiKeyData = Security(
        validate_api_key, scopes=["embeddings:base"])
):
    """
    Endpoint to create a chat completion.
    """
    # Log the request
    logger.debug(
        f"Received chat completion request: {json.dumps(body.model_dump(), indent=2)}")

    # Get api key from the request
    apiKey = request.headers.get("Authorization", "").replace("Bearer ", "")

    # Check if the request is for streaming
    is_streaming = body.stream
    if is_streaming:
        # Log the streaming mode
        logger.debug("Run in streaming mode")

        # Define a generator function to stream responses
        stream_generator = query_streaming_chat_completion(body,
                                                           user_id=apiKeyData.user_id,
                                                           apiKey=apiKey)

        # Return a streaming response
        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream"
        )

    # For non-streaming requests, call the query function directly
    logger.debug("Run in non-streaming mode")
    response = await query_chat_completion(body,
                                           user_id=apiKeyData.user_id,
                                           apiKey=apiKey)
    return response
