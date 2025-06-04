# -*- coding: utf-8 -*-
"""
"""
import json
import asyncio
import time
import uuid
from typing import List, Any, AsyncGenerator, Optional
from logger import get_logger

from ..typedef import (
    ChatMessage,
    ChatCompletionChunkChoice,
    CreateChatCompletionChunkResponse,
    UsageInfo,
    ToolCall
)
from .tool_calls import extract_tool_calls_from_text
from .token_counter import get_default_model, create_usage_info

# Set up logger for this module
logger = get_logger(__name__)


async def stream_generator(
        content: Any,
        model: str,
        text_input: str,
        tools: Optional[List[ToolCall]] = None,
        parallel_tool_calls: Optional[bool] = True,
        response_format: Optional[str] = 'text',
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming chat completions.

    Args:
        response_data: The data to stream back to the client

    Yields:
        Chunks of the response in SSE format
    """
    # Stream header with model information
    header = CreateChatCompletionChunkResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=model,
        choices=[],
    )
    yield f"data: {json.dumps(header.model_dump())}\n\n"

    # Generate the content in small chunks
    words = content.split()

    # Keep track of accumulated content
    accumulated_content = ""

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
            finish_reason="" if i < len(words) - 1 else ""
        )

        # Create the chunk response without usage info for intermediate chunks
        chunk_data = CreateChatCompletionChunkResponse(
            id=header.id,
            created=header.created,
            model=header.model,
            choices=[choice],
        )

        yield f"data: {json.dumps(chunk_data.model_dump())}\n\n"
        await asyncio.sleep(0.005)  # Small delay between chunks

    # Finalize the last chunk with accumulated content
    accumulated_content = accumulated_content.strip()

    # Check if JSON format is required and ensure the response starts with '{'
    if (response_format == 'json_object'):
        # Ensure response starts with '{' for JSON format
        if not accumulated_content.startswith('{'):
            accumulated_content = '{' + accumulated_content
        # If the response doesn't end with '}', add it
        if not accumulated_content.endswith('}'):
            accumulated_content = accumulated_content + '}'

        logger.debug("Adjusted response for JSON format compatibility")

    # Truncate long responses for logging
    log_text = accumulated_content[:100] + \
        "..." if len(accumulated_content) > 100 else accumulated_content
    logger.info(f"Processed response text: {log_text}")

    # Now check for tool calls in the complete accumulated content
    cleaned_text = accumulated_content
    tool_calls = []
    finish_reason = "stop"
    if isinstance(tools, list) and len(tools) > 0:
        # If tools are provided, check for tool calls in the accumulated content
        detected_tool_calls, cleaned_text, has_tool_calls = extract_tool_calls_from_text(
            accumulated_content, parallel_tool_calls=parallel_tool_calls)
        if has_tool_calls:
            tool_calls = detected_tool_calls
            finish_reason = "tool_calls"
            logger.info(
                f"Found {len(detected_tool_calls)} tool call(s) in complete response")

    # Create the final ChatCompletionChunkChoice
    final_delta = ChatMessage(
        role="assistant",
        content=cleaned_text if len(tool_calls) == 0 else "",
        tool_calls=tool_calls
    ) if len(tool_calls) > 0 else ChatMessage(
        role="assistant",
        content=cleaned_text
    )

    # Create the final choice with finish reason
    final_choice = ChatCompletionChunkChoice(
        index=0,
        delta=final_delta,
        finish_reason=finish_reason
    )

    # Create an accurate usage info with token counting
    usage = await create_usage_info(
        model=model,
        input_text=text_input,
        completion=accumulated_content,
        tool_calls=tool_calls if len(tool_calls) > 0 else None,
        request_id=header.id
    )

    # Create the final chunk response with usage info
    final_chunk = CreateChatCompletionChunkResponse(
        id=header.id,
        created=header.created,
        model=model,
        choices=[final_choice],
        usage=usage
    )

    # Send a final chunk
    yield f"data: {json.dumps(final_chunk.model_dump())}\n\n"

    # End the stream
    yield "data: [DONE]\n\n"
