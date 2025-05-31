"""
Session token endpoints for OAuth2.

This module provides endpoints for session token management,
including login and user information retrieval.
"""

from fastapi import Depends, HTTPException, status, Response, Security
from fastapi.security import OAuth2PasswordRequestForm, SecurityScopes
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

from logger import get_logger
from ..db import get_db
from ..auth import authenticate_user, verify_password, get_password_hash
from ..token_manager import create_session_token, verify_token
from ..rbac import verify_scopes
from ..db.operations import get_user_by_username
from . import session_router

# Initialize logger
logger = get_logger(__name__)


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str
    expires_at: datetime = None


class UserInfo(BaseModel):
    """User information response model."""
    username: str
    email: str = None
    full_name: str = None
    disabled: bool = False
    role: str = "user"
    scopes: List[str] = []


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str
    new_password: str


@session_router.post("", response_model=Token)
async def login_for_session_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login to obtain a session token.
    
    This endpoint authenticates a user and returns a session token
    for web application access.
    
    Args:
        form_data: Username and password form data
        db: Database session
        
    Returns:
        Token: Session token response
        
    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate user
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get scopes based on user role
    scopes = form_data.scopes or []
    if user.role == "admin":
        scopes.append("admin")
    
    # Create session token
    token = create_session_token(
        username=user.username,
        scopes=scopes,
        additional_data={"role": user.role}
    )
    
    # Calculate expiration time for response
    token_data = verify_token(token)
    expires_at = None
    if "exp" in token_data:
        expires_at = datetime.fromtimestamp(token_data["exp"])
    
    logger.info(f"Session token created for user: {form_data.username}")
    return Token(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at
    )


@session_router.get("/user", response_model=UserInfo)
async def get_current_user(
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=[]),
    db: Session = Depends(get_db)
):
    """
    Get information about the current authenticated user.
    
    This endpoint returns information about the user based on
    the session token.
    
    Args:
        token_data: Verified token data
        db: Database session
        
    Returns:
        UserInfo: Current user information
    """
    # Extract username from token
    username = token_data.get("sub")
    
    # Get user from database
    user = get_user_by_username(db, username)
    
    if user is None:
        logger.warning(f"User not found for token: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.debug(f"Returning user info for: {username}")
    return UserInfo(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        role=user.role,
        scopes=token_data.get("scopes", [])
    )

@session_router.post("/changePwd")
async def change_password(
    update_data: PasswordChangeRequest,
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=[]),
    db: Session = Depends(get_db)
):
    """
    Change the password for the authenticated user.
    
    This endpoint allows the user to change their password
    by providing the current password and the new password.

    Args:
        update_data: Current and new password data
        token_data: Verified token data
        db: Database session

    Raises:
        HTTPException: If the current password is incorrect or user not found
    """
    # Extract username from token
    username = token_data.get("sub")
    
    # Get user from database
    user = get_user_by_username(db, username)
    
    if user is None:
        logger.warning(f"User not found for password change: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify current password
    if not verify_password(update_data.current_password, user.hashed_password):
        logger.warning(f"Incorrect current password for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password"
        )
    
    # Update password
    user.hashed_password = get_password_hash(update_data.new_password)
    db.commit()
    db.refresh(user)
    logger.info(f"Password changed successfully for user: {username}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
    