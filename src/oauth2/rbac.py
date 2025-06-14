"""
Role-Based Access Control (RBAC) for OAuth2.

This module provides functionality for role-based access control,
including scope verification and permission management.
"""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import SecurityScopes
from typing import List, Dict
from sqlalchemy.exc import SQLAlchemyError
from logger import get_logger
from config import get_config
from . import oauth2_scheme
from .token_manager import decode_token
from .db import get_db
from .db.operations import check_token_revoked
from .db.models import Token

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})


class RoleBasedAccessControl:
    """
    Role-Based Access Control (RBAC) system.
    
    This class manages role-based permissions and access control.
    """
    
    def __init__(self):
        """Initialize the RBAC system with role-to-scope mappings."""
        # Default role-to-scope mappings
        self.role_scopes = {
            "user": ["models:read", "chat:read", "embeddings:read"],
            "admin": ["admin", "models:read", "chat:read", "embeddings:read"],
        }
        
        logger.info("Role-based access control initialized")
    
    def get_scopes_for_role(self, role: str) -> List[str]:
        """
        Get the list of scopes for a specific role.
        
        Args:
            role: The role name
            
        Returns:
            List[str]: List of scopes for the role
        """
        return self.role_scopes.get(role, [])
    
    def has_scope(self, role: str, scope: str) -> bool:
        """
        Check if a role has a specific scope.
        
        Args:
            role: The role name
            scope: The scope to check
            
        Returns:
            bool: True if the role has the scope, False otherwise
        """
        return scope in self.role_scopes.get(role, [])


def verify_scopes(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Verify that the token has the required scopes.
    
    This function is used as a dependency in FastAPI endpoints to ensure
    that the user has the required scopes.
    
    Args:
        security_scopes: The required scopes for the endpoint
        token: The JWT token from the request
        
    Returns:
        Dict: The decoded token payload
        
    Raises:
        HTTPException: If the token is invalid or missing required scopes
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    try:
        # Decode token without verifying scopes yet
        payload = decode_token(token)
        
        # Check if this is an access token for v1 APIs
        token_type = payload.get("type")

        if token_type == "access":
            # For access tokens, verify in database that it exists and is not revoked
            db = next(get_db())
            try:
                # First check if token exists in database
                token_record = db.query(Token).filter(Token.token == token).first()
                if not token_record:
                    logger.warning(f"Access token not found in database for user {payload.get('sub')}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token not found in database",
                        headers={"WWW-Authenticate": authenticate_value},
                    )
                
                # Then check if token is revoked
                if token_record.revoked:
                    logger.warning(f"Access token is revoked for user {payload.get('sub')}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked",
                        headers={"WWW-Authenticate": authenticate_value},
                    )
            except SQLAlchemyError as e:
                logger.error(f"Database error checking token: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error validating token",
                    headers={"WWW-Authenticate": authenticate_value},
                )
            finally:
                db.close()
        
        # Extract token scopes
        token_scopes = payload.get("scopes", [])
        
        # Check if the token has the required scopes
        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                logger.warning(
                    f"User {payload.get('sub')} missing required scope: {scope}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required: {scope}",
                    headers={"WWW-Authenticate": authenticate_value},
                )
        
        logger.info(f"Scope verification successful for user {payload.get('sub')}")
        return payload
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Scope verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )
