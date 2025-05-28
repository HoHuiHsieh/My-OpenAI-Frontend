# -*- coding: utf-8 -*-
"""
File overview:

Chat Completion API Type Definitions

This module contains Pydantic models for the Chat Completion API, defining both request and
response structures. These models enforce type validation and provide documentation
for the Chat Completion interface.

The main models are:
- CreateChatCompletionRequest: For validating chat completion requests
- CreateChatCompletionResponse: For chat completion API response

Request body
- messages [array] (required): A list of messages comprising the conversation so far.
- model [string] (required): Model ID used to generate the response.
- frequency_penalty [number or null] (optional): Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim.
- max_completion_tokens [integer or null] (optional): An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens.
- n [integer or null] (optional): How many chat completion choices to generate for each input message. Note that you will be charged based on the number of generated tokens across all of the choices. Keep n as 1 to minimize costs.
- parallel_tool_calls [boolean] (optional): Whether to enable parallel function calling during tool use.
- presence_penalty [number or null] (optional): Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics.
- response_format [object] (optional): An object specifying the format that the model must output.
- stop [string / array / null] (optional): Up to 4 sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
- stream [boolean or null] (optional): If set to true, the model response data will be streamed to the client as it is generated using server-sent events.
- temperature [number or null] (optional): What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic.
- tool_choice [string or object] (optional): Controls which (if any) tool is called by the model. none means the model will not call any tool and instead generates a message. auto means the model can pick between generating a message or calling one or more tools. required means the model must call one or more tools. Specifying a particular tool via {"type": "function", "function": {"name": "my_function"}} forces the model to call that tool.
- tools [array] (optional): A list of tools the model may call. Currently, only functions are supported as a tool. Use this to provide a list of functions the model may generate JSON inputs for.
- top_p [number or null] (optional): An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass. So 0.1 means only the tokens comprising the top 10% probability mass are considered.
- user [string] (optional): A stable identifier for your end-users. Used to boost cache hit rates by better bucketing similar requests and to help OpenAI detect and prevent abuse. Learn more.

Response body:
- choices [array] (required): A list of chat completion choices. Can be more than one if n is greater than 1.
- created [integer] (required): The Unix timestamp (in seconds) of when the chat completion was created.
- id [string] (required): A unique identifier for the chat completion.
- model [string] (required): The model used for the chat completion.
- object [string] (required): The object type, which is always chat.completion.
- usage [object] (required): Usage statistics for the completion request.

"""

from __future__ import annotations  # Add this import at the top

from pydantic import BaseModel, Field, field_validator, constr
from typing import List, Optional, Dict, Union, Any, Annotated, Literal
from pydantic.types import PositiveInt
import time
import uuid
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)


class ToolCallFunction(BaseModel):
    """
    Represents a function call made by the model.
    """
    name: str = Field(
        description="The name of the function to be called."
    )
    arguments: Dict[str, Any] = Field(
        description="The arguments to be passed to the function."
    )    


class ToolCall(BaseModel):
    """
    Represents a tool call made by the model.
    """
    id: str = Field(
        default_factory=lambda: f"call_{uuid.uuid4().hex[:12]}",
        description="A unique identifier for the tool call."
    )
    type: str = Field(
        default="function",
        description="The type of tool call. Currently only 'function' is supported."
    )
    function: 'ToolCallFunction' = Field(
        description="The function that was called, including name and arguments."
    )


class TextContentPart(BaseModel):
    """
    Represents a text content part of a message.
    """
    type: Literal["text"] = Field(
        default="text",
        description="The type of content. Currently only 'text' is supported."
    )
    text: str = Field(
        description="The text content."
    )


class FileObject(BaseModel):
    """
    Represents a file object.
    """
    file_data: Optional[str] = Field(
        default=None,
        description="The base64 encoded file data, used when passing the file to the model as a string."
    )
    file_id: Optional[str] = Field(
        default=None,
        description="The ID of an uploaded file to use as input."
    )
    filename: Optional[str] = Field(
        default=None,
        description="The name of the file, used when passing the file to the model as a string."
    )


class FileContentPart(BaseModel):
    """
    Represents a file content part of a message.
    """
    type: str = Field(
        default="file",
        description="The type of content. Currently only 'file' is supported."
    )
    file: FileObject = Field(
        description="The file content."
    )


