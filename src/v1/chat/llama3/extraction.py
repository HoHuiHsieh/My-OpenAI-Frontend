"""
Response extraction utilities for Llama 3 models.

This module provides functions for extracting and parsing responses from
Llama 3 models, including handling special formats like tool calls and code blocks.
"""

import json
from typing import Dict, Any
from .constants import *
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def extract_assistant_response(response: str) -> Dict[str, Any]:
    """
    Extract the assistant's response from the model's output.

    Some models may return the entire prompt template with the response,
    this function extracts only the assistant's response part and identifies
    whether it contains tool calls or regular text.

    Args:
        response: The raw response from the model

    Returns:
        A dictionary containing the extracted response and metadata about tool calls
    """
    result = {
        "content": "",
        "has_tool_calls": False,
        "tool_calls": []
    }

    # Look for the assistant role header pattern
    assistant_header = f"{START_HEADER}assistant{END_HEADER}"
    if assistant_header in response:
        parts = response.split(assistant_header, 1)
        if len(parts) > 1:
            response = parts[1].strip()

    # Remove end tokens if present
    if END_OF_TEXT in response:
        response = response.split(END_OF_TEXT, 1)[0].strip()

    if END_OF_TURN in response:
        response = response.split(END_OF_TURN, 1)[0].strip()

    if END_OF_MESSAGE in response:
        response = response.split(END_OF_MESSAGE, 1)[0].strip()

    # Handle code blocks specifically
    if PYTHON_TAG in response:
        # Extract code between PYTHON_TAG and END_OF_MESSAGE
        parts = response.split(PYTHON_TAG, 1)
        if len(parts) > 1:
            code_parts = parts[1].split(
                END_OF_MESSAGE, 1) if END_OF_MESSAGE in parts[1] else [parts[1]]
            code = code_parts[0].strip()
            result["content"] = f"```python\n{code}\n```"
            result["has_tool_calls"] = True
            result["tool_calls"] = [{
                "type": "function",
                "function": {
                    "name": "python",
                    "arguments": json.dumps({"code": code})
                }
            }]
            return result

    # Try to extract JSON for tool calls
    # Tool calls are usually JSON objects in the response
    json_start = response.find('{')
    json_end = response.rfind('}')

    if json_start >= 0 and json_end > json_start:
        potential_json = response[json_start:json_end+1]
        try:
            json_data = json.loads(potential_json)

            # Check if this is likely a function call
            if isinstance(json_data, dict) and ('name' in json_data or 'function' in json_data):
                result["has_tool_calls"] = True

                # Create standardized tool call format
                if 'name' in json_data and 'arguments' in json_data:
                    # Direct function call format
                    tool_call = {
                        "type": "function",
                        "function": {
                            "name": json_data['name'],
                            "arguments": json_data.get('arguments') if isinstance(json_data.get('arguments'), str)
                            else json.dumps(json_data.get('arguments', {}))
                        }
                    }
                    result["tool_calls"].append(tool_call)

                # Preserve the JSON in the content
                result["content"] = potential_json
                return result
        except json.JSONDecodeError:
            # Not valid JSON, treat as regular text
            pass

    # Regular text response
    result["content"] = response.strip()
    return result
