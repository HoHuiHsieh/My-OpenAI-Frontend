# -*- coding: utf-8 -*-

import json
from time import time
import asyncio
import uuid
from typing import List, Union, AsyncGenerator, Callable
from tritonclient.utils import InferenceServerException
from logger import get_logger
from config import get_config
from ...models import (ChatCompletionRequest,
                       ChatCompletionResponse,
                       ChatCompletionStreamResponse,
                       )
from ...models.response import (ChatCompletionChoice, ChatCompletionStreamChoice,
                                ChatCompletionStreamMessage, Usage, ChatCompletionMessage)
from ..llama3 import serialize_message as serialize_llama3_messages
from .connection import TritonClient
from .util import extract_tool_calls_from_text, log_chat_api_usage


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration
try:
    config = get_config()
    chat_models = config.get_models_by_type("chat:base")
except Exception as e:
    logger.error(f"Failed to load available models: {e}")
    raise RuntimeError("Configuration loading failed") from e


def _get_serialize_function(data: ChatCompletionRequest) -> str:
    """
    Serialize a message for a specific model.
    """
    # Get the model name from the request
    model_name = data.model.split("/")[-1]
    # Check if the model is supported
    if model_name.lower() in ["llama-3.3-70b-instruct", "llama-3.1-8b-instruct", "llama-3.1-70b-instruct"]:
        return serialize_llama3_messages(data)

    raise ValueError(f"Unsupported model: {model_name}")


def _prepare_triton_inputs(triton_client: TritonClient, data: ChatCompletionRequest, serialized_message: str):
    """
    Prepare Triton inputs based on the request data.
    """
    # Prepare inputs to the format expected by Triton
    triton_client = triton_client.set_input(
        "text_input", [serialized_message.encode('utf-8')], "BYTES")

    if data.max_completion_tokens is not None:
        triton_client = triton_client.set_input(
            "max_tokens", [data.max_completion_tokens], "INT32")

    if data.stop is not None:
        if isinstance(data.stop, str):
            triton_client = triton_client.set_input(
                "stop_words", [data.stop], "BYTES")
        elif isinstance(data.stop, list):
            triton_client = triton_client.set_input(
                "stop_words", data.stop, "BYTES")

    if data.temperature is not None:
        triton_client = triton_client.set_input(
            "temperature", [data.temperature], "FP32")

    if data.top_p is not None:
        triton_client = triton_client.set_input("top_p", [data.top_p], "FP32")

    if data.presence_penalty is not None:
        triton_client = triton_client.set_input("presence_penalty",
                                                [data.presence_penalty], "FP32")

    if data.frequency_penalty is not None:
        triton_client = triton_client.set_input("frequency_penalty",
                                                [data.frequency_penalty], "FP32")

    if data.stream is True:
        triton_client = triton_client.set_input("stream", [True], "BOOL")

    random_seed = int(time())
    triton_client = triton_client.set_input(
        "random_seed", [random_seed], "UINT64")

    return triton_client


def _count_tokens(text: str, triton_client: TritonClient) -> int:
    """
    Count the number of tokens in a given text.
    """
    # Clear previous inputs and outputs
    triton_client.inputs.clear()
    triton_client.outputs.clear()

    # Prepare inputs to the format expected by Triton
    text_input = text.encode('utf-8')
    triton_client = triton_client.set_input("prompt", [text_input], "BYTES")

    # Prepare outputs to the format expected by Triton
    triton_client = triton_client.set_output("num_tokens")

    # Send inference request
    try:
        # Send inference request to count tokens
        num_tokens = triton_client.client.infer(
            model_name="counter",
            inputs=triton_client.inputs,
            outputs=triton_client.outputs,
            request_id=uuid.uuid4().hex[:8]
        ).as_numpy("num_tokens")[0]
        return int(num_tokens)
    except InferenceServerException as e:
        logger.error(f"Error counting tokens: {e}")
        raise RuntimeError("Failed to count tokens") from e


