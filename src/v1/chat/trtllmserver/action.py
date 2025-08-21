from datetime import datetime
import json
import httpx
from typing import AsyncGenerator, List
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from logger import get_logger
from config import get_config, ModelConfig
import re
from ..models import (
    ChatCompletionRequest, ChatCompletionResponse, ChatCompletionStreamResponse
)
from ..models.request import (
    ChatCompletionMessages, ToolCall as ToolCallRequest,
    ToolFunction,
    SystemMessage,
    DeveloperMessage,
    Tool as RequestToolType,
    ToolFunctionParameters,
    TextResponseFormat,
    StructuralTagFormat,
)
from ..models.response import (
    ChatCompletionChoice,
    ChatCompletionMessage,
    ChatCompletionStreamChoice,
    ChatCompletionStreamMessage,
    ToolCall,
    ToolCallFunction, Usage
)

# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration
try:
    config = get_config()
    chat_models = config.get_models_by_type("chat:base")
except Exception as e:
    logger.error(f"Failed to load available models: {e}")
    raise RuntimeError("Configuration loading failed") from e


SYSTEM_PROMPT_TEMPLATE = (
    "You are a helpful assistant."
    "Current date and time: {current_date_time}"
    ""
    "Reasoning: medium"
    ""
    "# Valid channels: analysis, commentary, final. Channel must be included for every message."
    "{tool_call_system_prompt}"
)

DEVELOPER_PROMPT_TEMPLATE = (
    "# Instructions"
    ""
    "{instructions}"
    ""
    ""
    "# Tools"
    ""
    "{tool_call_developer_prompt}"
)


def _get_target_model(data: ChatCompletionRequest) -> ModelConfig:
    model_name = data.model.split("/")[-1]
    target_model = chat_models.get(model_name)
    if not target_model:
        logger.error(f"Model {model_name} not found in configuration")
        raise ValueError(f"Model {model_name} not found in configuration")
    return target_model


def _create_client(model_config: ModelConfig) -> OpenAI:
    """
    Create an OpenAI client for the specified model configuration.
    """
    base_url = f"http://{model_config.host}:{model_config.port}/v1"
    logger.info(f"Creating OpenAI client for {base_url}")

    # Create HTTP client with longer timeout and retry settings
    http_client = httpx.Client(
        verify=False,
        timeout=httpx.Timeout(30.0, connect=10.0),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
    )

    return OpenAI(
        base_url=base_url,
        api_key="tensorrt_llm",
        http_client=http_client
    )


def _prepare_messages(messages: List[ChatCompletionMessages], tools: List[ToolCallRequest] = None) -> List[object]:
    current_date_time = datetime.now().isoformat()
    tool_call_system_prompt = ""
    instructions = ""
    tool_call_developer_prompt = ""

    # Find system message
    sys_message = next((msg for msg in messages if msg.role == "system"), None)
    if sys_message:
        instructions = sys_message.content

    # Prepare prompts for tool call
    if tools:
        # tool prompt in system prompt
        tool_call_system_prompt = "Calls to these tools must go to commentary channel, for example:\n"
        for tool in tools:
            tool_call_system_prompt += f"    commentary to={tool.function.name}\n"

        # tool prompt in developer prompt
        for tool in tools:
            fun: ToolFunction = tool.function
            description = fun.description or ""
            name = fun.name
            props = fun.parameters or {}
            if props:
                props = props.properties

            tool_call_developer_prompt += f"// {description}\n"
            if (props):
                tool_call_developer_prompt += "%s = (_: {\n" % (name)
                for key, value in props.items():
                    if type(value.enum) is list:
                        prop_type = " | ".join(value.enum)
                    else:
                        prop_type = value.type or "any"
                    tool_call_developer_prompt += "    %s: %s, // %s\n" % (
                        key, prop_type, value.description)
                tool_call_developer_prompt += "}) => any;\n\n"
            else:
                tool_call_developer_prompt += "%s = () => any;\n\n" % (name)

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        current_date_time=current_date_time,
        tool_call_system_prompt=tool_call_system_prompt
    )

    developer_prompt = DEVELOPER_PROMPT_TEMPLATE.format(
        instructions=instructions,
        tool_call_developer_prompt=tool_call_developer_prompt
    )

    new_messages = [
        SystemMessage(content=system_prompt),
        DeveloperMessage(content=developer_prompt),
        *messages
    ]

    return [msg.model_dump(exclude_none=True) for msg in new_messages]


def _prepare_structural_tags(tools: List[RequestToolType]) -> List[StructuralTagFormat]:
    """
    Prepare structural tags from the messages.
    """
    # If tools not provided, return text response format
    if not tools:
        return 

    # Return empty structure if no tools are provided
    structures = []
    for tool in tools:
        fun_name = tool.function.name if tool.function.name else ""
        if not fun_name:
            continue
        if tool.function.parameters:
            fun_schema = tool.function.parameters
        else:
            fun_schema = ToolFunctionParameters(properties={}).model_dump(exclude_none=True)

        structures.append({
            "begin": f"<|channel|>commentary to={fun_name} <|constrain|>json<|message|>",
            "schema": fun_schema,
            "end": "<|call|>"
        })

    return StructuralTagFormat(structures=structures).model_dump(exclude_none=True)


