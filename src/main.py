"""
Main FastAPI application entry point.
This file imports and mounts FastAPI applications from subfolders.
"""
from config import get_config
from logger import get_logger, initialize_logger, shutdown_logging
from usage import (
    usage_user_router,
    usage_admin_router,
    initialize_usage_logger,
    shutdown_usage_logger
)
from v1 import v1_router
from apikey import apikey_router, init_database as init_apikey_database
from oauth2 import auth_router, user_router, admin_router, setup_database as init_auth_database
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
import sys
from pathlib import Path

# Add the workspace root to Python path so we can import src modules
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))


# Define the lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    """
    # Initialize logging system
    initialize_logger(get_config())
    initialize_usage_logger()
    logger = get_logger(__name__)
    logger.info("Starting My OpenAI Frontend API application")

    # Initialize database
    init_auth_database()
    init_apikey_database()
    logger.info("Database initialized")

    # The application runs here
    yield

    # Shutdown logic (if needed)
    shutdown_logging()
    shutdown_usage_logger()

# Create the main FastAPI application
app = FastAPI(
    title="My OpenAI Frontend API",
    description="A FastAPI application that proxies requests to Triton Inference Server with OAuth2 authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Include routes
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(apikey_router)
app.include_router(v1_router)
app.include_router(usage_user_router)
app.include_router(usage_admin_router)

# Configure CORS middleware - must be added AFTER AuthMiddleware to process CORS first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow the React app domain
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
