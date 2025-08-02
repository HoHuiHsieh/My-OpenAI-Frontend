"""
serialize.py
This module provides serialization functions for chat messages in the Llama3 model.
It includes functions to serialize chat messages into a format compatible with the Llama3 model.
"""
import json
from typing import List
from ..models.request import ChatCompletionMessages, ChatCompletionRequest, JsonSchema
from .tool_use import create_tool_use_prompt
from logger import get_logger


# Set up logger for this module
logger = get_logger(__name__)

# Start of the prompt
BEGIN_OF_TEXT = "<|begin_of_text|>"

# End of generation - generated only by base models
END_OF_TEXT = "<|end_of_text|>"

# Message role header markers
START_HEADER = "<|start_header_id|>"
END_HEADER = "<|end_header_id|>"

# End of a message - stopping point for tool calls
END_OF_MESSAGE = "<|eom_id|>"

# End of turn - marks the completion of interaction with a user message
END_OF_TURN = "<|eot_id|>"

# Special tag for Python code in responses
PYTHON_TAG = "<|python_tag|>"

# Special tag for image content in responses
IMAGE_TAG = "<|image|>"

# System prompt template
SYSTEM_PROMPT_TEMPLATE_WITH_TOOLS = (
    "You are a helpful AI assistant with access to tools. Your goal is to provide accurate, "
    "helpful responses while leveraging available tools when they can enhance your answer.\n\n"
    "## Available Tools\n"
    "{tools}\n\n"
    "## Instructions\n"
    "{instructions}\n\n"
    "## Guidelines\n"
    "- First determine if you can provide a complete, accurate answer using your existing knowledge\n"
    "- If you can answer directly without tools, do so immediately\n"
    "- Only use tools when they are necessary to:\n"
    "  - Access real-time or current information\n"
    "  - Perform calculations or computations\n"
    "  - Retrieve specific data you don't have\n"
    "  - Execute actions or operations\n"
    "- When using tools, explain why they are needed and how they enhance your response\n"
    "- Do NOT predict, guess, or assume what tool calls will return\n"
    "- Provide clear, well-structured responses regardless of tool usage\n"
    "- Verify tool outputs and integrate them naturally into your response"
    "{guidelines}\n\n"
    "## Tool Usage Format\n"
    "When you need to use tools, respond with a valid JSON array containing tool call objects.\n"
    "Each tool call object should contain:\n"
    "- \"name\": the exact function name to call\n"
    "- \"arguments\": an object containing all required parameters for the function\n\n"
    "For a single tool call:\n"
    "```json\n"
    "[{{\n"
    "  \"name\": \"tool_name\",\n"
    "  \"arguments\": {{\n"
    "    \"param1\": \"value1\",\n"
    "    \"param2\": \"value2\"\n"
    "  }}\n"
    "}}]\n"
    "```\n\n"
    "{parallel_tool_call_instruction}\n\n"
    "## Response Format\n"
    "{response_instruction}\n\n"
    "Always prioritize direct responses when your knowledge is sufficient. Use tools strategically "
    "only when they add genuine value to your answer.\n"
)

SYSTEM_PROMPT_TEMPLATE_WITHOUT_TOOLS = (
    "You are a helpful AI assistant. Your goal is to provide accurate, helpful, and "
    "well-reasoned responses based on your knowledge.\n\n"
    "## Instructions\n"
    "{instructions}\n\n"
    "## Guidelines\n"
    "- Provide clear, concise, and accurate information\n"
    "- Structure your responses logically with proper organization\n"
    "- Use examples and analogies when they enhance understanding\n"
    "- Be specific and detailed when appropriate\n"
    "- Acknowledge limitations and express uncertainty when warranted\n"
    "- Maintain a professional and helpful tone\n"
    "- Focus on being practical and actionable in your advice"
    "{guidelines}\n\n"
    "## Response Format\n"
    "{response_instruction}\n\n"
    "Always strive to provide comprehensive yet focused responses that directly address "
    "the user's needs while maintaining clarity and accuracy.\n"
)


