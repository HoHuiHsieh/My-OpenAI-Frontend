
from typing import Annotated, Dict, List, Literal, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from config import get_config
from apikey import validate_api_key, ApiKeyData
from pydantic import BaseModel, Field, confloat, conint, field_validator


class ModelListResponse(BaseModel):
    """
    Request model list response.
    """
    object: Literal["list"] = Field(
        default="list",
        description="The type of object returned, typically 'list'."
    )
    data: List[Dict[str, Union[str, int]]] = Field(
        default_factory=list,
        description="The list of models."
    )

# Create router
models_router = APIRouter(prefix="/models", tags=["models"])

# Get config
config = get_config()


@models_router.get("", response_model=ModelListResponse)
@models_router.get("/", response_model=ModelListResponse)
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
    return ModelListResponse(data=[val.response for val in models.values()])