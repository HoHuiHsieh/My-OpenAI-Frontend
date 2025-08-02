
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from config import get_config
from apikey import validate_api_key, ApiKeyData


# Create router
models_router = APIRouter(prefix="/models", tags=["models"])

# Get config
config = get_config()


@models_router.get("", response_model=List[dict])
@models_router.get("/", response_model=List[dict])
async def list_models(
    api_key_data: ApiKeyData = Security(validate_api_key, scopes=["models:read"])
):
    """
    List available models
    """
    # Fetch model names from the database or configuration
    config = get_config()
    models = config.get_models()

    if not models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No models available"
        )
    
    # Get scopes from the API key data
    scopes = api_key_data.scopes if api_key_data else []

    # Filter models based on scopes
    models = {name: model for name, model in models.items() if set(model.type).intersection(scopes)}

    return [val.response for val in models.values()]
