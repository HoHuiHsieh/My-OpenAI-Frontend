# -*- coding: utf-8 -*-
"""
Usage Statistics Module

This module provides interfaces for retrieving API usage statistics from the logging database.
It includes functions to get usage data by time periods (days, weeks, months) for specific users.
Admin users can retrieve usage data for all users or specific users.

Module Structure:
- db.py:                Database access and query functions for statistics
- models.py:            Data models for usage statistics
- operations.py:        Business logic for aggregating and formatting statistics
- routes/
  - __init__.py:        Routes package initialization
  - user.py:            Endpoints for user usage statistics (/usage/{period})
  - admin.py:           Endpoints for admin usage statistics (/admin/usage/*)

API Endpoints (require login):
- GET  /usage/{period}:                        Get usage statistics for the current user by time period.

Admin API Endpoints (require admin role):
- GET  /admin/usage/user/{username}/{period}:  Get usage statistics for a specific user by username and period.
- GET  /admin/usage/all/{period}:              Get usage statistics for all users by period.
- GET  /admin/usage/summary:                   Get summary statistics including total users, active users today, API requests today, and total tokens used today.
- GET  /admin/usage/list/user/{username}/{period}: Get API requests list for a specific user by username and period.
"""

from logger import get_logger
from config import get_config

# Initialize the enhanced logging system
logger = get_logger(__name__)

# Load configuration
config = get_config()

# Import internal modules
from . import models
from . import db
from . import operations

# Import router objects and export them
from .routes import statistic_router

# Export important components
__all__ = [
    # Data models
    "models",
    
    # Database access
    "db",
    
    # Business logic
    "operations",
    
    # FastAPI router
    "statistic_router"
]