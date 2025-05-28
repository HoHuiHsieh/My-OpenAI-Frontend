"""
OAuth2 Dependency Functions

This module provides dependency functions for FastAPI routes, 
including authorization checks and other common requirements.
"""

from fastapi import Depends, HTTPException, status
from typing import Annotated
import logging
from . import User, get_current_active_user
from logger import get_logger

# Get logger from our enhanced logging system
logger = get_logger(__name__)

# Admin scope name
ADMIN_SCOPE = "admin"

async def require_admin(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Dependency function that verifies the current user has admin privileges.
    
    Args:
        current_user: The authenticated user from the request
        
    Returns:
        The current user if they have admin privileges
        
    Raises:
        HTTPException: If the user doesn't have admin scope
    """
    if ADMIN_SCOPE not in current_user.scopes:
        logger.warning(f"User '{current_user.username}' attempted to access admin resource without admin scope")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: admin access required",
            headers={"WWW-Authenticate": "Bearer scope=\"admin\""},
        )
    
    logger.debug(f"Admin access granted to user '{current_user.username}'")
    return current_user