class ChatMessage(BaseModel):
    """
    Represents a chat message within the chat completion.

    Depending on the model you use, different message types are supported, like 'developer', 'system', 'user', 'assistant', or 'tool'.
    """
    role: str = Field(
        description="The role of the message author. One of 'developer', 'system', 'user', 'assistant', or 'tool'."
    )
    content: Union[
        str,
        List[str],
        List[TextContentPart],
        List[FileContentPart],
    ] = Field(
        description="The content of the message."
    )
    name: Optional[str] = Field(
        default=None,
        description="An optional name for the participant. Provides the model information to differentiate between participants of the same role."
    )
    tool_calls: Optional[List['ToolCall']] = Field(
        default=None,
        description="The tool calls generated by the model, such as function calls. Only applicable for 'assistant' role."
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="The tool call that this message is responding to. Only applicable for 'tool' role."
    )


class ResponseFormat(BaseModel):
    """
    Specifies the format that the model must output.

    This allows control over the structure of the model's response,
    such as requesting JSON output.
    """
    type: str = Field(
        default="text",
        description="The format type to use for this response. Can be 'text' or 'json_object'."
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        description="A JSON schema that the model's output must conform to."
    )

    @field_validator('type')
    def validate_type(cls, v):
        valid_types = ['text', 'json_object']
        if v not in valid_types:
            raise ValueError(
                f"Response format type must be one of {valid_types}")
        return v

    @field_validator('json_schema')
    def validate_json_schema(cls, v, values):
        if values.get('type') == 'json_object' and v is None:
            raise ValueError(
                "json_schema must be provided when type is 'json_object'")
        return v


class PropertiesDefinition(BaseModel):
    """
    Represents a parameter definition for a function.

    This is used to define the parameters that a function can accept.
    """
    type: str = Field(
        description="The type of the parameter. Can be 'string', 'number', 'boolean', etc."
    )
    description: Optional[str] = Field(
        default=None,
        description="A description of the parameter."
    )


class ParametersDefinition(BaseModel):
    """
    Represents a parameter definition for a function.

    This is used to define the parameters that a function can accept.
    """
    type: str = Field(
        description="The type of the parameter. Can be 'object', 'array', etc."
    )
    properties: Optional[Dict[str,PropertiesDefinition]] = Field(
        default=None,
        description="A json object PropertiesDefinition object."
    )
    required: List[str] = Field(
        default_factory=list,
        description="A list of required properties for the function."
    )
    additionalProperties: Optional[bool] = Field(
        default=False,
        description="Whether additional properties are allowed in the parameter definition."
    )


class FunctionDefinition(BaseModel):
    """
    Represents a function definition that can be called by the model.
    """
    name: str = Field(
        description="The name of the function to be called. Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length of 64 characters."
    )
    description: Optional[str] = Field(
        default=None,
        description="A description of what the function does, used by the model to choose when and how to call the function."
    )
    parameters: Optional[ParametersDefinition] = Field(
        default_factory=dict,
        description="The parameters the function accepts, described as a JSON Schema object."
    )
    strict: Optional[bool] = Field(
        default=False,
        description="Whether to enable strict schema adherence when generating the function call."
    )


class Tool(BaseModel):
    """
    Represents a tool that can be used by the model, such as a function to call.

    This follows the OpenAI API convention for function calling.
    """
    type: str = Field(
        default="function",
        description="The type of the tool. Currently only 'function' is supported."
    )
    function: 'FunctionDefinition' = Field(
        description="The function definition for the tool."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the tool, such as version or additional information."
    )


