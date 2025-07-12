"""
Formatting utilities for Llama 3 models.

This module provides functions for formatting messages and tools according to
the Llama 3 prompt format requirements.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import json
import base64
from ..typedef import ChatMessage, Tool, ResponseFormat, TextContentPart, FileContentPart, FileObject
from .constants import *
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def format_tools_for_llama3(tools: List[Tool]) -> str:
    """
    Format tools for Llama 3 models.

    This converts the OpenAI-style tool definitions to a format Llama 3 can understand.

    Args:
        tools: List of Tool objects containing function definitions

    Returns:
        A string representation of tools compatible with Llama 3's tool format
    """
    if not tools:
        return ""

    formatted_tools = []

    for tool in tools:
        # Extract function information
        function = tool.function
        name = function.name
        description = function.description or ""
        parameters = function.parameters

        # Format the tool definition
        tool_str = f"Tool: {name}\n"

        if description:
            tool_str += f"Description: {description}\n"

        # Format parameters section
        if parameters:
            tool_str += "Parameters:\n"

            # Handle properties based on the ParametersDefinition model
            properties = {}
            required_params = []

            # Check if parameters is a dictionary or a ParametersDefinition object
            if isinstance(parameters, dict):
                if "properties" in parameters:
                    properties = parameters["properties"]
                if "required" in parameters:
                    required_params = parameters["required"]
            else:
                # It's a ParametersDefinition object
                properties = parameters.properties or {}
                required_params = parameters.required if hasattr(
                    parameters, "required") else []

            # Format each parameter
            for param_name, param_details in properties.items():
                # Handle both dict and PropertiesDefinition object
                if isinstance(param_details, dict):
                    param_type = param_details.get("type", "unknown")
                    param_desc = param_details.get("description", "")
                    enum_values = param_details.get("enum", None)
                else:
                    param_type = param_details.type
                    param_desc = param_details.description or ""
                    enum_values = getattr(param_details, "enum", None)

                req_status = "required" if param_name in required_params else "optional"

                # Format each parameter
                tool_str += f"  - {param_name} ({param_type}, {req_status}): {param_desc}\n"

                # If enum values are available, include them
                if enum_values:
                    enum_str = ", ".join([str(v) for v in enum_values])
                    tool_str += f"    Allowed values: [{enum_str}]\n"

        formatted_tools.append(tool_str)

    # Join all tool definitions with separators
    return "\n".join(formatted_tools)


def format_system_message(
        system_message: Optional[ChatMessage],
        tool_instructions: str,
        format_instructions: str
) -> str:
    """
    Format the system message with tool and format instructions.

    Args:
        system_message: The system message object.
        tool_string: Formatted string of tools.
        format_instructions: Instructions for response format.

    Returns:
        A formatted system message string.
    """
    input_system_content = system_message.content if system_message else "You are a helpful, harmless, and precise assistant."
    if tool_instructions and format_instructions:
        return f"{tool_instructions}\n{format_instructions}\n\n{input_system_content}"
    return f"{tool_instructions}{format_instructions}\n\n{input_system_content}"


def process_message_content(message, supports_vision, encoded_files) -> Tuple[str, List[str]]:
    """
    Process the content of a message and return formatted text and encoded files.

    Args:
        message: The message object.
        supports_vision: Whether vision support is enabled.
        encoded_files: List to collect encoded file data.

    Returns:
        A tuple containing formatted text and a list of text parts.
    """
    text_parts, file_parts = [], []
    for part in message.content:
        try:
            if isinstance(part, dict):
                part_type = part.get("type", "")
                if part_type == "text":
                    text_parts.append(part.get("text", "").strip())
                elif part_type == "file" and supports_vision:
                    file = part.get("file", {})
                    file_parts.append(file)
                    if file.get("file_data"):
                        encoded_files.append({
                            "data": file["file_data"],
                            "filename": file.get("filename", "image.jpg")
                        })
            elif isinstance(part, TextContentPart) and part.text:
                text_parts.append(part.text.strip())
            elif isinstance(part, FileContentPart) and supports_vision:
                file_parts.append(part.file)
                if part.file.file_data:
                    encoded_files.append({
                        "data": part.file.file_data,
                        "filename": part.file.filename or "image.jpg"
                    })
        except Exception as e:
            logger.error(f"Error processing content part: {e}")
            continue

    formatted_text = "<|image|>" if file_parts and supports_vision else ""
    return formatted_text, text_parts


def format_messages_for_llama3(
        messages: List[ChatMessage],
        tools: Optional[List[Tool]] = None,
        response_format: Optional[Union[ResponseFormat,
                                        Dict[str, Any]]] = None,
        model_types: Optional[List[str]] = None,
        parallel_tool_calls: Optional[bool] = True
) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
    """
    Format a list of messages according to the Llama 3 prompt format.

    Args:
        messages: List of ChatMessage objects containing role and content.
        tools: Optional list of Tool objects for function calling capability.
        response_format: Optional dictionary specifying the format for model's response (e.g., JSON).
        model_types: Optional list of model types to determine if file content should be processed.
        parallel_tool_calls: Whether to allow parallel tool calls in the response.

    Returns:
        A tuple containing:
        - A formatted string ready to be sent to a Llama 3 model.
        - A list of encoded file data if any files were processed, otherwise None.
    """
    if not messages:
        logger.warning(
            "Empty message list provided to format_messages_for_llama3")
        return ""

    formatted_text = f"{BEGIN_OF_TEXT}\n"
    has_system = False
    tool_instructions = ""
    format_instructions = ""

    # Create tool instructions if tools are provided
    tool_string = format_tools_for_llama3(tools) if tools else ""
    if tool_string:
        if parallel_tool_calls:
            parallel_tool_calls_string = "\n\nYou can call multiple tools in parallel. "
        else:
            parallel_tool_calls_string = "\n\nYou can call one tool at a time. "
        tool_instructions = f"\n\nYou have access to the following tools:\n\n{tool_string}\n\nTo use a tool, respond with a message containing a valid JSON object with these required attributes:\n- \"name\": the exact function name to call\n- \"arguments\": an object containing all required parameters for the function\n\nExample format:\n```json\n{{\n  \"name\": \"tool_name\",\n  \"arguments\": {{\n    \"param1\": \"value1\",\n    \"param2\": \"value2\"\n  }}\n}}\n```\n{parallel_tool_calls_string}" if tool_string else ""


    if response_format:
        if isinstance(response_format, ResponseFormat):
            format_type = response_format.type
            json_schema = response_format.json_schema
        else:
            format_type = response_format.get("type", "text")
            json_schema = response_format.get("json_schema", None)

        if format_type == "json_object":
            format_instructions += "You must respond in JSON format. "
            if json_schema:
                schema_str = json.dumps(json_schema, indent=2)
                format_instructions += f"The JSON should follow this schema:\n{schema_str}"
            else:
                format_instructions += "The response should be valid JSON."

    system_message = next(
        (msg for msg in messages if msg.role == "system"), None)
    system_content = format_system_message(
        system_message, tool_instructions, format_instructions)
    formatted_text += f"{START_HEADER}system{END_HEADER}\n{system_content}\n{END_OF_TURN}\n"
    has_system = True

    encoded_files = []
    supports_vision = model_types and "vision" in model_types

    for message in messages:
        if message.role == "system" and has_system:
            continue

        formatted_text += f"{START_HEADER}{message.role}{END_HEADER}\n"

        # if not message.content:
        #     formatted_text += f"{END_OF_TURN}\n"
        #     continue
        logger.debug( f"{message}")

        if isinstance(message.content, str):
            content = message.content.strip()
            formatted_text += f"{content}\n{END_OF_TURN}\n" if content else f"{END_OF_TURN}\n"
        elif isinstance(message.content, list):
            file_text, text_parts = process_message_content(
                message, supports_vision, encoded_files)
            formatted_text += file_text
            if text_parts:
                # Join with space but preserve original formatting when combining multiple text parts
                formatted_text += f"{' '.join(text_parts).strip()}\n{END_OF_TURN}\n"
            else:
                formatted_text += f"{END_OF_TURN}\n"
        else:
            logger.warning(
                f"Unsupported content type: {type(message.content)}")
            formatted_text += f"{END_OF_TURN}\n"

    # Add assistant role for the model's response
    formatted_text += f"{START_HEADER}assistant{END_HEADER}\n"

    # Add JSON hint if needed for structured responses
    if response_format:
        if isinstance(response_format, ResponseFormat):
            format_type = response_format.type
        else:
            format_type = response_format.get("type", "text")

        if format_type == "json_object":
            # Provide opening brace to prompt model to continue the JSON structure
            formatted_text += '{\n"name":'

    # Logging for debugging purposes with truncated preview
    log_preview = formatted_text[:100] + \
        "..." if len(formatted_text) > 100 else formatted_text
    logger.debug(f"Formatted Llama 3 prompt: {log_preview}")
    logger.debug(f"Estimated token count: {len(formatted_text.split())}")

    return formatted_text, encoded_files if encoded_files else None
