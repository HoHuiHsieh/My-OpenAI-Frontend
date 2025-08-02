"""
Middleware for API key validation
"""

from typing import Optional
from fastapi import HTTPException, status, Depends, Header
from fastapi.security import SecurityScopes
from .manager import ApiKeyManager
from .models import ApiKeyData

# Initialize API key manager
api_key_manager = ApiKeyManager()


def get_api_key_from_header(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Extract API key from Authorization header"""
    if not authorization:
        return None
    
    # Support both "Bearer <token>" and "ApiKey <token>" formats
    if authorization.startswith("Bearer "):
        return authorization[7:]
    elif authorization.startswith("ApiKey "):
        return authorization[7:]
    else:
        # Direct API key without prefix
        return authorization


def validate_api_key(
    security_scopes: SecurityScopes, 
    api_key: Optional[str] = Depends(get_api_key_from_header)
) -> ApiKeyData:
    """Dependency to validate API key and check required scopes"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    api_key_data = api_key_manager.validate_api_key(api_key)
    if not api_key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check if the API key has the required scopes
    if security_scopes.scopes:
        # Check if user has all required scopes
        for scope in security_scopes.scopes:
            if scope not in api_key_data.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scopes: {', '.join(security_scopes.scopes)}",
                    headers={"WWW-Authenticate": f"ApiKey scope=\"{' '.join(security_scopes.scopes)}\""},
                )
    
    return api_key_data


def get_optional_api_key(api_key: Optional[str] = Depends(get_api_key_from_header)) -> Optional[ApiKeyData]:
    """Optional API key validation - returns None if no API key provided"""
    if not api_key:
        return None
    
    return api_key_manager.validate_api_key(api_key)