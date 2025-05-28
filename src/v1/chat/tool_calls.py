"""Tool call extraction utilities for chat completions."""
import json
import re
from typing import List, Tuple, Optional

from logger import get_logger
from .typedef import ToolCall, ToolCallFunction

# Set up logger for this module
logger = get_logger(__name__)


def extract_tool_calls_from_text(text: str, parallel_tool_calls: Optional[bool] = True) -> Tuple[List[ToolCall], str, bool]:
    """
    Extract tool calls from text and return the tool calls and cleaned text.

    Args:
        text: The text to extract tool calls from
        parallel_tool_calls: Whether multiple tool calls are allowed

    Returns:
        Tuple of (tool_calls, cleaned_text, found_tool_calls)
    """
    tool_calls = []
    cleaned_text = text
    found_tool_calls = False

    try:
        # Check for patterns that indicate tool calls in the response
        if '\"name\"' in text and '\"arguments\"' in text:
            logger.debug("Potential tool call patterns found in stream chunk")
            # Match JSON objects (potentially nested) using a regex pattern
            json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
            potential_objects = re.findall(json_pattern, text)

            logger.debug(
                f"Found {len(potential_objects)} potential JSON objects in stream")
            content_without_tools = text

            for obj_str in potential_objects:
                try:
                    # Try to parse the JSON object
                    function_data = json.loads(obj_str)

                    # Check if this looks like a tool call
                    if isinstance(function_data, dict):
                        # Ensure we have the required fields
                        if 'name' in function_data and 'arguments' in function_data:
                            # Handle arguments that could be string or dict
                            arguments = function_data['arguments']
                            if isinstance(arguments, str):
                                # Try to parse string arguments as JSON if they look like JSON
                                if arguments.strip().startswith('{') and arguments.strip().endswith('}'):
                                    try:
                                        arguments = json.loads(arguments)
                                    except json.JSONDecodeError:
                                        # Keep as string if it's not valid JSON
                                        pass

                            # Create a proper ToolCallFunction
                            tool_function = ToolCallFunction(
                                name=function_data['name'],
                                arguments=arguments
                            )

                            # Create the ToolCall
                            tool_call = ToolCall(
                                type="function",
                                function=tool_function
                            )

                            # Only add the tool call if parallel_tool_calls is True or this is the first tool call
                            if parallel_tool_calls or len(tool_calls) == 0:
                                tool_calls.append(tool_call)
                                found_tool_calls = True
                            else:
                                logger.debug(
                                    "Skipping additional tool call because parallel_tool_calls is False")

                            # Remove the tool call from the content
                            content_without_tools = content_without_tools.replace(
                                obj_str, "").strip()

                except json.JSONDecodeError:
                    # Not a valid JSON object, skip it
                    continue
                except Exception as e:
                    logger.warning(
                        f"Error processing potential tool call in stream: {str(e)}")
                    continue

            if found_tool_calls:
                cleaned_text = content_without_tools
    except Exception as e:
        logger.warning(f"Error extracting tool calls from stream: {str(e)}")

    return tool_calls, cleaned_text, found_tool_calls
