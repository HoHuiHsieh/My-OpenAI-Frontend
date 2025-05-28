# -*- coding: utf-8 -*-
"""
Audio API Type Definitions

This module contains Pydantic models for the audio API, defining both request and
response structures. These models enforce type validation and provide documentation
for the audio interface.

The APIs are:
- Create speech: Generates audio from the input text.
- Create transcription: Converts audio to text.

"""

from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


"""
Create speech API

Generates audio from the input text.

Request body
- input [string] (required): The text to generate audio for. The maximum length is 4096 characters.
- model [string] (required): One of the available TTS models.
- voice [string] (required): The voice to use when generating the audio. Supported voices are alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, and verse. Previews of the voices are available in the Text to speech guide.
- instructions [string] (optional): Control the voice of your generated audio with additional instructions. Does not work with tts-1 or tts-1-hd.
- response_format [string] (optional): The format to audio in. Supported formats are mp3, opus, aac, flac, wav, and pcm.
- speed [number] (optional): The speed of the generated audio. Select a value from 0.25 to 4.0. 1.0 is the default. Does not work with gpt-4o-mini-tts.

Returns
The audio file content.
"""


class CreateSpeechRequest(BaseModel):
    """
    Request model for creating speech from text.
    """
    input: str = Field(
        description="The text to generate audio for. The maximum length is 4096 characters."
    )
    model: str = Field(
        description="One of the available TTS models."
    )
    voice: str = Field(
        description="The voice to use when generating the audio. Supported voices are alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, and verse."
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Control the voice of your generated audio with additional instructions. Does not work with tts-1 or tts-1-hd."
    )
    response_format: Optional[Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]] = Field(
        default="mp3",
        description="The format to audio in. Supported formats are mp3, opus, aac, flac, wav, and pcm."
    )
    speed: Optional[float] = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="The speed of the generated audio. Select a value from 0.25 to 4.0. 1.0 is the default. Does not work with gpt-4o-mini-tts."
    )

    # Validate input field
    @field_validator("input")
    def validate_input(cls, v: str) -> str:
        if len(v) > 4096:
            raise ValueError("Input text cannot exceed 4096 characters.")
        return v


class CreateSpeechResponse(BaseModel):
    """
    Response model for the speech generation API.

    This is a binary response containing the audio file in the requested format.
    """
    # This class is empty because the API returns binary data
    pass


"""
Create transcription API

Transcribes audio into the input language.

Request body
- file [file] (required): The audio file object (not file name) to transcribe, in one of these formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm.
- model [string] (required): ID of the model to use. The options are gpt-4o-transcribe, gpt-4o-mini-transcribe, and whisper-1 (which is powered by our open source Whisper V2 model).
- chunking_strategy [string or object] (optional): Controls how the audio is cut into chunks. When set to "auto", the server first normalizes loudness and then uses voice activity detection (VAD) to choose boundaries. server_vad object can be provided to tweak VAD detection parameters manually. If unset, the audio is transcribed as a single block.
- include [array] (optional): Additional information to include in the transcription response. logprobs will return the log probabilities of the tokens in the response to understand the model's confidence in the transcription. logprobs only works with response_format set to json and only with the models gpt-4o-transcribe and gpt-4o-mini-transcribe.
- language [string] (optional): The language of the input audio. Supplying the input language in ISO-639-1 (e.g. en) format will improve accuracy and latency.
- prompt [string] (optional): An optional text to guide the model's style or continue a previous audio segment. The prompt should match the audio language.
- response_format [string] (optional): The format of the output, in one of these options: json, text, srt, verbose_json, or vtt. For gpt-4o-transcribe and gpt-4o-mini-transcribe, the only supported format is json.
- stream [boolean or null] (optional): If set to true, the model response data will be streamed to the client as it is generated using server-sent events. See the Streaming section of the Speech-to-Text guide for more information. Note: Streaming is not supported for the whisper-1 model and will be ignored.
- temperature [number] (optional): The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. If set to 0, the model will use log probability to automatically increase the temperature until certain thresholds are hit.
- timestamp_granularities[] (array) (optional): The timestamp granularities to populate for this transcription. response_format must be set verbose_json to use timestamp granularities. Either or both of these options are supported: word, or segment. Note: There is no additional latency for segment timestamps, but generating word timestamps incurs additional latency.

Returns
The transcription object, a verbose transcription object or a stream of transcript events.

- Stream Event (transcript.text.delta): Emitted when there is an additional text delta. This is also the first event emitted when the transcription starts. Only emitted when you create a transcription with the Stream parameter set to true.
  - delta [string] (required): The text delta that was additionally transcribed.
  - logprobs [array] (optional): The log probabilities of the delta. Only included if you create a transcription with the include[] parameter set to logprobs.
    - bytes [array] (required): The bytes that were used to generate the log probability.
    - logprob [number] (required): The log probability of the token.
    - token [string] (required): The token that was used to generate the log probability.
  - type [string] (required): The type of the event. Always transcript.text.delta.

- The transcription object (JSON): Represents a transcription response returned by model, based on the provided input.
  - logprobs [array] (optional): The log probabilities of the delta. Only included if you create a transcription with the include[] parameter set to logprobs.
    - bytes [array] (required): The bytes that were used to generate the log probability.
    - logprob [number] (required): The log probability of the token.
    - token [string] (required): The token that was used to generate the log probability.
  - text [string] (required): The transcribed text.
"""


