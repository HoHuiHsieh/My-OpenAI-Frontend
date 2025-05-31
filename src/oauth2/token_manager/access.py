"""
API access token management for OAuth2.

This module provides functionality for creating, validating, and
managing long-lived access tokens for API access with scope control.
"""

from datetime import timedelta
from typing import Dict, Any, List, Optional

from logger import get_logger
from config import get_config
from .base import create_token, token_type_access

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})

# Access token configuration
USER_TOKEN_EXPIRE_DAYS = oauth2_config.get("user_token_expire_days", 180)
ADMIN_TOKEN_NEVER_EXPIRES = oauth2_config.get("admin_token_never_expires", False)


def create_access_token(
    username: str,
    scopes: List[str],
    is_admin: bool = False,
    expires_days: Optional[int] = None,
    never_expires: Optional[bool] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create an access token for API authentication.
    
    Args:
        username: The username for the token subject
        scopes: List of scopes for the token
        is_admin: Whether this is an admin token
        expires_days: Custom expiration time in days
        never_expires: Whether the token should never expire
        additional_data: Additional data to include in the token
        
    Returns:
        str: The encoded JWT token
    """
    # Determine if token should never expire
    should_never_expire = never_expires
    if should_never_expire is None and is_admin:
        should_never_expire = ADMIN_TOKEN_NEVER_EXPIRES
    
    # Set expiration
    expires_delta = None
    if not should_never_expire:
        # Use custom expiration or default from config
        expiration_days = expires_days or USER_TOKEN_EXPIRE_DAYS
        expires_delta = timedelta(days=expiration_days)
        
        logger.info(
            f"Creating access token for user {username} with "
            f"{expiration_days} days expiration"
        )
    else:
        logger.info(f"Creating never-expiring access token for user {username}")
    
    # Create access token
    token = create_token(
        subject=username,
        token_type=token_type_access,
        expires_delta=expires_delta,
        scopes=scopes,
        additional_data=additional_data
    )
    
    return token
