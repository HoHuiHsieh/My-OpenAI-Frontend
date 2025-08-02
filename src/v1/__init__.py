"""
OpenAI API Module

This module handles ...


It provides:
- models
    - Model list endpoint
- chat completion
    - Chat completion endpoint
- embedding
    - Embedding endpoint
- audio
    - Audio transcription endpoint

Model configuration settings available in src/config module

Module Structure:
- __init__.py:                 This file initializes the OpenAI API module- routes/
- routes
    - __init__.py:               Routes package initialization
    - models.py:                 Model list endpoint
    - chat.py:                   Chat completion endpoint
    - embedding.py:              Embedding endpoint
    - audio.py:                  Audio transcription endpoint
- chat
    - __init__.py:               Chat package initialization
- embedding
    - __init__.py:               Embedding package initialization
- audio
    - __init__.py:               Audio package initialization

API Endpoints (require access token in header):
- GET /models:              List all available models
- POST /chat/completions:   Chat completion endpoint
- POST /embeddings:         Embedding endpoint
- POST /audio/transcriptions: Audio transcription endpoint
"""
from .routes import v1_router
