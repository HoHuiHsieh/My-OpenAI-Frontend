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
from typing import List, Any
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
    data: List[Any] = Field(
        default_factory=list,
        description="A list of model information objects."
    )
