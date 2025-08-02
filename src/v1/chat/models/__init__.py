"""
Chat models package for OpenAI-compatible chat completions.

This package provides data models for chat completion requests and responses
that are compatible with the OpenAI Chat Completions API.
"""

from .response import (
    ChatCompletionResponse,
    ChatCompletionStreamResponse
)
from .request import (
    ChatCompletionRequest
)

# Define public API
__all__ = [
    # Response models
    "ChatCompletionResponse",
    "ChatCompletionStreamResponse",
    
    # Request models
    "ChatCompletionRequest"
]