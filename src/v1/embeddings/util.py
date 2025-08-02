from usage import get_usage_logger
import json
import uuid
from datetime import datetime


def log_embeddings_usage(
        request_id: str,
        user_id: str,
        model: str,
        input_count: int,
        prompt_tokens: int,
        **kwargs
):
    """Log usage for embeddings API calls"""

    logger = get_usage_logger("embeddings")

    usage_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_type": "embeddings",
        "user_id": user_id,
        "model": model,
        "request_id": request_id or str(uuid.uuid4()),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": 0,
        "total_tokens": prompt_tokens,
        "input_count": input_count,
        "extra_data": kwargs
    }
    # Log the usage data
    logger.log(25, json.dumps(usage_data))
