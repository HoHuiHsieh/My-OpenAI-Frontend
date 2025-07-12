# -*- coding: utf-8 -*-
"""
File Overview:
--------------
This module implements a proxy service for model information.

It serves as a central aggregator for model metadata from multiple backend sources
defined in the configuration file. The module:
- Loads server configuration from a YAML file
- Configures a FastAPI application to serve as the proxy
- Provides an endpoint that forwards requests to multiple target servers
- Consolidates responses from all sources into a single, unified model list
- Implements OAuth2 authentication for secure access

The proxy pattern allows clients to access multiple model services through a single
endpoint, abstracting away the distributed nature of the underlying architecture.
"""
from fastapi import FastAPI, HTTPException, Security, Depends
import time
from .typedef import CreateModelListResponse, ModelInfo
from config import get_config
from logger import get_logger
from oauth2 import get_current_active_user, User, SecurityScopes

# Set up logger for this module
logger = get_logger(__name__)

# Safely load configuration with validation
config = get_config(force_reload=False)


# Define the FastAPI application
app = FastAPI(
    title="Proxy API",
    description="A FastAPI application that list and describe the various models available in the API. .",
    # Disable automatic redirection for trailing slashes
    redirect_slashes=False
)


@app.get("/", response_model=CreateModelListResponse, summary="List available models")
@app.get("", response_model=CreateModelListResponse, summary="List available models")
async def models_root(
    current_user: User = Security(get_current_active_user,
                                  scopes=["models:read"])
):
    """
    List all available models from configured model providers.

    This endpoint aggregates model information from all configured model servers,
    providing a unified view of all available models across the system.
    This endpoint is protected and requires OAuth2 authentication with 'models:read' scope.

    Args:
        request: The incoming FastAPI request
        current_user: The authenticated user with models:read scope

    Returns:
        A consolidated response with model data from all servers

    Raises:
        HTTPException: If all target servers fail to respond or unauthorized access
    """
    print("models_root called", current_user.full_name, current_user.scopes)

    # Extract the original request data and log the request
    logger.info(
        f"Received request to list all models from user: {current_user.username}")

    # Get the model server configurations from the config
    model_configs = config.get("models", {})
    if not model_configs:
        logger.warning("No model servers configured in the system.")
        raise HTTPException(
            status_code=500, detail="No model servers configured in the system.")

    # Initialize an empty list to hold model data
    data = []
    for (key, model) in model_configs.items():
        # Validate the model is an object with a response attribute
        if not isinstance(model, dict) or "response" not in model:
            logger.warning(
                f"Model server {key} does not have a valid response configuration.")
            continue

        # Check if the user has permission to access this model
        if "admin" not in current_user.scopes:
            if not set(model.get('type', [])).intersection(current_user.scopes):
                logger.debug(f"User {current_user.username} does not have required scopes for model {key}. Skipping.")
                continue

        try:
            # Extract the target model response data and convert to ModelInfo
            model_response = model.get("response")

            # Set default timestamp if not provided or if it's zero
            if not model_response.get("created") or model_response.get("created") == 0:
                model_response["created"] = int(time.time())

            # Create a validated ModelInfo object
            model_info = ModelInfo(**model_response)
            data.append(model_info)
        except Exception as e:
            logger.error(f"Error processing model {key}: {str(e)}")
            # Continue with other models if one fails
            continue

    # Return the consolidated response
    logger.info(
        f"Returning consolidated response with {len(data)} total models")
    responses = CreateModelListResponse(
        object="list",
        data=data
    )
    return responses
