"""
Streaming generator for Triton Inference Server responses.
This module handles streaming responses back to clients in SSE format.
"""

import json
import time
import uuid
import asyncio
from typing import List, AsyncGenerator, Optional, Tuple
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
from .token_counter import create_usage_info
from .stream_processor import StreamingResponseCallback, StreamProcessor, get_token_from_text

# Set up logger for this module
logger = get_logger(__name__)


class StreamGenerator(StreamProcessor):
    """
    Generator for streaming chat completions to clients.
    This class formats and yields responses in SSE format.
    """
    
    def __init__(
        self,
        stream_callback: StreamingResponseCallback,
        triton_client: grpcclient.InferenceServerClient,
        tokenizor_client: grpcclient.InferenceServerClient,
        model: str,
        text_input: str,
        tools: Optional[List[ToolCall]] = None,
        parallel_tool_calls: Optional[bool] = True,
        response_format: Optional[str] = 'text',
        timeout=60,
        stop_dict=[],
        max_tokens: Optional[int] = None,
        ignore_usage: Optional[bool] = False,
        request_id: Optional[str] = None
    ):
        """
        Initialize the stream generator.
        
        Args:
            stream_callback: The callback for handling streaming responses
            triton_client: The Triton client
            tokenizor_client: Client for tokenization
            model: Model name
            text_input: Input text for the model
            tools: List of available tools
            parallel_tool_calls: Whether to allow parallel tool calls
            response_format: Format of the response ('text' or 'json_object')
            timeout: Maximum time to wait for response completion
            stop_dict: List of stop sequences
            max_tokens: Maximum number of tokens to generate
            ignore_usage: Whether to ignore usage tracking
            request_id: The ID of the request for tracking
        """
        super().__init__(
            stream_callback=stream_callback,
            triton_client=triton_client,
            tokenizor_client=tokenizor_client,
            timeout=timeout,
            stop_dict=stop_dict,
            max_tokens=max_tokens,
            request_id=request_id
        )
        self.model = model
        self.text_input = text_input
        self.tools = tools
        self.parallel_tool_calls = parallel_tool_calls
        self.response_format = response_format
        self.ignore_usage = ignore_usage
        
    async def generate(self) -> AsyncGenerator[str, None]:
        """
        Generate streaming responses to be sent to clients.
        
        Yields:
            Response chunks in SSE format
        """
        try:
            # Initialize response
            accumulated_content = ""
            completion_id = f"chatcmpl-{uuid.uuid4().hex}"
            created = int(time.time())

            # Create and send header based on response format
            header = self._create_header(completion_id, created, accumulated_content)
            yield f"data: {json.dumps(header.model_dump())}\n\n"

            # Process the stream and collect chunks
            response_queue = await self.stream_callback.get_queue()
            tokens_buffer = []  # Buffer for tokens
            prefix_buffer = []  # Buffer for prefixes
            count = 0
            start_time = time.time()
            
            # Main streaming loop
            while time.time() - start_time < self.timeout:
                try:
                    # Check accumulated_content include stop sequences
                    if self.stop_dict and any(stop in accumulated_content for stop in self.stop_dict):
                        logger.warning(f"Detected stop sequence in accumulated content, stopping stream")
                        break
                    
                    # Check for max tokens limit
                    if self.max_tokens is not None and count >= self.max_tokens:
                        logger.info(f"Reached max_tokens limit: {self.max_tokens}, stopping stream")
                        break
                    
                    # Get next chunk with timeout
                    current_word = await asyncio.wait_for(response_queue.get(), 1.0)
                    
                    # Check stop conditions
                    if current_word is None or current_word.strip() in self.stop_dict:
                        break
                    
                    # Process token
                    token, prefix = get_token_from_text(current_word)
                    if token is not None:
                        logger.debug(f"Found incomplete UTF-8 character, buffering: {repr(current_word)}")
                        tokens_buffer.append(token)
                        if prefix:
                            prefix_buffer.append(prefix)
                        count += 1
                        continue
                    elif len(tokens_buffer) > 0:
                        current_word = ""
                        # Handle prefixes
                        if len(prefix_buffer) > 0:
                            current_word = prefix_buffer.pop(0)
                        # Decode tokens
                        current_word += self.tokenizor(tokens_buffer)
                        tokens_buffer.clear()
                    
                    # Add to accumulated content
                    accumulated_content += current_word
                    
                    # Create chunk response
                    delta = ChatMessage(
                        role="assistant",
                        content=current_word
                    )
                    choice = ChatCompletionChunkChoice(
                        index=0,
                        delta=delta,
                        finish_reason=""
                    )
                    chunk_data = CreateChatCompletionChunkResponse(
                        id=header.id,
                        created=header.created,
                        model=self.model,
                        choices=[choice],
                    )
                    
                    # Send the chunk
                    yield f"data: {json.dumps(chunk_data.model_dump())}\n\n"
                    count += 1
                
                except asyncio.TimeoutError:
                    if self.stream_callback.is_completed():
                        response_queue.task_done()
                        break
                    if time.time() - start_time > self.timeout / 2:
                        logger.warning(f"Still waiting for response after {time.time() - start_time:.1f}s")
            
            # Finalize the response
            accumulated_content = accumulated_content.strip()
            
            # Log truncated response
            log_text = accumulated_content[:100] + "..." if len(accumulated_content) > 100 else accumulated_content
            logger.info(f"Processed response text: {log_text}")
            
            # Check for tool calls
            tool_calls = []
            finish_reason = "stop"
            if isinstance(self.tools, list) and len(self.tools) > 0:
                detected_tool_calls, cleaned_text, has_tool_calls = extract_tool_calls_from_text(
                    accumulated_content, parallel_tool_calls=self.parallel_tool_calls
                )
                if has_tool_calls:
                    tool_calls = detected_tool_calls
                    finish_reason = "tool_calls"
                    logger.info(f"Found {len(detected_tool_calls)} tool call(s) in complete response")
            
            # Create final response
            final_delta = ChatMessage(
                role="assistant",
                content="",
                tool_calls=tool_calls
            )
            final_choice = ChatCompletionChunkChoice(
                index=0,
                delta=final_delta,
                finish_reason=finish_reason
            )
            
            # Calculate usage
            if not self.ignore_usage:
                from .token_counter import create_usage_info
                usage = await create_usage_info(
                    model=self.model,
                    input_text=self.text_input,
                    completion=accumulated_content,
                    tool_calls=tool_calls if len(tool_calls) > 0 else None,
                    request_id=header.id
                )
            else:
                from ..typedef import UsageInfo
                usage = UsageInfo(
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0
                )
            
            # Send final chunk
            final_chunk = CreateChatCompletionChunkResponse(
                id=header.id,
                created=header.created,
                model=self.model,
                choices=[final_choice],
                usage=usage
            )
            yield f"data: {json.dumps(final_chunk.model_dump())}\n\n"
            
        finally:
            # End the stream
            yield "data: [DONE]\n\n"
            self.cleanup_resources()
    
    def _create_header(self, completion_id: str, created: int, accumulated_content: str) -> CreateChatCompletionChunkResponse:
        """
        Create the response header based on response format.
        
        Args:
            completion_id: Unique ID for this completion
            created: Timestamp when the completion was created
            accumulated_content: Initial content for JSON format
            
        Returns:
            Header for the response
        """
        if self.response_format == 'json_object':
            # For JSON format, start with an opening brace
            accumulated_content = "{"
            header = CreateChatCompletionChunkResponse(
                id=completion_id,
                created=created,
                model=self.model,
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
                model=self.model,
                choices=[],
            )
            
        return header
        
    async def _process_stream(self, accumulated_content: str) -> tuple[str, int]:
        """
        Process the stream, yielding chunks as they become available.
        
        Args:
            accumulated_content: Initial content (empty or '{' for JSON)
            
        Returns:
            Tuple of (accumulated_content, token_count)
        """
        start_time = time.time()
        response_queue = await self.stream_callback.get_queue()
        tokens_buffer = []  # Buffer to store tokens for incomplete UTF-8 characters
        prefix_buffer = []  # Buffer to store prefixes
        count = 0
        
        while time.time() - start_time < self.timeout:
            # Get the next chunk
            current_word, should_break = await self._wait_for_chunk(response_queue, start_time, count)
            
            # Break if indicated (max tokens reached, stop sequence, etc.)
            if should_break:
                break
                
            # Skip if timeout occurred
            if current_word is None:
                continue
            
            # Process the token with both buffers
            processed_word, is_buffered = await self._process_token(current_word, tokens_buffer, prefix_buffer)
            
            # If we got some text to send, create and yield a chunk
            if processed_word:
                # Accumulate the processed word
                accumulated_content += processed_word
            
            # Increment token count
            count += 1
            
        return accumulated_content, count
        
    def _create_chunk_data(self, id: str, created: int, content: str) -> CreateChatCompletionChunkResponse:
        """
        Create a chunk response for the given content.
        
        Args:
            id: The completion ID
            created: Timestamp when the completion was created
            content: Content for this chunk
            
        Returns:
            A response chunk
        """
        # Create a Delta ChatMessage for this chunk
        delta = ChatMessage(
            role="assistant",
            content=content
        )
        
        # Create a ChatCompletionChunkChoice
        choice = ChatCompletionChunkChoice(
            index=0,
            delta=delta,
            finish_reason=""
        )
        
        # Create the chunk response without usage info
        return CreateChatCompletionChunkResponse(
            id=id,
            created=created,
            model=self.model,
            choices=[choice],
        )
        
    async def _finalize_response(self, header: CreateChatCompletionChunkResponse, accumulated_content: str) -> AsyncGenerator[str, None]:
        """
        Finalize the response with tool calls and usage info.
        
        Args:
            header: The response header
            accumulated_content: The accumulated content
            
        Yields:
            Final response chunk in SSE format
        """
        # Trim any whitespace
        accumulated_content = accumulated_content.strip()
        
        # Truncate long responses for logging
        log_text = accumulated_content[:100] + "..." if len(accumulated_content) > 100 else accumulated_content
        logger.info(f"Processed response text: {log_text}")
        
        # Check for tool calls
        tool_calls = []
        finish_reason = "stop"
        if isinstance(self.tools, list) and len(self.tools) > 0:
            detected_tool_calls, cleaned_text, has_tool_calls = extract_tool_calls_from_text(
                accumulated_content, parallel_tool_calls=self.parallel_tool_calls
            )
            if has_tool_calls:
                tool_calls = detected_tool_calls
                finish_reason = "tool_calls"
                logger.info(f"Found {len(detected_tool_calls)} tool call(s) in complete response")
        
        # Create the final delta and choice
        final_delta = ChatMessage(
            role="assistant",
            content="",
            tool_calls=tool_calls
        )
        
        final_choice = ChatCompletionChunkChoice(
            index=0,
            delta=final_delta,
            finish_reason=finish_reason
        )
        
        # Calculate usage info
        if not self.ignore_usage:
            usage = await create_usage_info(
                model=self.model,
                input_text=self.text_input,
                completion=accumulated_content,
                tool_calls=tool_calls if len(tool_calls) > 0 else None,
                request_id=header.id
            )
        else:
            usage = UsageInfo(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            )
        
        # Create and yield the final chunk
        final_chunk = CreateChatCompletionChunkResponse(
            id=header.id,
            created=header.created,
            model=self.model,
            choices=[final_choice],
            usage=usage
        )
        
        yield f"data: {json.dumps(final_chunk.model_dump())}\n\n"


