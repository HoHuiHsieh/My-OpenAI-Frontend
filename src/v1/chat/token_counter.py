"""Token counting utilities for calculating usage information.

This module provides functions to count tokens in prompts and completions, 
including handling for tool calls. These counts are used to create UsageInfo objects.

Each request gets its own independent token counting to ensure usage is tracked
separately per API call without accumulating across requests.
"""
import numpy as np
import asyncio
import functools
from typing import List, Optional, Dict, Union, Any, Tuple
import json
import uuid

import tritonclient.grpc as grpcclient
from logger import get_logger
from config import get_config
from .typedef import UsageInfo, ToolCall

# Set up logger for this module
logger = get_logger(__name__)

# Simple LRU cache for token counts to improve performance
# (text_hash, count) pairs with a maximum size
TOKEN_CACHE_SIZE = 1000
token_cache = {}


class RequestTracker:
    """
    A class to track token usage for specific API requests.
    Each request gets its own tracker instance to ensure usage is tracked independently.
    """

    def __init__(self, request_id: str, model: str):
        self.request_id = request_id
        self.model = model
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.tool_call_tokens = 0

    def add_prompt_tokens(self, count: int) -> None:
        """Add tokens to the prompt count for this request"""
        self.prompt_tokens += count

    def add_completion_tokens(self, count: int) -> None:
        """Add tokens to the completion count for this request"""
        self.completion_tokens += count

    def add_tool_call_tokens(self, count: int) -> None:
        """Add tokens to the tool calls count for this request"""
        self.tool_call_tokens += count
        self.completion_tokens += count  # Tool calls are part of completion

    def get_usage_info(self) -> UsageInfo:
        """Get a UsageInfo object for this request"""
        return UsageInfo(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.prompt_tokens + self.completion_tokens
        )


def get_default_model() -> str:
    """Get the default model to use for token counting.

    Returns:
        The name of a default model to use for token counting
    """
    config = get_config()
    # First check if we have a dedicated usage_counter model
    if "usage_counter" in config.get("models", {}):
        return "usage_counter"
    # Fallback to any available model
    models = list(config.get("models", {}).keys())
    if models:
        return models[0]
    # Last resort default
    return "gpt-4"


def get_cache_key(text: Union[str, List[str]]) -> str:
    """Generate a cache key for the text input."""
    if isinstance(text, list):
        return "|".join(text[:100])  # Limit to first 100 chars of each item
    return text[:500]  # Limit to first 500 chars for single string