class ServerVADParams(BaseModel):
    """
    Parameters for the Voice Activity Detection (VAD) server processing.
    """
    silence_thresh_dur: Optional[float] = Field(
        default=None,
        description="Duration threshold (in seconds) for silence detection."
    )
    speech_thresh_dur: Optional[float] = Field(
        default=None,
        description="Duration threshold (in seconds) for speech detection."
    )
    silence_thresh_db: Optional[float] = Field(
        default=None,
        description="Audio level (in dB) for silence threshold detection."
    )


class ChunkingStrategy(BaseModel):
    """
    Strategy for breaking audio into chunks for processing.
    """
    mode: str = Field(
        description="The chunking mode to use. Set to 'auto' for automatic chunking or 'server_vad' for manual configuration."
    )
    server_vad: Optional[ServerVADParams] = Field(
        default=None,
        description="Parameters for server VAD when mode is 'server_vad'."
    )


class CreateTranscriptionRequest(BaseModel):
    """
    Request model for transcribing audio files.
    """
    file: str = Field(
        description="The audio file object to transcribe, in one of these formats: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav, or webm."
    )
    model: str = Field(
        description="ID of the model to use. The options are gpt-4o-transcribe, gpt-4o-mini-transcribe, and whisper-1."
    )
    chunking_strategy: Optional[Union[str, ChunkingStrategy]] = Field(
        default=None,
        description="Controls how the audio is cut into chunks."
    )
    include: Optional[List[str]] = Field(
        default=None,
        description="Additional information to include in the transcription response."
    )
    language: Optional[str] = Field(
        default=None,
        description="The language of the input audio in ISO-639-1 format."
    )
    prompt: Optional[str] = Field(
        default=None,
        description="An optional text to guide the model's style or continue a previous audio segment."
    )
    response_format: Optional[Literal["json", "text", "srt", "verbose_json", "vtt"]] = Field(
        default="json",
        description="The format of the output."
    )
    stream: Optional[bool] = Field(
        default=None,
        description="If set to true, the model response data will be streamed to the client as it is generated."
    )
    temperature: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="The sampling temperature, between 0 and 1."
    )
    timestamp_granularities: Optional[List[str]] = Field(
        default=None,
        description="The timestamp granularities to populate for this transcription."
    )

    @field_validator("include")
    def validate_include(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            allowed_values = ["logprobs"]
            invalid_items = [item for item in v if item not in allowed_values]
            if invalid_items:
                raise ValueError(
                    f"Include items {invalid_items} are not supported. Supported values: {allowed_values}"
                )
        return v


class LogProbItem(BaseModel):
    """
    Log probability details for a token.
    """
    bytes: List[int] = Field(
        description="The bytes that were used to generate the log probability."
    )
    logprob: float = Field(
        description="The log probability of the token."
    )
    token: str = Field(
        description="The token that was used to generate the log probability."
    )


class TranscriptDelta(BaseModel):
    """
    Delta information for streaming transcription events.
    """
    delta: str = Field(
        description="The text delta that was additionally transcribed."
    )
    logprobs: Optional[List[LogProbItem]] = Field(
        default=None,
        description="The log probabilities of the delta."
    )
    type: str = Field(
        default="transcript.text.delta",
        description="The type of the event. Always transcript.text.delta."
    )


class CreateTranscriptionResponse(BaseModel):
    """
    Response model for the transcription API.
    """
    text: str = Field(
        description="The transcribed text."
    )
    logprobs: Optional[List[LogProbItem]] = Field(
        default=None,
        description="The log probabilities of the tokens."
    )
