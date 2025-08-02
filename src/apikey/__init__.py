"""
API key Module

This module handles api key management for the application.

It provides features:
- JWT api-key support
- api-key generation and validation
- PostgreSQL database integration for api-keys

PostgreSQL database configuration settings available in src/config module

Module Structure:
- __init__.py:               This file initializes the api-key module
- manager.py:                api-key management logic
- models.py:                 api-key data models
- database.py:               Database setup and api-key model
- routes.py:                 api-key management endpoints
- middleware.py:             Middleware for api-key validation
- config.py:                 Configuration settings for api-key management

API Endpoints:
- POST /apikey:            Create new api-key endpoint

API Endpoints (require api-key in header):
- GET /apikey:             Validate api-key endpoint
"""

# Export main components
from .routes import apikey_router
from .middleware import validate_api_key, get_optional_api_key
from .manager import ApiKeyManager
from .models import ApiKey, ApiKeyData, ApiKeyDB
from .database import init_database

# Initialize manager for direct usage
api_key_manager = ApiKeyManager()

__all__ = [
    "apikey_router",
    "validate_api_key", 
    "get_optional_api_key",
    "api_key_manager",
    "ApiKey",
    "ApiKeyData", 
    "ApiKeyDB",
    "init_database"
]