async def stream_generator(
    stream_callback: StreamingResponseCallback,
    triton_client: grpcclient.InferenceServerClient,
    tokenizor_client: grpcclient.InferenceServerClient,
    model: str,
    text_input: str,
    tools: Optional[List[ToolCall]] = None,
    parallel_tool_calls: Optional[bool] = True,
    response_format: Optional[str] = 'text',
    timeout=60,
    stop_dict=[],
    max_tokens: Optional[int] = None,
    ignore_usage: Optional[bool] = False,
    request_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generator for streaming chat completions.
    
    This function maintains backward compatibility with the original API.
    
    Args:
        stream_callback: The callback for handling streaming responses
        triton_client: The Triton client
        tokenizor_client: Client for tokenization
        model: Model name
        text_input: Input text for the model
        tools: List of available tools
        parallel_tool_calls: Whether to allow parallel tool calls
        response_format: Format of the response ('text' or 'json_object')
        timeout: Maximum time to wait for response completion
        stop_dict: List of stop sequences
        max_tokens: Maximum number of tokens to generate
        ignore_usage: Whether to ignore usage tracking
        request_id: The ID of the request for tracking
        
    Yields:
        Chunks of the response in SSE format
    """
    generator = StreamGenerator(
        stream_callback=stream_callback,
        triton_client=triton_client,
        tokenizor_client=tokenizor_client,
        model=model,
        text_input=text_input,
        tools=tools,
        parallel_tool_calls=parallel_tool_calls,
        response_format=response_format,
        timeout=timeout,
        stop_dict=stop_dict,
        max_tokens=max_tokens,
        ignore_usage=ignore_usage,
        request_id=request_id
    )
    
    try:
        async for chunk in generator.generate():
            yield chunk
    except Exception as e:
        logger.error(f"Error in stream_generator: {e}")
        # Ensure resources are cleaned up even if an error occurs
        generator.cleanup_resources()
        # Re-raise the exception after cleanup
        raise