def _parse_tool_calls_from_response(text: str, parallel_tool_calls=False) -> List[ToolCall]:
    """
    Parse tool calls from the response text.
    """
    regex = r"(<\|channel\|>commentary to=)(\w+)( <\|constrain\|>json<\|message\|>)([\S\s]+)(<\|call\|>)"
    matches = re.findall(regex, text)
    tool_calls = []

    for match in matches:
        tool_name = match[1]
        tool_properties = match[3]
        tool_call = ToolCall(
            type="function",
            function=ToolCallFunction(
                name=tool_name,
                arguments=json.dumps(tool_properties, ensure_ascii=False)
            )
        )
        tool_calls.append(tool_call)

        # If not parallel tool calls, break after the first tool call
        if not parallel_tool_calls and tool_call:
            break

    return tool_calls


async def query_chat_completion(data: ChatCompletionRequest, user_id=None, apiKey="") -> ChatCompletionResponse:
    try:
        # Get target Model
        target_model = _get_target_model(data)

        # Get client
        client = _create_client(target_model)

        # Get request properties
        model = data.model.split("/")[-1]
        messages = data.messages
        max_completion_tokens = data.max_completion_tokens or 4096
        response_format = _prepare_structural_tags(data.tools) or data.response_format.model_dump(exclude_none=True)
        stop = data.stop or None
        parallel_tool_calls = data.parallel_tool_calls

        # Prepare messages
        prepared_message = _prepare_messages(messages, data.tools)
        
        # Get response
        response: ChatCompletion = client.chat.completions.create(
            model=model,
            messages=prepared_message,
            max_completion_tokens=max_completion_tokens,
            stream=False,
            stop=stop,
            response_format=response_format,
            extra_body={
                "skip_special_tokens": False,
                "include_stop_str_in_output": True,
            },
        )

        # Parse tool call
        response_text = response.choices[0].message.content
        tool_calls = _parse_tool_calls_from_response(
            response_text, parallel_tool_calls)
        usage = response.usage

        # Return response
        return ChatCompletionResponse(
            model=data.model,
            choices=[
                ChatCompletionChoice(
                    index=1,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=response_text,
                        tool_calls=tool_calls
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens
            ),
        )
    except ConnectionError as e:
        logger.error(f"Connection error in chat completion: {e}")
        # Return a fallback response when server is unavailable
        return ChatCompletionResponse(
            model=data.model,
            choices=[
                ChatCompletionChoice(
                    index=1,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="I apologize, but I'm currently unable to process your request due to a server connection issue. Please try again later or contact support if the problem persists.",
                        tool_calls=[]
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=50,
                total_tokens=50
            ),
        )
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        raise


async def query_streaming_chat_completion(data: ChatCompletionRequest, user_id=None, apiKey="") -> AsyncGenerator[str, None]:
    try:
        # Get target Model
        target_model = _get_target_model(data)

        # Get client
        client = _create_client(target_model)

        # Get request properties
        model = data.model.split("/")[-1]
        messages = data.messages
        max_completion_tokens = data.max_completion_tokens or 500
        response_format = _prepare_structural_tags(data.tools) or data.response_format.model_dump(exclude_none=True)
        stop = data.stop or None
        parallel_tool_calls = data.parallel_tool_calls or False

        # Prepare messages
        prepared_message = _prepare_messages(messages, data.tools)

        # Get response
        response: Stream[ChatCompletionChunk] = client.chat.completions.create(
            model=model,
            messages=prepared_message,
            max_completion_tokens=max_completion_tokens,
            stream=True,
            stop=stop,
            response_format=response_format,
            extra_body={
                "skip_special_tokens": False,
                "include_stop_str_in_output": True,
            },
        )

        # Process response
        response_text = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                response_text += content

                # Create a streaming response chunk
                chunk_response = ChatCompletionStreamResponse(
                    model=data.model,
                    choices=[
                        ChatCompletionStreamChoice(
                            index=1,
                            delta=ChatCompletionStreamMessage(
                                role="assistant",
                                content=content
                            ),
                        )
                    ],
                    usage=Usage(
                        prompt_tokens=chunk.usage.prompt_tokens if chunk.usage else 0,
                        completion_tokens=chunk.usage.completion_tokens if chunk.usage else 0,
                        total_tokens=chunk.usage.total_tokens if chunk.usage else 0
                    ),
                ).model_dump_json(exclude_none=True)

                # Create a streaming response chunk
                yield f"data: {chunk_response}\n\n"

        # Parse tool call
        tool_calls = _parse_tool_calls_from_response(
            response_text, parallel_tool_calls)

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
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
        ).model_dump_json(exclude_none=True)

        # Yield the final response
        yield f"data: {final_response}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error in streaming chat completion: {e}")
        # Yield error response
        error_response = ChatCompletionStreamResponse(
            model=data.model,
            choices=[
                ChatCompletionStreamChoice(
                    index=1,
                    delta=ChatCompletionStreamMessage(
                        role="assistant",
                        content=f"Error: {str(e)}"
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
        ).model_dump_json(exclude_none=True)

        yield f"data: {error_response}\n\n"
        yield "data: [DONE]\n\n"
