"""
FastAPI v1 API Router

This module provides centralized routing for all v1 API endpoints,
including models, chat, and embeddings services. It serves as an
aggregator for all v1 API routes to improve organization and maintainability.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute
from .models import app as models_app
from .chat import app as chat_app
from .embeddings import app as embeddings_app
from logger import get_logger

# Set up logger for this module
logger = get_logger(__name__)

# Create the main v1 API router
router = APIRouter(
    prefix="/v1",
    tags=["v1"]
)

# Root endpoint for v1 API
@router.get("/")
async def v1_root():
    """
    Root endpoint for v1 API that shows available endpoints
    """
    logger.debug("v1 root endpoint called")
    response = {
        "name": "My OpenAI API v1",
        "version": "1.0.0",
        "endpoints": [
            {
                "path": "/v1/models",
                "description": "Models API for accessing model information"
            },
            {
                "path": "/v1/chat",
                "description": "Chat API for text generation"
            },
            {
                "path": "/v1/embeddings",
                "description": "Embeddings API for vector embeddings"
            }
        ]
    }
    logger.info("Served v1 API information")
    return response

# Include routes from models_app, chat_app, and embeddings_app
logger.info("Registering models API routes")
for route in models_app.routes:
    if isinstance(route, APIRoute):
        path = f"/models{route.path}"
        logger.debug(f"Registering route: {', '.join(route.methods)} {path}")
        router.add_api_route(
            path,
            route.endpoint,
            methods=route.methods,
            name=route.name,
            description=route.description,
            dependencies=route.dependencies
        )

logger.info("Registering chat API routes")
for route in chat_app.routes:
    if isinstance(route, APIRoute):
        path = f"/chat{route.path}"
        logger.debug(f"Registering route: {', '.join(route.methods)} {path}")
        router.add_api_route(
            path,
            route.endpoint,
            methods=route.methods,
            name=route.name,
            description=route.description,
            dependencies=route.dependencies
        )

logger.info("Registering embeddings API routes")
for route in embeddings_app.routes:
    if isinstance(route, APIRoute):
        path = f"/embeddings{route.path}"
        logger.debug(f"Registering route: {', '.join(route.methods)} {path}")
        router.add_api_route(
            path,
            route.endpoint,
            methods=route.methods,
            name=route.name,
            description=route.description,
            dependencies=route.dependencies
        )
