"""
Authentication Routes and Handlers

This module provides FastAPI routes for handling OAuth2 authentication,
including token generation and user authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta, datetime
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
import jwt
from logger import get_logger
from . import (
    ADMIN_TOKEN_NEVER_EXPIRES,
    ALGORITHM,
    SECRET_KEY,
    authenticate_user,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    USER_TOKEN_EXPIRE_DAYS,
    Token,
    User,
    get_current_active_user,
    pwd_context,
    verify_password
)
from .database import get_db, DBUser
from .models import PasswordChangeRequest

logger = get_logger(__name__)
router = APIRouter(tags=["authentication"])


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get a short-lived access token for future requests.
    For long-lived tokens, use the /refresh-token endpoint instead.
    """
    # We need to use the Session directly, not the context manager
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # For admin users, include all their authorized scopes by default
    # For regular users, only include the requested scopes that they have permission for
    is_admin = "admin" in user.scopes
    if is_admin:
        # Admin gets all their authorized scopes automatically
        scopes = user.scopes
        logger.info(f"Admin user {user.username} granted all available scopes: {scopes}")
    else:
        # Regular users only get scopes they specifically requested and are authorized for
        scopes = [scope for scope in form_data.scopes if scope in user.scopes]
        logger.info(f"User {user.username} granted requested scopes: {scopes}")

    # Create a standard short-lived tokenmi
    access_token = create_access_token(
        data={"sub": user.username, "scopes": scopes},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information based on the token
    """
    return current_user


class TokenResponse(BaseModel):
    """Extended token response with expiration information"""
    access_token: str
    token_type: str
    # ISO format date or "never" for admin tokens
    expires_at: Optional[str] = None


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_access_token(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new long-lived access token for the authenticated user.
    Token will be valid for the configured period (default 6 months).
    """
    # Log token refresh request
    logger.info(
        f"User '{current_user.username}' requested a long-lived token refresh")

    # Check if user is an admin (special handling for admin tokens)
    is_admin = "admin" in current_user.scopes

    # Create a long-lived token
    access_token = create_access_token(
        data={"sub": current_user.username, "scopes": current_user.scopes},
        is_admin=is_admin,
        is_long_lived=True
    )

    # Update the last_token_refresh timestamp in database
    db_user = db.query(DBUser).filter(
        DBUser.username == current_user.username).first()
    db_user.last_token_refresh = datetime.now().isoformat()
    db.commit()

    # Determine expiration for response
    if is_admin and "admin" in current_user.scopes:
        expires_at = "never"  # Admin tokens never expire if configured
    else:
        # Calculate expiration date for regular users (6 months from now)
        expires_at = (datetime.now() +
                      timedelta(days=USER_TOKEN_EXPIRE_DAYS)).isoformat()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at
    }


@router.get("/token-info")
async def get_token_info(
    current_user: User = Depends(get_current_active_user),
    authorization: str = Depends(OAuth2PasswordBearer(tokenUrl="token"))
):
    """
    Get information about the current token.
    Useful for debugging token expiration and validation.
    """
    try:
        # Decode without verifying expiration to get all token data
        payload = jwt.decode(
            authorization,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False}
        )

        # Extract important information
        username = payload.get("sub")
        scopes = payload.get("scopes", [])
        exp_timestamp = payload.get("exp")

        # Format expiration time if present
        expiration = None
        is_expired = False
        if exp_timestamp:
            expiration = datetime.fromtimestamp(exp_timestamp).isoformat()
            is_expired = datetime.now().timestamp() > exp_timestamp

        # Determine if this is an admin token
        is_admin = "admin" in scopes

        # Check if this token is long-lived (expires more than a day in the future)
        is_long_lived = exp_timestamp and exp_timestamp > datetime.now().timestamp() + \
            86400

        return {
            "username": username,
            "scopes": scopes,
            "expiration": expiration,
            "is_expired": is_expired,
            "is_admin": is_admin,
            "is_long_lived": is_long_lived,
            "never_expires": is_admin and ADMIN_TOKEN_NEVER_EXPIRES and not expiration
        }
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid token format: {str(e)}"
        )


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_change: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change password for the authenticated user.
    
    This endpoint allows a user to change their own password by providing
    their current password and a new password.
    """
    # Get the actual user from the database
    db_user = db.query(DBUser).filter(DBUser.username == current_user.username).first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_change.current_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update password in database
    db_user.hashed_password = pwd_context.hash(password_change.new_password)
    db.commit()
    
    logger.info(f"Password changed successfully for user: {current_user.username}")
    
    return {"message": "Password changed successfully"}
