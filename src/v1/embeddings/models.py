from typing import Annotated, Dict, List, Optional, Union
from pydantic import BaseModel, Field, confloat, conint, field_validator


class EmbeddingsRequest(BaseModel):
    """
    Request model for creating an embedding.
    """

    model: str = Field(
        description="The name of the model to use for generating the embedding."
    )
    input: Union[str, List[str]] = Field(
        description="The input text to embed, encoded as a string or an array of strings."
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
                raise ValueError(
                    "All items in input list must be non-empty strings")
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


class Usage(BaseModel):
    """
    Represents usage statistics for the completion request.
    """
    prompt_tokens: int = Field(
        description="The number of tokens in the input prompt."
    )
    total_tokens: int = Field(
        description="The total number of tokens used in the request (prompt + completion)."
    )


class EmbeddingsResponse(BaseModel):
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
    usage: Usage = Field(
        description="Information about the number of tokens used in the request."
    )
