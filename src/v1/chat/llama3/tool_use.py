import json
from ..models.request import (
    Tool,
    ChatCompletionRequest
)

from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


def create_tool_use_prompt(data: ChatCompletionRequest) -> str:
    """
    Create a prompt for tool use based on the provided tools.
    """
    logger.debug("Creating tool use prompt")

    # Get tools from the request data
    tools = data.tools or []
    tool_choice = data.tool_choice

    # If tools is empty, return an empty string
    if not tools:
        logger.debug("Tools list is empty")
        return ""

    #
    if isinstance(tool_choice, str):
        # If tool_choice is a string, check if it is 'none'
        if tool_choice == "none":
            logger.debug("Tool choice is 'none', returning empty prompt")
            return ""

    elif hasattr(tool_choice, 'function'):
        # If tool_choice is an object with a function attribute, get the function name
        if tool_choice.function and hasattr(tool_choice.function, 'name'):
            tool_name = tool_choice.function.name
        else:
            logger.error("Tool choice function name is not provided")
            return ""

        tools = [tool
                 for tool in tools if tool.function and tool.function.name == tool_name]

    else:
        # If tool_choice is not a string or an object with a function, log an error
        logger.error(
            f"Invalid tool choice type: {type(tool_choice)}. Expected str or Tool instance.")
        return ""

    # loop through tools and create a prompt
    tool_prompts = []
    for index, tool in enumerate(tools):
        # Validate tool instance
        if not isinstance(tool, Tool) or not tool.function:
            logger.error(
                f"Invalid tool type: {type(tool)}. Expected Tool instance.")
            continue

        #  Get tool attributes
        tool_function = tool.function
        tool_name = tool_function.name or ""
        tool_description = tool_function.description or "No description provided"
        tool_properties = tool_function.parameters.properties or {}
        is_strict = tool_function.strict or False

        # Validate tool parameters
        if not tool_name:
            logger.error(
                f"Invalid tool name: {type(tool_name)}. Expected str.")
            continue

        if not isinstance(tool_properties, dict):
            logger.error(
                f"Invalid tool parameters type: {type(tool_properties)}. Expected dict.")
            continue

        # Create tool property prompts
        tool_property_prompts = []
        for key, value in tool_properties.items():
            prop_type = value.type
            prop_description = value.description or "No description provided"
            prop_enum = value.enum
            # If the property is an enum
            if prop_enum:
                prop_enum = ", ".join(prop_enum)
                tool_property_prompts.append(
                    f"  - {key} ({prop_type}): Select one of {prop_enum}."
                )
                continue
            # If the property is a simple type
            tool_property_prompts.append((
                f"  - {key} ({prop_type}): {prop_description}."
            ))
        tool_property_prompts = "\n".join(tool_property_prompts)

        # initialize prompt
        if is_strict:
            required_parameters = [key for key in tool_properties.keys()]
            required_parameters = ", ".join(required_parameters)
            required_parameters = f"Required: {required_parameters}\n"
        else:
            required_parameters = ""

        tool_prompt = (
            f"{index + 1}: **{tool_name}**: {tool_description}\n"
            f"  Arguments:\n{tool_property_prompts}"
        )

        # Append tool prompt to list
        tool_prompts.append(tool_prompt)

    # Join all tool prompts into a single string
    full_prompt = "\n".join(tool_prompts)
    logger.debug(f"Full tool use prompt created: {full_prompt}")

    return full_prompt
