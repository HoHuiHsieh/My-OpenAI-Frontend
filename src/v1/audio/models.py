
from typing import Annotated, Dict, List, Optional, Union
from pydantic import BaseModel, Field, confloat, conint, field_validator
from fastapi import UploadFile


class TranscriptionRequest(BaseModel):
    """
    Request model for audio transcriptions.
    """
    file: UploadFile = Field(
        description="The audio file to be transcribed. Must be a valid audio format."
    )
    model: str = Field(
        description="The name of the model to use for transcription."
    )


class TranscriptionResponse(BaseModel):
    """
    Response model for a single transcription result.
    """
    text: str = Field(
        description="The transcribed text from the audio."
    )
