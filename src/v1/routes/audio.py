
import json
from fastapi import APIRouter, Request, Depends, UploadFile, Form, Security
from apikey import validate_api_key, ApiKeyData
from logger import get_logger
from ..audio import TranscriptionRequest, TranscriptionResponse, query_transcription

# Set up logger for this module
logger = get_logger(__name__)

# Create router
audio_router = APIRouter(prefix="/audio", tags=["transcriptions"])


@audio_router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcriptions(
    file: UploadFile,
    model: str = Form(...),
    apiKeyData: ApiKeyData = Security(
        validate_api_key, scopes=["audio:transcribe"])
):
    """
    Transcribe audio file to text.
    """
    # Create the request object from form data
    body = TranscriptionRequest(file=file, model=model)
    
    # Log the request (excluding file content)
    logger.debug(
        f"Received transcription request - model: {model}, file: {file.filename}, content_type: {file.content_type}")

    return await query_transcription(body, apiKeyData.user_id)

    # return TranscriptionResponse(text="ok")  # Placeholder for actual transcription logic
