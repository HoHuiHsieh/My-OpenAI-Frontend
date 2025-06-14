"""
Core authentication functionality for OAuth2.

This module provides authentication functions for user verification,
password hashing and checking, and authentication flow.
"""

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional

from logger import get_logger
from config import get_config

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})

# Initialize password context for hashing and verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if a plain password matches its hashed version.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using the configured password hashing algorithm.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def authenticate_user(db: Session, username: str, password: str) -> Optional[object]:
    """
    Authenticate a user by username and password.
    
    Args:
        db: Database session
        username: Username to authenticate
        password: Password to verify
        
    Returns:
        Optional[User]: The authenticated user object or None if authentication fails
    """
    try:
        # Import here to avoid circular imports
        from .db.operations import get_user_by_username
        
        # Get user from database
        user = get_user_by_username(db, username)
        
        # Check if user exists and is enabled
        if not user:
            logger.info(f"Authentication failed: User {username} not found")
            return None
            
        if user.disabled:
            logger.info(f"Authentication failed: User {username} is disabled")
            return None
            
        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.info(f"Authentication failed: Invalid password for user {username}")
            return None
            
        logger.info(f"Authentication successful for user {username}")
        return user
    except Exception as e:
        logger.error(f"Authentication error for user {username}: {str(e)}")
        return None
