"""
User dependencies for FastAPI.

This module provides FastAPI dependencies for user authentication.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import SecurityScopes
from sqlalchemy.orm import Session
from typing import Optional

from logger import get_logger
from .db import get_db
from .db.models import User
from .rbac import verify_scopes
from .db.operations import get_user_by_username

# Initialize logger
logger = get_logger(__name__)

async def get_current_user(
    security_scopes: SecurityScopes,
    token_data: dict = Depends(verify_scopes),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user.
    
    Args:
        security_scopes: The required scopes for the endpoint
        token_data: The decoded JWT token data
        db: Database session
        
    Returns:
        User: The current authenticated user
        
    Raises:
        HTTPException: If the user is not found
    """
    username = token_data.get("sub")
    
    # Get user from database
    user = get_user_by_username(db, username)
    
    if user is None:
        logger.warning(f"User not found for token: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    return user
    
    
async def get_current_active_user(
    security_scopes: SecurityScopes,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get the current active (non-disabled) user.
    
    Args:
        security_scopes: The required scopes for the endpoint
        current_user: The current authenticated user
        
    Returns:
        User: The current active user
        
    Raises:
        HTTPException: If the user is disabled
    """
    if current_user.disabled:
        logger.warning(f"Disabled user attempted access: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
        
    return current_user
