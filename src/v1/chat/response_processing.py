"""Response processing for chat completions."""
import json
import re
import uuid
import time
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
import numpy as np

from logger import get_logger, UsageLogger
from .typedef import (
    ChatMessage, 
    ChatCompletionChoice, 
    CreateChatCompletionResponse,
    UsageInfo,
    ToolCall,
    ToolCallFunction
)
from .tool_calls import extract_tool_calls_from_text
from .token_counter import create_usage_info

# Set up logger for this module
logger = get_logger(__name__)

async def process_triton_response(triton_response: Any, model_name: str, request_data: dict = None, current_user=None, request=None) -> CreateChatCompletionResponse:
    """
    Process the response from Triton Inference Server.

    Args:
        triton_response: The response from Triton Inference Server
        model_name: The name of the model used
        request_data: Original request data for token counting (if available)
        current_user: The current user making the request
        request: The original FastAPI request object

    Returns:
        A formatted ChatCompletionResponse
    """
    try:
        # Extract the output tensor data
        output_tensor = triton_response.as_numpy("output")
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
        if (request_data and request_data.get('response_format') and
            (isinstance(request_data['response_format'], dict) and
             request_data['response_format'].get('type') == 'json_object' or
             hasattr(request_data['response_format'], 'type') and
             request_data['response_format'].type == 'json_object')):
            # Ensure response starts with '{' for JSON format
            if not response_text.startswith('{'):
                response_text = '{' + response_text
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
        tool_calls, cleaned_text, has_tool_calls = extract_tool_calls_from_text(response_text, parallel_tool_calls=request_data.get('parallel_tool_calls'))
        
        if has_tool_calls:
            response_text = cleaned_text
            # Update finish_reason to tool_calls if we found tool calls
            finish_reason = "tool_calls"
            logger.info(f"Extracted {len(tool_calls)} tool calls from response")

        # Create the ChatCompletionChoice
        choice = ChatCompletionChoice(
            index=0,
            message=ChatMessage(
                role="assistant",
                content=response_text,
                tool_calls=tool_calls if has_tool_calls else None
            ),
            finish_reason=finish_reason
        )

        # Get accurate token counts using the token_counter module
        input_text = ""
        if request_data and "messages" in request_data:
            # Concatenate all messages for token counting
            for msg in request_data.get("messages", []):
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if content:
                        input_text += content + "\n"
        
        # Use the tool calls in token counting if present
        tool_calls_list = tool_calls if has_tool_calls else None
        # Get request_id if available to ensure independent token counting per request
        request_id = str(request.state.request_id) if request and hasattr(request.state, "request_id") else None
        usage = await create_usage_info(
            model=model_name,
            input_text=input_text,
            completion=response_text,
            tool_calls=tool_calls_list,
            request_id=request_id
        )

        # Log usage information if user data is available
        if current_user and hasattr(current_user, 'username'):
            UsageLogger.log_chat_usage(
                user_id=current_user.username,
                model=model_name,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                request_id=str(request.state.request_id) if request and hasattr(request.state, "request_id") else None,
                extra={
                    "endpoint": "/v1/chat/completion", 
                    "stream": request_data.get("stream", False) if request_data else False,
                    "has_tool_calls": has_tool_calls
                }
            )

        # Create and return the full response
        response = CreateChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            model=model_name,
            choices=[choice],
            usage=usage
        )

        return response

    except Exception as e:
        logger.error(f"Error processing Triton response: {str(e)}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing model response: {str(e)}"
        )
