"""
# src/v1/routes/__init__.py
This module initializes the v1 API routes for the application.
"""
from fastapi import APIRouter
from .models import models_router
from .chat import chat_router
from .embeddings import embeddings_router
from .audio import audio_router

# Create main router for v1
v1_router = APIRouter(prefix="/v1", tags=["v1"])
v1_router.include_router(models_router)
v1_router.include_router(chat_router)
v1_router.include_router(embeddings_router)
v1_router.include_router(audio_router)