class CreateChatCompletionRequest(BaseModel):
    """
    Request model for creating a chat completion.

    This follows the OpenAI API convention for chat completion requests.
    """
    model: str = Field(
        description="ID of the model to use for chat completion."
    )
    messages: List['ChatMessage'] = Field(
        description="A list of messages comprising the conversation so far."
    )
    max_completion_tokens: Optional[PositiveInt] = Field(
        default=None,
        description="An upper bound for the number of tokens that can be generated for a completion, including visible output tokens and reasoning tokens."
    )
    temperature: Optional[float] = Field(
        default=1.0,
        description="What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic."
    )
    top_p: Optional[float] = Field(
        default=1.0,
        description="An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass."
    )
    presence_penalty: Optional[float] = Field(
        default=0.0,
        description="Number between -2.0 and 2.0. Positive values penalize new tokens based on whether they appear in the text so far, increasing the model's likelihood to talk about new topics."
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0,
        description="Number between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, decreasing the model's likelihood to repeat the same line verbatim."
    )
    tools: Optional[List['Tool']] = Field(
        default=None,
        description="A list of tools the model may call. Currently, only functions are supported as a tool."
    )
    stop: Optional[Union[str, List[str]]] = Field(
        default=None,
        description="Up to 4 sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence."
    )
    n: Optional[PositiveInt] = Field(
        default=1,
        description="How many chat completion choices to generate for each input message. Note that you will be charged based on the number of generated tokens across all of the choices."
    )
    response_format: Optional[ResponseFormat] = Field(
        default=None,
        description="An object specifying the format that the model must output."
    )
    stream: Optional[bool] = Field(
        default=False,
        description="If set to true, the model response data will be streamed to the client as it is generated using server-sent events."
    )
    parallel_tool_calls: Optional[bool] = Field(
        default=False,
        description="Whether to enable parallel function calling during tool use."
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="Controls which (if any) tool is called by the model. Options include 'none', 'auto', 'required', or a specific tool definition."
    )
    user: Optional[str] = Field(
        default=None,
        description="A stable identifier for your end-users. Used to boost cache hit rates and help detect and prevent abuse."
    )


class ChatCompletionChoice(BaseModel):
    """
    Represents a single chat completion choice in the response.
    """
    index: int = Field(
        description="The index of the choice in the list of choices."
    )
    message: 'ChatMessage' = Field(
        description="The chat message generated by the model, which may include tool calls."
    )
    finish_reason: str = Field(
        description="The reason why the model stopped generating text. Possible values include 'stop', 'length', 'content_filter', 'tool_calls', etc."
    )


class ChatCompletionChunkChoice(BaseModel):
    index: int = Field(
        description="The index of the choice in the list of choices."
    )
    delta: 'ChatMessage' = Field(
        description="The chat message generated by the model, which may include tool calls."
    )
    finish_reason: str = Field(
        description="The reason why the model stopped generating text. Possible values include 'stop', 'length', 'content_filter', 'tool_calls', etc."
    )


class UsageInfo(BaseModel):
    """
    Represents usage statistics for the completion request.
    """
    prompt_tokens: int = Field(
        description="The number of tokens in the input prompt."
    )
    completion_tokens: int = Field(
        description="The number of tokens in the generated completion."
    )
    total_tokens: int = Field(
        description="The total number of tokens used in the request (prompt + completion)."
    )

class CreateChatCompletionResponse(BaseModel):
    """
    Response model for chat completion.

    This follows the OpenAI API convention for chat completion objects.
    """
    id: str = Field(
        default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}",
        description="A unique identifier for the chat completion."
    )
    object: str = Field(
        default="chat.completion",
        description="The object type, which is always 'chat.completion'."
    )
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="The Unix timestamp (in seconds) when the chat completion was created."
    )
    model: str = Field(
        description="The model used for generating the chat completion."
    )
    choices: List['ChatCompletionChoice'] = Field(
        description="A list of chat completion choices. Can be more than one if n > 1 is specified."
    )
    usage: Optional[UsageInfo] = Field(
        default=None,
        description="Usage statistics for the completion request."
    )
    parallel_tool_calls: Optional[bool] = Field(
        default=None,
        description="Indicates whether parallel tool calls were enabled during the request."
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None,
        description="The tool choice used during the request, if applicable."
    )

class CreateChatCompletionChunkResponse(CreateChatCompletionResponse):
    object: str = Field(
        default="chat.completion.chunk",
        description="The object type, which is always 'chat.completion.chunk'."
    )
    choices: List['ChatCompletionChunkChoice'] = Field(
        description="A list of chat completion choices for chunk data. Can be more than one if n > 1 is specified."
    )

# Adding forward references to avoid circular dependencies
CreateChatCompletionResponse.model_rebuild()
ChatCompletionChoice.model_rebuild()
ToolCall.model_rebuild()
ToolCallFunction.model_rebuild()
ChatMessage.model_rebuild()
Tool.model_rebuild()
FunctionDefinition.model_rebuild()
ChatCompletionChunkChoice.model_rebuild()
