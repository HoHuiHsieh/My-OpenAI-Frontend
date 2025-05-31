"""
Request validation middleware for OAuth2 routes.

This module provides validation for API requests to ensure
they meet the required format and security standards.
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import SecurityScopes
from typing import Dict, Any, Callable, Awaitable, Optional
from functools import wraps

from logger import get_logger
from ..token_manager import verify_token
from ..rbac import verify_scopes

# Initialize logger
logger = get_logger(__name__)


def validate_token_header(request: Request) -> Optional[str]:
    """
    Extract and validate the authorization header from a request.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        Optional[str]: The extracted token or None if not found
        
    Raises:
        HTTPException: If the authorization header is invalid
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning(f"Missing authorization header for {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid auth scheme: {scheme}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token
    except ValueError:
        logger.warning("Invalid authorization header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )


def validate_request_body(request_body: Dict[str, Any], required_fields: list) -> bool:
    """
    Validate that a request body contains all required fields.
    
    Args:
        request_body: The request body to validate
        required_fields: List of required field names
        
    Returns:
        bool: True if all required fields are present
        
    Raises:
        HTTPException: If a required field is missing
    """
    for field in required_fields:
        if field not in request_body or request_body[field] is None:
            logger.warning(f"Missing required field: {field}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )
    return True


def require_scopes(scopes: list):
    """
    Decorator to require specific scopes for an endpoint.
    
    This decorator wraps FastAPI endpoints to require specific scopes,
    using the verify_scopes dependency.
    
    Args:
        scopes: List of required scopes
        
    Returns:
        Callable: Decorator function
    """
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract security_scopes from kwargs or create new
            security_scopes = kwargs.get("security_scopes", SecurityScopes(scopes=scopes))
            
            # Add security_scopes to kwargs if not present
            if "security_scopes" not in kwargs:
                kwargs["security_scopes"] = security_scopes
                
            # Call the original function
            return await func(*args, **kwargs)
        return wrapper
    return decorator
