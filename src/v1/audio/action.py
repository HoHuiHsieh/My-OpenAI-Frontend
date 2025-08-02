# -*- coding: utf-8 -*-
import traceback
import base64
import uuid
import numpy as np
from typing import List
import tritonclient.grpc as grpcclient
from tritonclient.utils import InferenceServerException
from logger import get_logger
from config import get_config
from .models import TranscriptionRequest, TranscriptionResponse
from .util import log_transcription_usage


# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration
try:
    config = get_config()
    audio_models = config.get_models_by_type("audio:transcription")
except Exception as e:
    logger.error(f"Failed to load available models: {e}")
    raise RuntimeError("Configuration loading failed") from e


async def query_transcription(data: TranscriptionRequest, user_id=None) -> TranscriptionResponse:
    """
    Queries the Triton server for audio transcription.
    """
    model_name = data.model.split("/")[-1]
    target_model = audio_models.get(model_name)
    if not target_model:
        logger.error(f"Model {data.model} not found in configuration")
        raise ValueError(f"Model {data.model} not found in configuration")

    # Read the audio file to bytes
    await data.file.seek(0)
    audio_data = await data.file.read()
    # Check if audio data is empty
    if not audio_data:
        logger.error("Received empty audio data")
        raise ValueError("Received empty audio data")

    # Encode audio data to base64
    audio_data = base64.b64encode(audio_data)

    # Prepare input data for Triton server
    inputs: List[grpcclient.InferInput] = []
    buf = grpcclient.InferInput("input.audio", [1], "BYTES")
    buf.set_data_from_numpy(np.array([audio_data], dtype=np.object_))
    inputs.append(buf)

    # Prepare outputs to the format expected by Triton
    outputs = []
    outputs.append(grpcclient.InferRequestedOutput("output.text"))

    # Prepare Triton client
    host = target_model.host
    port = target_model.port
    triton_client = grpcclient.InferenceServerClient(
        url=f"{host}:{port}",
        verbose=False
    )

    # Prepare request ID
    request_id = f"req_{uuid.uuid4().hex}"

    # Query the Triton server
    try:
        # Query the Triton server
        response = triton_client.infer(
            model_name=model_name,
            inputs=inputs,
            outputs=outputs,
            request_id=request_id
        )

        # Extract the text output from the response
        asr_text = response.as_numpy("output.text")
        asr_text = asr_text[0].decode("utf-8") if asr_text else ""

        # Log the transcription result
        logger.info(f"Transcription result for model {model_name}: {asr_text}")
        log_transcription_usage(
            request_id=request_id,
            user_id=user_id,
            model=data.model,
            asr_texts=asr_text
        )

        return TranscriptionResponse(text=asr_text)

    except InferenceServerException as e:
        logger.error(f"Failed to query Triton server: {e}")
        raise RuntimeError("Triton server query failed") from e
