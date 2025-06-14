"""
Main FastAPI application entry point.
This file imports and mounts FastAPI applications from subfolders.
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from v1 import v1_router
from oauth2.routes.session import session_router
from oauth2.routes.access import access_router
from oauth2.routes.admin import admin_router
from oauth2.middleware import OAuth2Middleware as AuthMiddleware
from oauth2.migrations import initialize_database
from config import get_config
from logger import get_logger, UsageLogger
from statistic import statistic_router
from constant import DEFAULT_SHARE_PATH
import os


# Initialize enhanced logging system
logger = get_logger(__name__)
logger.info("Starting My OpenAI Frontend API application")

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})
enable_auth = oauth2_config.get("enable_authentication", True)
exclude_paths = oauth2_config.get("exclude_paths", [])

# Define the lifespan context manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        # Initialize OAuth2 database
        initialize_database()
        
        # Initialize usage logging system
        logger.info("Initializing usage logging system...")
        UsageLogger.initialize()
        logger.info("Usage logging system initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database or usage logger: {e}", exc_info=True)
        # Continue startup even if initialization fails
        # This allows the application to start and use in-memory fallbacks if necessary

    yield  # The application runs here

    # Shutdown logic (if needed)
    # Any cleanup code would go here

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

# Include OAuth2 authentication and admin routes
app.include_router(session_router)
app.include_router(access_router)
app.include_router(admin_router)

# Add authentication middleware if enabled in config
if enable_auth:
    app.add_middleware(AuthMiddleware, exclude_paths=exclude_paths)

# Configure CORS middleware - must be added AFTER AuthMiddleware to process CORS first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow the React app domain
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include the v1 router (protected by the authentication middleware)
logger.info("Mounting v1 API router")
app.include_router(v1_router)

# Include usage statistics router
logger.info("Mounting usage statistics router")
app.include_router(statistic_router)

# Custom StaticFiles class that redirects to index.html when path is '/'
class IndexStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        if path == "":
            return RedirectResponse(url=f"{scope['path']}index.html")
        return await super().get_response(path, scope)

# Mount static files directory if it exists
if os.path.exists(DEFAULT_SHARE_PATH):
    logger.info(f"Mounting static files from {DEFAULT_SHARE_PATH} under /share path")
    app.mount("/share", IndexStaticFiles(directory=DEFAULT_SHARE_PATH), name="share")
else:
    logger.warning(f"Static files directory {DEFAULT_SHARE_PATH} does not exist, skipping mount")

# Root endpoint redirects to share/index.html
@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    
    # Check if the share folder exists and has an index.html file
    index_html_path = os.path.join(DEFAULT_SHARE_PATH, "index.html")
    if os.path.exists(index_html_path):
        logger.info(f"Redirecting root endpoint to /share/ (index.html found)")
        # Redirect to the share folder root, which will serve index.html via our custom StaticFiles
        return RedirectResponse(url="/share/")
    
    # Otherwise, serve the default API information
    logger.info("Serving API information from root endpoint (no index.html found)")
    response = {
        "name": "My OpenAI Frontend API",
        "version": "1.0.0",
        "description": "A proxy service for Triton Inference Server with OAuth2 authentication",
        "static_files": f"/share (serving files from {DEFAULT_SHARE_PATH})" if os.path.exists(DEFAULT_SHARE_PATH) else "Not available"
    }
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
