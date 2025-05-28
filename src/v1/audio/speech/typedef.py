# -*- coding: utf-8 -*-
"""
Audio API Type Definitions

This module contains Pydantic models for the audio API, defining both request and
response structures. These models enforce type validation and provide documentation
for the audio interface.

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
from typing import Annotated, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


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
