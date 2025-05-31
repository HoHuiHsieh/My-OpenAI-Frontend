"""
Common token functionality for OAuth2.

This module provides base functionality for token management,
including creation, validation, and decoding of JWT tokens.
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from fastapi import HTTPException, status

from logger import get_logger
from config import get_config

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})

# Token types
token_type_session = "session"
token_type_access = "access"

# JWT configuration
SECRET_KEY = oauth2_config.get("secret_key", "your-secret-key-placeholder")
ALGORITHM = oauth2_config.get("algorithm", "HS256")


def create_token(
    subject: str,
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    scopes: Optional[List[str]] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT token with specified payload.
    
    Args:
        subject: The subject of the token (usually username)
        token_type: Type of token (session or access)
        expires_delta: Expiration time delta
        scopes: List of scopes for the token
        additional_data: Additional data to include in the token
        
    Returns:
        str: The encoded JWT token
    """
    payload = {}
    
    # Current time for issued at
    now = datetime.utcnow()
    
    # Add standard JWT claims
    payload.update({
        "sub": subject,
        "type": token_type,
        "iat": now,
    })
    
    # Add expiration if provided
    if expires_delta:
        payload["exp"] = now + expires_delta
    
    # Add scopes if provided
    if scopes:
        payload["scopes"] = scopes
    
    # Add any additional data
    if additional_data:
        payload.update(additional_data)
    
    try:
        encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating token for {subject}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create authentication token",
        )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Dict[str, Any]: The decoded token payload
        
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token signature expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify a token's validity and return its payload.
    
    This function is a wrapper around decode_token that logs
    additional information about the token.
    
    Args:
        token: The JWT token to verify
        
    Returns:
        Dict[str, Any]: The decoded token payload
        
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        payload = decode_token(token)
        
        # Log token information
        subject = payload.get("sub", "unknown")
        token_type = payload.get("type", "unknown")
        scopes = payload.get("scopes", [])
        
        logger.debug(
            f"Token verified for user {subject}, type: {token_type}, "
            f"scopes: {', '.join(scopes)}"
        )
        
        return payload
    except HTTPException:
        # Re-raise HTTP exceptions from decode_token
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying token",
        )
