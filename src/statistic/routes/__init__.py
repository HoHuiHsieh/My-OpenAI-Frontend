"""
Routes package initialization for statistics module.

This package contains all FastAPI route handlers for the statistics endpoints.
"""

from fastapi import APIRouter

# Import all route modules
from . import user
from . import admin

# Create a router for statistics endpoints
statistic_router = APIRouter()

# Include all routes from the submodules
statistic_router.include_router(user.router, tags=["Usage Statistics"])
statistic_router.include_router(admin.router, tags=["Admin Usage Statistics"])

__all__ = ["statistic_router"]
