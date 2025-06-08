# -*- coding: utf-8 -*-
"""
"""
import json
import asyncio
import time
import uuid
from typing import List, Any, AsyncGenerator, Optional
from logger import get_logger
import tritonclient.grpc as grpcclient
from ..typedef import (
    ChatMessage,
    ChatCompletionChunkChoice,
    CreateChatCompletionChunkResponse,
    UsageInfo,
    ToolCall
)
from .tool_calls import extract_tool_calls_from_text
from .token_counter import get_default_model, create_usage_info
from .inference import StreamingResponseCallback

# Set up logger for this module
logger = get_logger(__name__)


def is_incomplete_unicode(byte_string, encoding='utf-8'):
    try:
        # print(byte_string, byte_string.decode(encoding))
        byte_string.decode(encoding)
        return False  # Decoding successful, not incomplete
    except UnicodeDecodeError:
        return True   # Decoding failed, likely incomplete


async def stream_generator(
        stream_callback: StreamingResponseCallback,
        triton_client: grpcclient.InferenceServerClient,
        model: str,
        text_input: str,
        tools: Optional[List[ToolCall]] = None,
        parallel_tool_calls: Optional[bool] = True,
        response_format: Optional[str] = 'text',
        timeout=60,
        stop_dict=[]
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming chat completions.

    Args:
        response_data: The data to stream back to the client

    Yields:
        Chunks of the response in SSE format
    """
    if not isinstance(stop_dict, list):
        stop_dict = []

    accumulated_content = ""
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    # Stream header with model information
    # Check if JSON format is required and ensure the response starts with '{'
    if (response_format == 'json_object'):
        accumulated_content = "{"
        header = CreateChatCompletionChunkResponse(
            id=completion_id,
            created=created,
            model=model,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatMessage(
                        role="assistant",
                        content=accumulated_content
                    ),
                    finish_reason=""
                )
            ],
        )
        logger.debug("Adjusted response for JSON format compatibility")

    else:
        header = CreateChatCompletionChunkResponse(
            id=completion_id,
            created=created,
            model=model,
            choices=[],
        )

    # Send the initial header chunk
    yield f"data: {json.dumps(header.model_dump())}\n\n"

    # Keep track of accumulated content
    start_time = time.time()
    response_queue = await stream_callback.get_queue()
    incomplete_char_buffer = ""  # Buffer to store incomplete UTF-8 characters
    
    while time.time() - start_time < timeout:
        try:
            # Wait for the next chunk from the response queue
            current_word: str = await asyncio.wait_for(response_queue.get(), 1.0)

            # Check if the current word is None or in the stop dictionary
            if current_word is None or current_word.strip() in stop_dict:
                break
            
            # Check for incomplete UTF-8 characters
            if incomplete_char_buffer:
                current_word = incomplete_char_buffer + current_word
                incomplete_char_buffer = ""
            
            # Check if current_word might end with an incomplete UTF-8 character
            if is_incomplete_unicode(current_word.encode('utf-8')):
                logger.warning(f"Found incomplete UTF-8 character, buffering: {repr(current_word)}")
                incomplete_char_buffer = current_word
                response_queue.task_done()
                continue

            # Continue with the rest of the stream processing
            #  Accumulate the current word into the accumulated content
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
                finish_reason=""
            )

            # Create the chunk response without usage info for intermediate chunks
            chunk_data = CreateChatCompletionChunkResponse(
                id=header.id,
                created=header.created,
                model=header.model,
                choices=[choice],
            )

            yield f"data: {json.dumps(chunk_data.model_dump())}\n\n"

        except asyncio.TimeoutError:
            if stream_callback.is_completed():
                response_queue.task_done()
                break
            if time.time() - start_time > timeout / 2:
                logger.warning(
                    f"Still waiting for response after {time.time() - start_time:.1f}s")

    # Finalize the last chunk with accumulated content
    accumulated_content = accumulated_content.strip()

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
        content="",
        tool_calls=tool_calls
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
