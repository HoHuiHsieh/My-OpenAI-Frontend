# -*- coding: utf-8 -*-
"""
"""
import json
import asyncio
import time
import uuid
from typing import Dict, List, Any, AsyncGenerator
from fastapi.responses import StreamingResponse

from logger import get_logger, UsageLogger
from .triton_client import (
    _setup_triton_stream,
    collect_stream_response
)
from .typedef import (
    ChatMessage,
    ChatCompletionChunkChoice,
    CreateChatCompletionChunkResponse,
    UsageInfo,
    ToolCall
)
from .tool_calls import extract_tool_calls_from_text
from .token_counter import get_default_model, create_usage_info, extract_tool_call_text, count_tokens

# Set up logger for this module
logger = get_logger(__name__)


async def handle_streaming_response(triton_client, model_name, inputs, outputs, model, body=None, user_id=""):
    """Handle streaming responses.

    Args:
        triton_client: The Triton client
        model_name: Name of the model
        inputs: The prepared inputs for Triton
        outputs: The requested outputs from Triton
        model: The model identifier for response generation
        body: The original request body (optional)
        n: Number of completions to generate (default: 1)

    Returns:
        A streaming response
    """
    # For streaming we need to generate one response at a time since parallelizing
    # would make the stream confusing to clients
    stream_callback = await _setup_triton_stream(triton_client, model_name, inputs, outputs)

    # Get the complete response content from the stream
    complete_response = await collect_stream_response(stream_callback, triton_client)

    # Prepare response data with model information
    response_data = {
        "model": model,
        "content": complete_response,
        # Include request body for tool call context
        "request_body": body.model_dump() if body else None
    }

    return StreamingResponse(
        stream_generator(
            response_data,
            body.parallel_tool_calls if body else True,
            user_id=user_id
        ),
        media_type="text/event-stream"
    )


async def estimate_tool_call_tokens(tool_calls: List[ToolCall], model: str = None) -> int:
    """
    Estimate the token count for tool calls.
    For streaming, we use a simple estimate to avoid too many token count API calls.

    Args:
        tool_calls: List of tool call objects
        model: Optional model name for token counting

    Returns:
        Estimated token count
    """
    if not tool_calls:
        return 0

    try:

        tool_call_text = await extract_tool_call_text(tool_calls)
        if not tool_call_text:
            return 0

        # Use provided model or default
        model_name = model if model else get_default_model()
        token_count = await count_tokens(model_name, tool_call_text)
        return token_count
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.warning(f"Error estimating tool call tokens: {e}")
        # Fallback: rough estimate based on character count
        return sum(len(str(call.model_dump())) // 4 for call in tool_calls)


async def stream_generator(
        response_data: Dict[str, Any],
        parallel_tool_calls: bool = True,
        user_id: str = ""
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming chat completions.

    Args:
        response_data: The data to stream back to the client

    Yields:
        Chunks of the response in SSE format
    """
    model = response_data.get("model", "unknown")
    completion_id = response_data.get("id", f"chatcmpl-{uuid.uuid4().hex}")
    created = int(time.time())
    request_body = response_data.get("request_body", {})

    # Start with a header - empty choices array for initial chunk
    # Get input_text from request_body for token counting if available
    input_text = ""
    if request_body and "messages" in request_body:
        for msg in request_body.get("messages", []):
            if isinstance(msg, dict) and msg.get("content"):
                input_text += msg.get("content", "") + "\n"

    header = CreateChatCompletionChunkResponse(
        id=completion_id,
        created=created,
        model=model,
        choices=[],
    )
    yield f"data: {json.dumps(header.model_dump())}\n\n"

    # Generate the content in small chunks
    content = response_data.get("content", "")
    words = content.split()

    # Keep track of accumulated content
    accumulated_content = ""
    # Check for tool calls only at the end
    check_for_tool_calls = request_body and request_body.get("tools")

    for i, word in enumerate(words):
        # Add to accumulated content
        current_word = word + (" " if i < len(words) - 1 else "")
        accumulated_content += current_word

        # Create a Delta ChatMessage for each chunk
        delta = ChatMessage(
            role="assistant",
            content=current_word
        )

        # Create a ChatCompletionChunkChoice
        choice = ChatCompletionChunkChoice(
            index=0,
            delta=delta,
            # Empty until final determination
            finish_reason="" if i < len(words) - 1 else ""
        )

        # Create the chunk response without usage info for intermediate chunks
        chunk_data = CreateChatCompletionChunkResponse(
            id=completion_id,
            created=created,
            model=model,
            choices=[choice],
        )

        yield f"data: {json.dumps(chunk_data.model_dump())}\n\n"
        await asyncio.sleep(0.01)  # Small delay between chunks

    # After streaming the content, compute usage and check for tool calls
    # Get prompt tokens count for final usage info
    prompt_tokens = 0
    completion_token_count = len(words)
    tool_token_estimate = 0

    if input_text:
        try:
            # Use the actual model for token counting
            model_name = model if model and model != "unknown" else get_default_model()
            # Get accurate token counts for the complete response
            usage_info = await create_usage_info(
                model=model_name,
                input_text=input_text,
                completion=accumulated_content,
                tool_calls=None,
                request_id=completion_id
            )
            prompt_tokens = usage_info.prompt_tokens
        except Exception as e:
            logger.warning(f"Failed to count prompt tokens: {e}")

    # Now check for tool calls in the complete accumulated content
    tool_calls = None
    finish_reason = "stop"
    cleaned_text = accumulated_content.strip()
    if check_for_tool_calls:
        detected_tool_calls, cleaned_text, has_tool_calls = extract_tool_calls_from_text(
            accumulated_content, parallel_tool_calls=parallel_tool_calls)
        if has_tool_calls:
            tool_calls = detected_tool_calls
            finish_reason = "tool_calls"
            logger.info(
                f"Found {len(detected_tool_calls)} tool call(s) in complete response")

            # Estimate tool call tokens for final usage
            if tool_calls:
                tool_token_estimate = await estimate_tool_call_tokens(tool_calls, model)
                completion_token_count += tool_token_estimate

    # Send a final chunk with accurate usage info and tool calls if found
    final_delta = ChatMessage(
        role="assistant",
        content=cleaned_text,
        tool_calls=tool_calls
    ) if tool_calls else ChatMessage(
        role="assistant",
        content=cleaned_text
    )

    final_choice = ChatCompletionChunkChoice(
        index=0,
        delta=final_delta,
        finish_reason=finish_reason
    )

    final_chunk = CreateChatCompletionChunkResponse(
        id=completion_id,
        created=created,
        model=model,
        choices=[final_choice],
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_token_count,
            total_tokens=prompt_tokens + completion_token_count
        )
    )

    yield f"data: {json.dumps(final_chunk.model_dump())}\n\n"

    # End the stream
    yield "data: [DONE]\n\n"

    # Log usage information
    UsageLogger.log_chat_usage(
        user_id=user_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_token_count,
        total_tokens=prompt_tokens + completion_token_count,
        request_id=completion_id
    )
