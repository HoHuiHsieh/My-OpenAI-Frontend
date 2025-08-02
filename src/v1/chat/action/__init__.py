from .main import (
    query_chat_completion,
    query_streaming_chat_completion
)


# Define public API
__all__ = [
    "query_chat_completion",
    "query_streaming_chat_completion",
]