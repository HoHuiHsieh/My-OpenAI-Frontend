"""
Access token endpoints for OAuth2.

This module provides endpoints for managing API access tokens,
including token creation, refresh, and information retrieval.
"""

from fastapi import Depends, HTTPException, status, Security
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
import jwt

from logger import get_logger
from ..db import get_db
from ..token_manager import create_access_token, decode_token
from ..rbac import verify_scopes
from ..db.operations import create_token_for_user, get_user_by_username
from ..db.operations import check_token_revoked
from . import access_router

# Initialize logger
logger = get_logger(__name__)


class TokenRequest(BaseModel):
    """Request model for token information."""
    token: str

class AccessToken(BaseModel):
    """Access token response model."""
    access_token: str
    token_type: str
    expires_at: Optional[datetime] = None


class TokenInfo(BaseModel):
    """Token information response model."""
    username: str
    type: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    issued_at: datetime
    active: bool


@access_router.post("/refresh", response_model=AccessToken)
async def refresh_access_token(
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=[]),
    db: Session = Depends(get_db)
):
    """
    Refresh or create a new API access token.
    
    This endpoint creates a new API access token for the authenticated user,
    with the same scopes as the session token.
    
    Args:
        token_data: Verified token data
        db: Database session
        
    Returns:
        AccessToken: New access token
    """
    # Extract username and scopes from token
    username = token_data.get("sub")
    scopes = token_data.get("scopes", [])
    role = token_data.get("role", "user")
    is_admin = "admin" in scopes or role == "admin"
    
    # Create new access token
    token = create_access_token(
        username=username,
        scopes=scopes,
        is_admin=is_admin
    )
    
    # Save token to database
    user = get_user_by_username(db, username)
    
    if user is None:
        logger.warning(f"User not found for token refresh: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Calculate expiration time
    token_data = decode_token(token)
    expires_at = None
    if "exp" in token_data:
        expires_at = datetime.fromtimestamp(token_data["exp"])    # Store token in database and revoke old access tokens
    create_token_for_user(
        db=db,
        username=username,
        token_value=token,
        token_type="access",
        scopes=scopes,
        expires_at=expires_at,
        metadata={"created_from": "refresh"},  # This is passed as metadata param but stored as token_metadata
        revoke_old_access_tokens=True  # Revoke existing access tokens for security
    )
    
    logger.info(f"Access token refreshed for user: {username}")
    return AccessToken(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at
    )


@access_router.post("/info", response_model=TokenInfo)
async def get_token_info(
    token_request: TokenRequest,
    _token_data: Dict[str, Any] = Security(verify_scopes, scopes=[]),  # For authentication only
    db: Session = Depends(get_db)
):
    """
    Get information about the posted access token.
    
    This endpoint returns detailed information about the
    access token provided in the request body, not the token
    used for authentication. It verifies the token's validity,
    checks if it has been revoked in the database, and returns
    detailed information about it.
    
    Args:
        token_request: The request containing the access token to verify
        _token_data: Verified token data from the authentication token (unused)
        db: Database session to check if the token has been revoked
        
    Returns:
        TokenInfo: Token information including validity status
    """
    try:
        # Verify the posted token
        token_data = decode_token(token_request.token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token format"
            )
            
        # Extract token information
        username = token_data.get("sub")
        token_type = token_data.get("type", "unknown")
        scopes = token_data.get("scopes", [])
          # Calculate times
        expires_at = None
        if "exp" in token_data:
            expires_at = datetime.fromtimestamp(token_data["exp"])
            
        issued_at = datetime.utcnow()
        if "iat" in token_data:
            issued_at = datetime.fromtimestamp(token_data["iat"])
        
        # Check if token is active
        active = True
        if expires_at and expires_at < datetime.utcnow():
            active = False
              # Verify token has not been revoked by checking the database
        is_revoked = check_token_revoked(db, token_request.token)
        
        if is_revoked:
            active = False
            logger.info(f"Token info retrieved for revoked token of user: {username}")
        else:
            logger.debug(f"Token info retrieved for active token of user: {username}")
        
        return TokenInfo(
            username=username,
            type=token_type,
            scopes=scopes,
            expires_at=expires_at,
            issued_at=issued_at,
            active=(active and not is_revoked)  # Token is active only if not expired and not revoked
        )
    except jwt.PyJWTError as e:
        logger.warning(f"Invalid token provided: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing token info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing token information"
        )