def serialize_message(data: ChatCompletionRequest) -> str:
    """
    Serialize a ChatCompletionMessages object to a string format.

    Args:
        data (ChatCompletionRequest): The chat completion request data containing messages.
    Returns:
        str: The serialized string representation of the chat messages.
    Raises:
        ValueError: If the data is invalid or does not meet the serialization requirements.
    """
    # Get the messages from the data
    messages: List[ChatCompletionMessages] = data.messages
    if not messages:
        raise ValueError("No messages provided for serialization")

    # Check if messages have more than one system message
    if len([m for m in messages if m.role == "system"]) > 1:
        raise ValueError("Only one system message is allowed")

    # Check if the last message is a user message
    if messages and messages[-1].role != "user":
        raise ValueError("The last message must be a user message")

    # Create tool use prompt if tools are present
    tool_use_prompt = ""
    if data.tools:
        tool_use_prompt = create_tool_use_prompt(data)

    # Prepare system prompt if it exists
    system_prompt = ""
    for message in messages:
        if message.role == "system" or message.role == "developer":
            system_prompt = message.content
            break

    # Prepare guidelines with the request data
    guidelines = []
    # - use parallel tool calls if specified
    is_parallel_tool_calls = data.parallel_tool_calls or False
    parallel_tool_call_instruction = ""
    if is_parallel_tool_calls and tool_use_prompt:
        guidelines.append(
            "If multiple tools are needed, use them in logical sequence.")
        parallel_tool_call_instruction = (
            "For multiple tool calls:\n"
            "```json\n"
            "[{{\n"
            "  \"name\": \"first_tool\",\n"
            "  \"arguments\": {{\n"
            "    \"param1\": \"value1\"\n"
            "  }}\n"
            "}},\n"
            "{{\n"
            "  \"name\": \"second_tool\",\n"
            "  \"arguments\": {{\n"
            "    \"param2\": \"value2\"\n"
            "  }}\n"
            "}}]\n"
            "```\n\n"
        )

    guidelines = "\n- ".join(guidelines) if guidelines else ""

    # Prepare response format
    response_format = data.response_format.type or "text"
    response_instruction = ""
    if response_format == "text":
        # Default text response format
        response_instruction = (
            "Provide well-structured responses with clear reasoning and explanations."
        )
    elif response_format == "json":
        # JSON response format
        response_instruction = (
            "Respond in JSON format with the required fields. Ensure the response is valid JSON."
        )
    elif response_format == "json_schema":
        # JSON schema response format
        json_schema: JsonSchema = data.response_format.json_schema or {}
        schema_name = json_schema.name or ""
        schema_description = json_schema.description or ""
        schema = json.dumps(json_schema.schema or {}, indent=2)
        schema_is_strict = json_schema.strict or False
        if schema_is_strict:
            response_instruction = (
                f"Respond in strict JSON format adhering to the schema '{schema_name}'. "
                f"Description: {schema_description}. "
                f"Schema:\n{schema}\n"
                "The response MUST exactly match the schema structure with no additional fields. "
                "Ensure the response is valid JSON."
            )
        else:
            response_instruction = (
                f"Respond in JSON format following the schema '{schema_name}'. "
                f"Description: {schema_description}. "
                f"Schema: {schema}. "
                "Additional fields are allowed but all required fields must be present. "
                "Ensure the response is valid JSON."
            )

    # Fill in the system prompt template
    if tool_use_prompt:
        system_prompt = SYSTEM_PROMPT_TEMPLATE_WITH_TOOLS.format(
            tools=tool_use_prompt,
            instructions=system_prompt,
            guidelines=guidelines,
            parallel_tool_call_instruction=parallel_tool_call_instruction,
            response_instruction=response_instruction
        )
    else:
        system_prompt = SYSTEM_PROMPT_TEMPLATE_WITHOUT_TOOLS.format(
            instructions=system_prompt,
            guidelines=guidelines,
            response_instruction=response_instruction
        )

    # Initialize serialized message
    serialized = (
        f"{BEGIN_OF_TEXT}"
        f"{START_HEADER}{message.role}{END_HEADER}"
        f"{system_prompt}{END_OF_TURN}"
    )

    # Loop through non 'system' messages and serialize each one
    for message in messages:
        # skip system and developer messages
        if message.role == "system" or message.role == "developer":
            continue

        # Prepare role for serialization
        if message.role in ["assistant", "tool"]:
            role = "assistant"
        elif message.role in ["user"]:
            role = "user"
        else:
            logger.warning(
                f"Unknown role '{message.role}' in message, defaulting to 'user'.")
            role = message.role

        # Serialize the message content
        serialized += (
            f"{START_HEADER}{role}{END_HEADER}"
            f"{message.content}"
            f"{END_OF_TURN}"
        )

    # Add assistant header for AI to respond
    serialized += f"{START_HEADER}assistant{END_HEADER}"

    return serialized
