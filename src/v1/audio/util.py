from usage import get_usage_logger
import json
import uuid
from datetime import datetime


def estimate_number_of_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a given text.
    This is a placeholder function and should be replaced with an actual tokenization logic.
    """
    # For simplicity, we assume 1 token per 4 characters
    return len(text) // 4 + 1


def log_transcription_usage(
        request_id: str,
        user_id: str,
        model: str,
        asr_texts: str,
        **kwargs
):
    """Log usage for transcription API calls"""
    # Estimate completion tokens based on the length of the transcription text
    completion_tokens = estimate_number_of_tokens(asr_texts)

    # Get the transcription logger
    logger = get_usage_logger("transcription")

    usage_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_type": "transcription",
        "user_id": user_id,
        "model": model,
        "request_id": request_id or str(uuid.uuid4()),
        "prompt_tokens": 0,
        "completion_tokens": completion_tokens, 
        "total_tokens": completion_tokens,
        "input_count": 1,
        "extra_data": kwargs
    }
    # Log the usage data
    logger.log(25, json.dumps(usage_data))


