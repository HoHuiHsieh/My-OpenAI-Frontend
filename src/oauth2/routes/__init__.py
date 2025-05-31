"""
Routes package initialization for OAuth2.

This module initializes FastAPI routers for authentication endpoints.
"""

from fastapi import APIRouter
from logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create routers
session_router = APIRouter(prefix="/session", tags=["Session"])
access_router = APIRouter(prefix="/access", tags=["Access"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# Import routes to register endpoints
from .session import *
from .access import *
from .admin import *
from . import validator

# Export routers
__all__ = ["session_router", "access_router", "admin_router"]