async def count_tokens(model: str, text: Union[str, List[str]]) -> int:
    """
    Count the number of tokens in a single text string or list of strings.

    Args:
        model: The model name to use for configuration
        text: A string or list of strings to count tokens for

    Returns:
        The number of tokens in the text
    """
    # Convert single string to list for consistent handling
    if isinstance(text, str):
        text = [text]
    elif not text:
        return 0

    # Check cache first
    cache_key = get_cache_key(text)
    if cache_key in token_cache:
        logger.debug(f"Token count cache hit for {len(text)} texts")
        return token_cache[cache_key]

    # Simple fallback estimator function in case the token counter service is unavailable
    def estimate_tokens(text_list: List[str]) -> int:
        """
        Estimate token count based on character count.
        This is a fallback when the token counter model is unavailable.

        Args:
            text_list: List of strings to estimate token count for

        Returns:
            Estimated token count
        """
        # Simple rule of thumb: ~4 chars per token on average for English text
        total_chars = sum(len(t) for t in text_list if t)
        return max(1, total_chars // 4)

    try:
        # Prepare the inputs for Triton
        text_bytes = [t.encode('utf-8') for t in text if t]
        if not text_bytes:
            return 0

        inputs = [grpcclient.InferInput(
            "prompt", [1, len(text_bytes)], "BYTES")]
        inputs[0].set_data_from_numpy(np.array([text_bytes], dtype=np.object_))

        # Prepare the outputs we want to receive
        outputs = [grpcclient.InferRequestedOutput("num_tokens")]

        # Extract the server URL from the model configuration
        config = get_config()

        # Use usage_counter model config if available, otherwise try the passed model config
        model_config = config.get("models", {}).get(model, {})
        host = model_config.get("host", "localhost")
        port = model_config.get("port", 8001)
        server_url = f"{host}:{port}"
        model_name = "usage_counter"

        # Create a Triton client
        triton_client = grpcclient.InferenceServerClient(
            url=server_url, verbose=False)

        # Check if the server is ready with timeout
        try:
            server_ready = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: triton_client.is_server_ready()
                ),
                timeout=2.0  # 2 second timeout
            )
            if not server_ready:
                logger.warning(
                    "Token counting server not ready, using fallback")
                count = estimate_tokens(text)
                token_cache[cache_key] = count
                return count
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(
                f"Token counting server check failed: {e}, using fallback")
            count = estimate_tokens(text)
            token_cache[cache_key] = count
            return count

        # For gRPC client, use run_in_executor since it doesn't support async directly
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: triton_client.infer(
                model_name=model_name,
                inputs=inputs,
                outputs=outputs
            )
        )

        # Extract the token count information from the response
        num_tokens = response.as_numpy("num_tokens")
        if num_tokens is None or len(num_tokens) == 0:
            logger.warning(
                "Failed to retrieve token counts from model, using fallback estimate")
            count = estimate_tokens(text)
        else:
            count = int(num_tokens.sum())

        # Update cache and manage cache size
        token_cache[cache_key] = count
        if len(token_cache) > TOKEN_CACHE_SIZE:
            # Simple approach: clear half the cache when it gets too large
            keys_to_remove = list(token_cache.keys())[:(TOKEN_CACHE_SIZE // 2)]
            for k in keys_to_remove:
                token_cache.pop(k, None)

        return count

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.warning(
            f"Token counting error, using fallback estimator: {str(e)}")
        count = estimate_tokens(text)
        token_cache[cache_key] = count
        return count


async def extract_tool_call_text(tool_calls: List[ToolCall]) -> str:
    """
    Extract text from tool calls for token counting purposes.

    Args:
        tool_calls: A list of tool call dictionaries

    Returns:
        A string representation of the tool calls for token counting
    """
    if not tool_calls:
        return ""

    result = []
    for call in tool_calls:
        # Convert each tool call to a string representation
        if hasattr(call, 'function'):
            # If the call has a function attribute, use its model_dump method if available
            if hasattr(call.function, 'model_dump'):
                # Use model_dump to get a dict representation of the function
                function = call.function.model_dump()
                result.append(f"{function}")
    return " ".join(result)


async def create_usage_info(
    model: Optional[str] = None,
    input_text: Union[str, List[str]] = "",
    completion: Union[str, List[str], None] = None,
    tool_calls: Optional[List[ToolCall]] = None,
    request_id: Optional[str] = None
) -> UsageInfo:
    """
    Create a UsageInfo object by counting tokens in prompts and completions.
    Each call creates an independent usage count specific to a single request.

    Args:
        model: The model name to use for token counting (optional, uses default if not provided)
        input_text: The input prompt text or list of texts
        completion: The model completion(s) as a string or list of strings
        tool_calls: Optional list of tool calls to include in token count
        request_id: Optional unique identifier for this specific request

    Returns:
        A UsageInfo object with token counts
    """
    # Generate a request_id if none provided to ensure each call is tracked independently
    if request_id is None:
        request_id = str(uuid.uuid4())

    # Use default model if none provided
    if model is None:
        model = get_default_model()

    # Create a request tracker to keep token counts for this specific request only
    tracker = RequestTracker(request_id=request_id, model=model)

    # Handle empty inputs
    if not input_text:
        input_text = ""
    else:
        # Count prompt tokens for this specific request
        prompt_tokens = await count_tokens(model, input_text)
        tracker.add_prompt_tokens(prompt_tokens)

    # Handle completion counting for this specific request
    if completion:
        # Convert completion to list if it's a string
        completion_texts = completion if isinstance(
            completion, list) else [completion]
        # Filter out None or empty strings
        completion_texts = [t for t in completion_texts if t]

        if completion_texts:
            # Count completion tokens
            completion_tokens = await count_tokens(model, completion_texts)
            tracker.add_completion_tokens(completion_tokens)

    # Include tool calls in completion token count if present
    if tool_calls:
        tool_call_text = await extract_tool_call_text(tool_calls)
        if tool_call_text:
            tool_call_tokens = await count_tokens(model, tool_call_text)
            tracker.add_tool_call_tokens(tool_call_tokens)
            logger.debug(
                f"Added {tool_call_tokens} tokens for tool calls for request {request_id}")

    # Get and return the UsageInfo object for this specific request only
    return tracker.get_usage_info()


# Overload function for backward compatibility with code that may not pass a model parameter
async def count_tokens_any(text: Union[str, List[str]]) -> int:
    """
    Count the number of tokens in a single text string or list of strings.
    This is a convenience wrapper that uses the default model.

    Args:
        text: A string or list of strings to count tokens for

    Returns:
        The number of tokens in the text
    """
    return await count_tokens(get_default_model(), text)

# Keep the original function for backward compatibility


async def token_counter(model_or_prompts: Union[str, List[str]], prompts: Optional[List[str]] = None) -> int:
    """
    Legacy function for counting tokens in a list of prompts.

    Args:
        model_or_prompts: Either model name or list of prompts (for backward compatibility)
        prompts: A list of prompt strings (optional)

    Returns:
        The number of tokens in the prompts
    """
    # Handle backward compatibility with different param orders
    if prompts is not None:
        # First param is model, second is prompts
        return await count_tokens(model_or_prompts, prompts)
    else:
        # Only prompts provided, use default model
        return await count_tokens_any(model_or_prompts)
