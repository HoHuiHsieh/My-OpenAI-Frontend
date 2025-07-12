"""Response processing for chat completions."""
import json
import re
import uuid
import time
from typing import Dict, Any, List, Optional, Union

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
import numpy as np
import tritonclient.grpc as grpcclient

from logger import get_logger, UsageLogger
from ..typedef import (
    UsageInfo,
    ChatMessage,
    ChatCompletionChoice,
    CreateChatCompletionResponse,
    CreateChatCompletionRequest,
)
from .tool_calls import extract_tool_calls_from_text
from .token_counter import create_usage_info

# Set up logger for this module
logger = get_logger(__name__)


async def prepare_chat_completion_response(
    responses: List[grpcclient.InferResult],
    body: CreateChatCompletionRequest,
    text_input: str,
    ignore_usage: bool = False,
    request_id: str = None
) -> CreateChatCompletionResponse:
    """
    Prepare a ChatCompletionResponse from Triton Inference Server response.

    Args:
        triton_response: The response from Triton Inference Server
        model_name: The name of the model used
        request_data: Original request data for token counting (if available)
        current_user: The current user making the request
        request: The original FastAPI request object
        request_id: Optional request ID to use for the completion ID

    Returns:
        A formatted ChatCompletionResponse
    """
    # Process all successful responses into a single response with multiple choices
    # Use the provided request_id if available, otherwise generate a new one
    completion_id = f"chatcmpl-{request_id or uuid.uuid4().hex}"
    created_time = int(time.time())

    all_choices: List[ChatCompletionChoice] = []
    tool_calls_list = []

    # Process each response text
    for i, response_text in enumerate(responses):
        # Create a synthetic response object with a check for None
        synthetic_response = type('obj', (object,), {
            'as_numpy': lambda name: np.array([response_text.encode('utf-8')])
            if name == 'output' and response_text is not None
            else np.array([b"Error: No response generated"])
        })

        # Process the individual response to get the choice
        response_type = body.response_format.type if hasattr(
            body, 'response_format') and hasattr(body.response_format, 'type') else None
        choice = await process_triton_response(synthetic_response, response_type, body.parallel_tool_calls)
        choice.index = i  # Set the index for the choice
        all_choices.append(choice)

        # Collect tool calls for token counting
        if choice.message and choice.message.tool_calls:
            tool_calls_list.extend([t for t in choice.message.tool_calls])

    # Get actual completions to count
    completions: List[str] = []
    for choice in all_choices:
        if choice.message and isinstance(choice.message.content, str) and choice.message.content:
            completions.append(choice.message.content)
        elif choice.message and isinstance(choice.message.content, list):
            # If content is a list, join it into a single string
            completions.append(' '.join(choice.message.content))

    # Create an accurate usage info with token counting - use completion_id as request_id for independent tracking
    if not ignore_usage:
        usage = await create_usage_info(
            model=body.model,
            input_text=text_input,
            completion=completions,
            tool_calls=tool_calls_list if len(tool_calls_list) > 0 else None,
            request_id=completion_id
        )
    else:
        usage = UsageInfo(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0
        )

    # Create the final response
    return CreateChatCompletionResponse(
        id=completion_id,
        created=created_time,
        model=body.model,
        choices=all_choices,
        usage=usage
    )


async def process_triton_response(
        response: grpcclient.InferResult,
        response_format: Optional[str] = "text",
        parallel_tool_calls: Optional[bool] = True,
) -> ChatCompletionChoice:
    """
    Process the response from Triton Inference Server.
    """
    try:
        # Extract the output tensor data
        output_tensor = response.as_numpy("output")
        if output_tensor is None:
            logger.error("Failed to get output tensor from Triton response")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process model output"
            )

        # Assume the output is a string tensor that needs to be decoded
        response_text = str(output_tensor[0].decode("utf-8", errors="replace"))

        # Truncate long responses for logging
        log_text = response_text[:100] + \
            "..." if len(response_text) > 100 else response_text
        logger.info(f"Processed response text: {log_text}")

        # Check for output format errors (common with LLM outputs)
        response_text = response_text.strip()

        # Check if JSON format is required and ensure the response starts with '{'
        if (response_format == 'json_object'):
            # Ensure response starts with '{' for JSON format
            if not response_text.startswith('{"name":'):
                response_text = '{\n"name":' + response_text
            # If the response doesn't end with '}', add it
            if not response_text.endswith('}'):
                response_text = response_text + '}'

            logger.debug("Adjusted response for JSON format compatibility")

        # Try to extract finish reason from model response if included
        finish_reason = "stop"
        if "<finish_reason>" in response_text.lower():
            # Some models return finish_reason as part of their output
            try:
                finish_marker = "<finish_reason>"
                if finish_marker in response_text.lower():
                    parts = response_text.lower().split(finish_marker)
                    if len(parts) > 1:
                        possible_reason = parts[1].strip().split()[0].strip()
                        if possible_reason in ["stop", "length", "content_filter"]:
                            finish_reason = possible_reason
                            # Remove the marker from the response
                            response_text = response_text.replace(
                                f"{finish_marker}{possible_reason}", "").strip()
            except Exception:
                # If parsing fails, keep default finish_reason
                pass

        # Check for ToolCall objects embedded in the response_text
        tool_calls, cleaned_text, has_tool_calls = extract_tool_calls_from_text(
            response_text,
            parallel_tool_calls=parallel_tool_calls
        )

        if has_tool_calls:
            # response_text = cleaned_text
            # Update finish_reason to tool_calls if we found tool calls
            finish_reason = "tool_calls"
            logger.info(
                f"Extracted {len(tool_calls)} tool calls from response")

        # Create the ChatCompletionChoice
        return ChatCompletionChoice(
            index=0,
            message=ChatMessage(
                role="assistant",
                content=response_text,
                tool_calls=tool_calls if has_tool_calls else None
            ),
            finish_reason=finish_reason
        )

    except Exception as e:
        logger.error(f"Error processing Triton response: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing model response: {str(e)}"
        )
