"""Tool call extraction utilities for chat completions."""
import json
import uuid
import re
from datetime import datetime
from typing import List, Tuple, Optional
from logger import get_logger
from usage import get_usage_logger
from ..models.response import ToolCall, ToolCallFunction


# Set up logger for this module
logger = get_logger(__name__)


def extract_tool_calls_from_text(
        text: str,
        parallel_tool_calls: Optional[bool] = True
) -> List[ToolCall]:
    """
    Extract tool calls from a given text.
    """
    tool_calls = []

    # Matching json objects (potentially nested) using a regex pattern
    json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    matches = re.findall(json_pattern, text)
    logger.debug(f"Found {len(matches)} potential JSON objects in text")

    # Iterate over all matches
    for match in matches:
        # load the match as JSON
        try:
            match = json.loads(match)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON from match: {match}")
            continue

        # Check if this looks like a tool call
        if isinstance(match, dict) and 'name' in match and 'arguments' in match:
            tool_function = ToolCallFunction(
                name=match['name'],
                arguments=json.dumps(match['arguments'], ensure_ascii=False)
            )
            tool_call = ToolCall(
                type="function",
                function=tool_function
            )
            tool_calls.append(tool_call)

        # If parallel_tool_calls is False, break after the first tool call
        if not parallel_tool_calls and tool_calls:
            break

    return tool_calls or None


def log_chat_api_usage(
        request_id: str,
        user_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        **kwargs
):
    """Log usage for chat API calls"""

    # Get the chat logger
    logger = get_usage_logger("chat")

    # Prepare usage data
    usage_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_type": "chat",
        "user_id": user_id,
        "model": model,
        "request_id": request_id or str(uuid.uuid4()),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "extra_data": kwargs  # Additional metadata
    }

    # Log the usage
    logger.log(25, json.dumps(usage_data))
