"""
Embeddings package for OpenAI-compatible embedding generation.

This package provides functionality for generating text embeddings using Triton Inference Server
with an OpenAI-compatible API interface.

Components:
- EmbeddingsRequest: Request model for embedding generation
- EmbeddingsResponse: Response model containing embeddings and usage info
- EmbeddingData: Individual embedding data model
- Usage: Token usage statistics model
- query_embeddings: Main function to process embedding requests

Example usage:
    from v1.embeddings import EmbeddingsRequest, query_embeddings
    
    request = EmbeddingsRequest(
        model="text-embedding-model",
        input="Hello world",
        encoding_format="float"
    )
    
    response = await query_embeddings(request)
"""
from .models import (
    EmbeddingsRequest,
    EmbeddingsResponse, 
    EmbeddingData,
    Usage
)
from .action import query_embeddings

# Define public API
__all__ = [
    # Request/Response models
    "EmbeddingsRequest",
    "EmbeddingsResponse",
    "EmbeddingData", 
    "Usage",
    
    # Main functionality
    "query_embeddings"
]
