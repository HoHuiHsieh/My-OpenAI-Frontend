import json
from typing import List
from fastapi import APIRouter, Request, Depends, Security
from ..embeddings import EmbeddingsRequest, EmbeddingsResponse, query_embeddings
from apikey import validate_api_key, ApiKeyData
from logger import get_logger


# Set up logger for this module
logger = get_logger(__name__)

# Create router
embeddings_router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@embeddings_router.post("", response_model=EmbeddingsResponse)
@embeddings_router.post("/", response_model=EmbeddingsResponse)
async def embeddings(
    request: Request,
    body: EmbeddingsRequest,
    api_key_data: ApiKeyData = Security(validate_api_key, scopes=["embeddings:base"])
):
    """
    Process embeddings request and return the response.
    This endpoint requires an API key with 'embeddings:base' scope.
    """
    # Log the request
    logger.debug(f"Received embeddings request: {json.dumps(body.model_dump(), indent=2)}")

    # Call the query function to get embeddings
    response = await query_embeddings(body, user_id=api_key_data.user_id)
    return response