async def query_chat_completion(data: ChatCompletionRequest, user_id=None, apiKey="") -> ChatCompletionResponse:
    """
    Query chat completion from the configured Triton server.
    """
    # Check if the model exists in the configuration
    model_name = data.model.split("/")[-1]
    target_model = chat_models.get(model_name)
    if not target_model:
        logger.error(f"Model {data.model} not found in configuration")
        raise ValueError(f"Model {data.model} not found in configuration")

    # Get the serialized message based on the model
    serialized_message = _get_serialize_function(data)

    # Prepare response format
    prefix = ""
    if data.response_format.type == "json":
        # JSON response format
        prefix = "[\n  {\n    \"name\": \""
    elif data.response_format.type == "json_schema":
        # JSON schema response format
        prefix = "```json\n"

    serialized_message += prefix

    # Prepare request ID for the inference
    request_id = f"req_{uuid.uuid4().hex}"

    # Send inference request in parallel
    tasks, clients = [], []
    for i in range(data.n or 1):
        # Prepare Triton client
        triton_client = TritonClient(
            host=target_model.host,
            port=target_model.port,
            api_key=apiKey
        ).get_client()

        # Prepare inputs to the format expected by Triton
        triton_client = _prepare_triton_inputs(triton_client,
                                               data,
                                               serialized_message)

        # Prepare outputs to the format expected by Triton
        triton_client = triton_client.set_output("text_output")

        # Create inference request task
        task = asyncio.create_task(
            triton_client.infer(model_name=model_name,
                                request_id=f"{request_id}_{i}")
        )
        clients.append(triton_client)
        tasks.append(task)

    # Wait for all tasks to complete
    responses: List[str] = await asyncio.gather(*tasks)
    responses = [prefix + res for res in responses if res is not None]

    # Extract tool calls from responses
    tool_calls = [
        extract_tool_calls_from_text(res, data.parallel_tool_calls)
        for res in responses
    ] or None

    # Get the usage
    prompt_tokens = _count_tokens(serialized_message, triton_client)
    completion_tokens = sum([_count_tokens(text, triton_client)
                            for text in responses])
    total_tokens = prompt_tokens + completion_tokens
    log_chat_api_usage(
        request_id=request_id,
        user_id=user_id,
        model=data.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )

    # Return the chat completion response
    return ChatCompletionResponse(
        model=data.model,
        choices=[
            ChatCompletionChoice(
                index=i + 1,
                message=ChatCompletionMessage(
                    role="assistant",
                    content=text,
                    tool_calls=tool_calls[i]
                ),
                finish_reason="stop"
            ) for i, text in enumerate(responses)
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens
        ),
    )


