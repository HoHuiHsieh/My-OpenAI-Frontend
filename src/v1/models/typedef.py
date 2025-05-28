"""
File Overview:
--------------
This module defines the type definitions and data models used throughout the models API.

It contains Pydantic models that:
- Define the structure of model metadata information (ModelInfo)
- Specify the response format for model listing endpoints (CreateModelListResponse)
- Enforce validation rules for API data

These type definitions ensure consistent data structures and validation across
the application, enabling proper type checking and automatic API documentation.
They follow OpenAI API conventions for model information representation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List
import time
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


class ModelInfo(BaseModel):
    """
    Model information representing metadata about an AI model.
    
    This follows the OpenAI API convention for model objects.
    """
    id: str = Field(
        description="The unique identifier for the model.",
        examples=["gpt-4", "claude-2", "llama-7b"]
    )
    object: str = Field(
        default="model",
        description="The type of object returned, always 'model' for model objects."
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="The Unix timestamp (in seconds) when the model was created."
    )
    owned_by: str = Field(
        description="The organization that owns or provides the model.",
        examples=["openai", "anthropic", "meta"]
    )
    
    @field_validator('created')
    @classmethod
    def check_created_timestamp(cls, value: int) -> int:
        """Validates that the created timestamp is reasonable."""
        # If value is 0, set it to current time
        if value == 0:
            logger.warning(f"Found a model with created=0, using current time instead")
            return int(time.time())
            
        # Ensure timestamp isn't in the future
        current_time = int(time.time())
        if value > current_time:
            raise ValueError(f"Created timestamp cannot be in the future")
        
        # Ensure timestamp isn't too far in the past, but allow older models
        # Use a much earlier cutoff (1970) to be more permissive
        if value < 0:  # Only reject negative timestamps
            logger.warning(f"Invalid timestamp {value}, using current time instead")
            return int(time.time())
        
        return value
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "gpt-4",
                    "object": "model",
                    "created": 1687882410,
                    "owned_by": "openai"
                }
            ]
        }
    }


class CreateModelListResponse(BaseModel):
    """
    Response model for listing available models.
    
    This follows the OpenAI API convention for list responses, consisting of
    an object type and a data array of model information objects.
    """
    object: str = Field(
        default="list",
        description="The type of object returned, always 'list' for list responses."
    )
    data: List[ModelInfo] = Field(
        default_factory=list,
        description="A list of model information objects."
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "object": "list",
                    "data": [
                        {"id": "gpt-4", "object": "model", "created": 1687882410, "owned_by": "openai"},
                        {"id": "gpt-3.5-turbo", "object": "model", "created": 1677610602, "owned_by": "openai"}
                    ]
                }
            ]
        }
    }
