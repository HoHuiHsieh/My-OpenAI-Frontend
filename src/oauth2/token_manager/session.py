"""
Session token management for OAuth2.

This module provides functionality for creating, validating, and
managing short-lived session tokens used for web access.
"""

from datetime import timedelta
from typing import Dict, Any, List, Optional

from logger import get_logger
from config import get_config
from .base import create_token, token_type_session

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})

# Session token configuration
ACCESS_TOKEN_EXPIRE_MINUTES = oauth2_config.get("access_token_expire_minutes", 30)


def create_session_token(
    username: str,
    scopes: Optional[List[str]] = None,
    expires_minutes: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a session token for web authentication.
    
    Args:
        username: The username for the token subject
        scopes: List of scopes for the token
        expires_minutes: Custom expiration time in minutes
        additional_data: Additional data to include in the token
        
    Returns:
        str: The encoded JWT token
    """
    # Use custom expiration or default from config
    expiration_minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    expires_delta = timedelta(minutes=expiration_minutes)
    
    # Create session token
    token = create_token(
        subject=username,
        token_type=token_type_session,
        expires_delta=expires_delta,
        scopes=scopes,
        additional_data=additional_data
    )
    
    logger.info(
        f"Created session token for user {username} with "
        f"{expiration_minutes} minutes expiration"
    )
    
    return token
