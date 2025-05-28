"""
Embedding API Type Definitions

This module contains Pydantic models for the embedding API, defining both request and
response structures. These models enforce type validation and provide documentation
for the embedding generation interface.

The main models are:
- CreateEmbeddingRequest: For validating embedding generation requests
- EmbeddingData: For individual embedding vectors in the response
- CreateEmbeddingResponse: For the complete embedding API response
"""

from typing import Annotated, Dict, List, Optional, Union
from pydantic import BaseModel, Field, confloat, conint, field_validator


"""
Create Embedding API 

Creates an embedding vector representing the input text.

Request body
- input [string or array](required): The input text to embed, encoded as a string or array of string.
- model [string](required): ID of the model to use. You can use the List models API to see all of your available models, or see our Model overview for descriptions of them.
- dimensions [integer](optional): The number of dimensions the resulting output embeddings should have. Only supported in text-embedding-3 and later models.
- encoding_format [string](optional): Defaults to float. The format to return the embeddings in. Can be either float or base64.
- user [string](optional): A unique identifier representing your end-user, which can help OpenAI to monitor and detect abuse. Learn more.
- type [string](optional): The type of input. Can be either 'query' or 'passage'.

Returns
A list of embedding objects with the following fields: 
- object [string]: The type of object returned, typically "embedding".
- index [integer]: The index of the embedding in the list of embeddings.
- embedding [array]: The embedding vector, which is a list of floats. The length of vector depends on the model as listed in the embedding guide.
"""

class CreateEmbeddingRequest(BaseModel):
    """
    Request model for creating an embedding.
    """

    model: str = Field(
        description="The name of the model to use for generating the embedding."
    )
    input: Union[str, List[str]] = Field(
        description="The input text to embed, encoded as a string or an array of strings."
    )
    type: Optional[Annotated[str, Field(enum=["query", "passage"])]] = Field(
        default=None,
        description="The type of input. Can be either 'query' or 'passage'.",
    )
    user: Optional[str] = Field(
        default=None,
        description="A unique identifier representing your end-user, which can help monitoring and abuse detection.",
    )
    encoding_format: Optional[Annotated[str, Field(enum=["float", "base64"])]] = Field(
        default="float",
        description="The format to return the embeddings in. Can be either `float` or `base64`.",
    )
    dimensions: Optional[Annotated[int, conint(ge=1)]] = Field(
        default=None,
        description="The number of dimensions the resulting output embeddings should have. Only supported in text-embedding-3 and later models.",
    )

    # Validate input field
    @field_validator("input")
    def validate_input(cls, v):
        if isinstance(v, str):
            if not v.strip():
                raise ValueError("Input text cannot be empty")
            return [v]  # Convert single string to list for consistent handling
        elif isinstance(v, list):
            if not v:
                raise ValueError("Input list cannot be empty")
            if not all(isinstance(item, str) and item.strip() for item in v):
                raise ValueError("All items in input list must be non-empty strings")
            return v
        else:
            raise ValueError("Input must be a string or a list of strings")


class EmbeddingData(BaseModel):
    """
    Data model for embedding response.
    """

    object: Annotated[str, Field(enum=["embedding"])] = Field(
        description="The type of object returned, typically 'embedding'."
    )
    embedding: Union[
        List[float],  # For encoding_format == "float"
        str           # For encoding_format == "base64"
    ] = Field(
        description=(
            "The embedding vector. "
            "If encoding_format is 'float', this is a list of floats. "
            "If encoding_format is 'base64', this is a base64-encoded string."
        )
    )
    index: Annotated[int, conint(ge=0)] = Field(
        description="The index of the embedding in the response."
    )


class UsageInfo(BaseModel):
    """
    Represents usage statistics for the completion request.
    """
    prompt_tokens: int = Field(
        description="The number of tokens in the input prompt."
    )
    total_tokens: int = Field(
        description="The total number of tokens used in the request (prompt + completion)."
    )


class CreateEmbeddingResponse(BaseModel):
    """
    Response model for creating an embedding.
    """

    object: Annotated[str, Field(enum=["list"])] = Field(
        description="The type of object returned."
    )
    data: List[EmbeddingData] = Field(
        description="A list of embedding data objects."
    )
    model: str = Field(
        description="The name of the model used to generate the embedding."
    )
    usage: UsageInfo = Field(
        description="Information about the number of tokens used in the request."
    )
