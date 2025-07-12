"""
Scope-Based Access Control for OAuth2.

This module provides functionality for scope-based access control,
including scope verification and permission management.
"""

from typing import List, Dict, Set, Any
try:
    from fastapi import Depends, HTTPException, Security, status
    from fastapi.security import SecurityScopes
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    # For development/testing without FastAPI installed
    Depends = lambda x: x
    HTTPException = Exception
    Security = lambda x: x
    status = type('status', (), {'HTTP_401_UNAUTHORIZED': 401, 'HTTP_403_FORBIDDEN': 403, 'HTTP_500_INTERNAL_SERVER_ERROR': 500})
    SecurityScopes = type('SecurityScopes', (), {'scopes': [], 'scope_str': ''})
    SQLAlchemyError = Exception
from logger import get_logger
from config import get_config
from . import oauth2_scheme
from .token_manager import decode_token
from .db import get_db
from .db.models import Token
from .scopes import Scopes, available_scopes
# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})


class ScopeBasedAccessControl:
    """
    Scope-Based Access Control system.
    
    This class manages scope-based permissions and access control.
    """
    
    def __init__(self):
        """Initialize the scope-based access control system."""
        # Available scopes
        self.available_scopes = [scope.value for scope in available_scopes]
        
        logger.info("Scope-based access control initialized")

    def has_scope(self, scopes: List[str], required_scope: str) -> bool:
        """
        Check if a list of scopes includes a specific required scope.
        
        Args:
            scopes: List of scopes to check
            required_scope: The scope to check for (string or Scopes enum)
            
        Returns:
            bool: True if the required scope is in the list, False otherwise
        """
        if isinstance(required_scope, Scopes):
            required_scope = required_scope.value
        return required_scope in scopes
    
    def has_any_scope(self, scopes: List[str], required_scopes: List[str]) -> bool:
        """
        Check if a list of scopes includes any of the required scopes.
        
        Args:
            scopes: List of scopes to check
            required_scopes: List of required scopes (strings or Scopes enums)
            
        Returns:
            bool: True if any of the required scopes are in the list, False otherwise
        """
        # Convert any Scope enum values to strings
        required_scope_values = [
            scope.value if isinstance(scope, Scopes) else scope
            for scope in required_scopes
        ]
        return any(scope in scopes for scope in required_scope_values)
    
    def has_all_scopes(self, scopes: List[str], required_scopes: List[str]) -> bool:
        """
        Check if a list of scopes includes all of the required scopes.
        
        Args:
            scopes: List of scopes to check
            required_scopes: List of required scopes (strings or Scopes enums)
            
        Returns:
            bool: True if all of the required scopes are in the list, False otherwise
        """
        # Convert any Scope enum values to strings
        required_scope_values = [
            scope.value if isinstance(scope, Scopes) else scope
            for scope in required_scopes
        ]
        return all(scope in scopes for scope in required_scope_values)
    
    def validate_scopes(self, scopes: List[str]) -> List[str]:
        """
        Validate a list of scopes against available scopes.
        
        Args:
            scopes: List of scopes to validate
            
        Returns:
            List[str]: List of valid scopes (invalid scopes are removed)
        """
        valid_scopes = []
        for scope in scopes:
            if scope in self.available_scopes:
                valid_scopes.append(scope)
            else:
                logger.warning(f"Invalid scope requested: {scope}")
        
        return valid_scopes
    
    def convert_to_scope_values(self, scopes: List[Any]) -> List[str]:
        """
        Convert a list of scopes (which may be strings or Scopes enums) to string values.
        
        Args:
            scopes: List of scopes (strings or Scopes enums)
            
        Returns:
            List[str]: List of scope string values
        """
        return [
            scope.value if isinstance(scope, Scopes) else scope
            for scope in scopes
        ]


# Create a global instance of the scope control
scope_control = ScopeBasedAccessControl()


def verify_scopes(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)):
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


def require_scopes(required_scopes: List[Any]):
    """
    Create a dependency that requires specific scopes.
    
    This function creates a dependency that can be used in FastAPI
    endpoints to require specific scopes.
    
    Args:
        required_scopes: List of required scopes (strings or Scopes enums)
        
    Returns:
        function: A dependency function that checks for the required scopes
    """
    # Convert any Scopes enum values to strings
    required_scope_values = [
        scope.value if isinstance(scope, Scopes) else scope
        for scope in required_scopes
    ]
    
    def dependency(token_data: Dict = Depends(verify_scopes)):
        token_scopes = token_data.get("scopes", [])
        for scope in required_scope_values:
            if scope not in token_scopes:
                logger.warning(
                    f"User {token_data.get('sub')} missing required scope: {scope}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required: {scope}",
                )
        return token_data
    return dependency


# Convenience functions for common scope requirements
def require_admin():
    """
    Create a dependency that requires admin scope.
    
    Returns:
        function: A dependency function that checks for the admin scope
    """
    return require_scopes([Scopes.ADMIN])

def require_models_read():
    """
    Create a dependency that requires models:read scope.
    
    Returns:
        function: A dependency function that checks for the models:read scope
    """
    return require_scopes([Scopes.MODELS_READ])

def require_chat_read():
    """
    Create a dependency that requires chat:read scope.
    
    Returns:
        function: A dependency function that checks for the chat:read scope
    """
    return require_scopes([Scopes.CHAT_READ])

def require_embeddings_read():
    """
    Create a dependency that requires embeddings:read scope.
    
    Returns:
        function: A dependency function that checks for the embeddings:read scope
    """
    return require_scopes([Scopes.EMBEDDINGS_READ])