async def query_streaming_chat_completion(data: ChatCompletionRequest, user_id=None, apiKey="") -> AsyncGenerator[str, None]:
    """
    Query chat completion in streaming mode.
    """
    # Check if the model exists in the configuration
    model_name = data.model.split("/")[-1]
    target_model = chat_models.get(model_name)
    if not target_model:
        logger.error(f"Model {data.model} not found in configuration")
        raise ValueError(f"Model {data.model} not found in configuration")

    # Get the serialized message based on the model
    serialized_message = _get_serialize_function(data)

    # Prepare response format
    prefix = ""
    if data.response_format.type == "json":
        # JSON response format
        prefix = "[\n  {\n    \"name\": \""
    elif data.response_format.type == "json_schema":
        # JSON schema response format
        prefix = "```json\n"

    serialized_message += prefix

    # Prepare Triton client
    triton_client = TritonClient(
        host=target_model.host,
        port=target_model.port,
        api_key=apiKey
    ).get_client()

    # Prepare inputs to the format expected by Triton
    triton_client = _prepare_triton_inputs(triton_client,
                                           data,
                                           serialized_message)

    # Prepare Tokenizor client
    tokenizor_client = TritonClient(
        host=target_model.host,
        port=target_model.port,
        api_key=apiKey
    ).get_client()

    # Prepare outputs to the format expected by Triton
    triton_client = triton_client.set_output("text_output")

    # Send prefix to the stream if applicable
    if prefix:
        # Create a streaming response chunk
        chunk_response = ChatCompletionStreamResponse(
            model=data.model,
            choices=[
                ChatCompletionStreamChoice(
                    index=1,
                    delta=ChatCompletionStreamMessage(
                        role="assistant",
                        content=prefix
                    ),
                )
            ],
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
        ).model_dump_json(exclude_none=True)

        # Yield the prefix as a streaming response chunk
        yield f"data: {chunk_response}\n\n"

    # Prepare request ID for the inference
    request_id = f"req_{uuid.uuid4().hex}"

    # Collect all response chunks
    collected_chunks = [prefix]
    try:
        # Start async inference
        stream_callback = await triton_client.async_infer(model_name=model_name, request_id=request_id)

        # Stream the responses as they come
        timeout = 60
        start_time = asyncio.get_event_loop().time()
        tokens_buffer = []

        while not stream_callback.is_completed():
            # Check for timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                triton_client.client.stop_stream()
                raise InferenceServerException("Streaming inference timeout")

            # Check for errors
            if stream_callback.error:
                triton_client.client.stop_stream()
                raise InferenceServerException(
                    f"Streaming error: {stream_callback.error}")

            # Try to get response from queue
            try:
                # Get the next response chunk from the queue
                response_chunk: str = await asyncio.wait_for(
                    stream_callback.response_queue.get(),
                    timeout=0.2
                )

                # Check if the response chunk is None (end of stream)
                if response_chunk is None:
                    break

                # Buffer incompleted token
                if response_chunk.startswith("t'"):
                    # Buffer the token
                    tokens_buffer.append(int(response_chunk[2:-1]))
                    continue  # Buffer chunks
                elif tokens_buffer:
                    # Clear previous inputs and outputs
                    tokenizor_client.inputs.clear()
                    tokenizor_client.outputs.clear()
                    # Process buffered tokens
                    logger.debug(
                        f"Processing buffered tokens: {tokens_buffer}")
                    tokenizor_client.set_input("tokens", tokens_buffer,
                                               "INT32", [len(tokens_buffer)])
                    tokenizor_client.set_output("output")
                    completed_chunk = tokenizor_client.client.infer(
                        model_name="tokenizer",
                        inputs=tokenizor_client.inputs,
                        outputs=tokenizor_client.outputs,
                        request_id=uuid.uuid4().hex[:8]
                    ).as_numpy("output")[0].decode("utf-8", errors="replace")

                    # Combine completed chunk with the current response chunk
                    response_chunk = completed_chunk + response_chunk

                    # Clear buffer after processing
                    tokens_buffer = []

                    # Debugging line
                    logger.debug(f"Combined response chunk: {response_chunk}")

                if response_chunk:  # Only yield non-empty chunks
                    # Create a streaming response chunk
                    chunk_response = ChatCompletionStreamResponse(
                        model=data.model,
                        choices=[
                            ChatCompletionStreamChoice(
                                index=1,
                                delta=ChatCompletionStreamMessage(
                                    role="assistant",
                                    content=response_chunk
                                ),
                            )
                        ],
                        usage=Usage(
                            prompt_tokens=0,
                            completion_tokens=0,
                            total_tokens=0
                        ),
                    ).model_dump_json(exclude_none=True)

                    # Create a streaming response chunk
                    yield f"data: {chunk_response}\n\n"

                    # Collect the response chunk
                    collected_chunks.append(response_chunk)

            except asyncio.TimeoutError:
                # No response available yet
                break

    finally:
        # Ensure stream is stopped
        try:
            triton_client.client.stop_stream()
            logger.debug("Streaming stopped successfully")
        except Exception as e:
            logger.warning(f"Error stopping stream: {e}")

    # Yield any remaining collected response if no chunks were streamed
    final_response = "".join(collected_chunks)
    logger.debug(f"Final response collected: {final_response}")

    if final_response:
        # Extract tool calls from responses
        tool_calls = extract_tool_calls_from_text(final_response,
                                                  data.parallel_tool_calls)

        # Get the usage
        prompt_tokens = _count_tokens(serialized_message, triton_client)
        completion_tokens = _count_tokens(final_response, triton_client)
        total_tokens = prompt_tokens + completion_tokens

        # Create the final response with tool calls
        final_response = ChatCompletionStreamResponse(
            model=data.model,
            choices=[
                ChatCompletionStreamChoice(
                    index=1,
                    delta=ChatCompletionStreamMessage(
                        role="assistant",
                        content="",
                        tool_calls=tool_calls
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            ),
        ).model_dump_json(exclude_none=True)

        # Yield the final response
        yield f"data: {final_response}\n\n"
        yield "data: [DONE]\n\n"

        log_chat_api_usage(
            request_id=request_id,
            user_id=user_id,
            model=data.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
