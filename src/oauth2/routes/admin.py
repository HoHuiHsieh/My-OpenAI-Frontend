"""
Admin endpoints for OAuth2.

This module provides endpoints for administrative functions,
including user and token management.
"""

from fastapi import Depends, HTTPException, status, Security, Path, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta

from logger import get_logger
from ..db import get_db
from ..db.operations import get_user_by_username, create_token_for_user
from ..token_manager import create_access_token, token_type_access, decode_token
from ..scope_control import verify_scopes
from ..db.operations import get_all_users
from ..db.operations import get_user_by_username
from ..db.operations import create_user
from ..db.operations import update_user
from ..db.operations import delete_user
from ..db.models import Token, User
from ..db.operations import delete_user_token
from ..scopes import available_scopes
from . import admin_router

# Initialize logger
logger = get_logger(__name__)


# Request and response models
class UserCreate(BaseModel):
    """User creation request model."""
    username: str
    password: str
    scopes: List[str]
    disabled: bool
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    

class UserUpdate(BaseModel):
    """User update request model."""
    full_name: Optional[str] = None
    password: Optional[str] = None
    scopes: List[str] = []
    email: Optional[EmailStr] = None
    disabled: Optional[bool] = None


class UserResponse(BaseModel):
    """User response model."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False  # Default to not disabled if None
    scopes: List[str] = []
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Token response model."""
    id: int
    token_type: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    revoked: bool
    created_at: datetime


class AccessTokenCreate(BaseModel):
    """Access token creation request model."""
    scopes: List[str]
    expires_days: Optional[int] = None
    never_expires: bool = False


class AccessTokenResponse(BaseModel):
    """Access token response model."""
    access_token: str
    token_type: str
    expires_at: Optional[datetime] = None
    scopes: List[str]


class AccessTokenResponse(BaseModel):
    """Access token list item response model."""
    id: int
    username: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    revoked: bool
    created_at: datetime


# User management endpoints
@admin_router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    List all users with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Returns:
        List[UserResponse]: List of users
    """
    users = get_all_users(db, skip=skip, limit=limit)
    logger.info(f"Admin {token_data.get('sub')} listed users (skip={skip}, limit={limit})")
    
    # Convert to response models
    return [
        UserResponse(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled if user.disabled is not None else False,
            scopes=user.scopes,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        for user in users
    ]


@admin_router.get("/users/{username}", response_model=UserResponse)
async def get_user(
    username: str = Path(..., description="Username of the user to retrieve"),
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Get user details by username.
    
    Args:
        username: Username of the user to retrieve
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Returns:
        UserResponse: User details
        
    Raises:
        HTTPException: If user is not found
    """
    
    user = get_user_by_username(db, username)
    if user is None:
        logger.warning(f"Admin {token_data.get('sub')} attempted to get non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )
    logger.info(f"Admin {token_data.get('sub')} retrieved user: {username}")
    return UserResponse(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        scopes=user.scopes,
        disabled=user.disabled if user.disabled is not None else False,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@admin_router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user_data: UserCreate,
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    
    Args:
        user_data: User data for creation
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Returns:
        UserResponse: Created user details
        
    Raises:
        HTTPException: If user creation fails
    """
    print(f"Creating user: {user_data}")
    
    # Check if user already exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        logger.warning(f"Admin {token_data.get('sub')} attempted to create existing user: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {user_data.username} already exists"
        )
    
    # Create new user
    user = create_user(
        db=db,
        username=user_data.username,
        password=user_data.password,
        email=user_data.email,
        full_name=user_data.full_name,
        disabled=user_data.disabled,
        scopes=user_data.scopes
    )
    
    if user is None:
        logger.error(f"Admin {token_data.get('sub')} failed to create user: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    logger.info(f"Admin {token_data.get('sub')} created new user: {user_data.username}")
    return UserResponse(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        scopes=user.scopes,
        disabled=user.disabled if user.disabled is not None else False,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@admin_router.put("/users/{username}", response_model=UserResponse)
async def update_user_info(
    username: str,
    user_data: UserUpdate,    
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Update user information.
    
    Args:
        username: Username of the user to update
        user_data: User data for update
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Returns:
        UserResponse: Updated user details
        
    Raises:
        HTTPException: If user update fails
    """
    # Check if user exists
    existing_user = get_user_by_username(db, username)
    if not existing_user:
        logger.warning(f"Admin {token_data.get('sub')} attempted to update non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )
    
    # Prepare update data
    update_data = user_data.dict(exclude_unset=True)

    # Update user
    user = update_user(
        db=db,
        username=username,
        update_data=update_data
    )
    
    if user is None:
        logger.error(f"Admin {token_data.get('sub')} failed to update user: {username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )
    
    logger.info(f"Admin {token_data.get('sub')} updated user: {username}")
    return UserResponse(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        scopes=user.scopes,
        disabled=user.disabled if user.disabled is not None else False,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@admin_router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_account(
    username: str = Path(..., description="Username of the user to delete"),
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Delete a user account.
    
    Args:
        username: Username of the user to delete
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Raises:
        HTTPException: If user deletion fails
    """
    
    # Check if user exists
    existing_user = get_user_by_username(db, username)
    if not existing_user:
        logger.warning(f"Admin {token_data.get('sub')} attempted to delete non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )
    
    # Prevent self-deletion
    admin_username = token_data.get("sub")
    if username == admin_username:
        logger.warning(f"Admin {admin_username} attempted to delete own account")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Delete user
    update_data = {
        "disabled": True,  # Disable the user instead of deleting immediately
    }
    success = update_user(
        db=db,
        username=username,
        update_data=update_data
    )
    if not success:
        logger.error(f"Admin {admin_username} failed to delete user: {username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
    
    logger.info(f"Admin {admin_username} deleted user: {username}")


# Token management endpoints
@admin_router.get("/access", response_model=List[AccessTokenResponse])
async def list_access_tokens(
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    List all access tokens.
    
    Args:
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Returns:
        List[AccessTokenResponse]: List of access tokens with user information
    """
    
    # Get all access tokens with user information
    tokens = (
        db.query(Token, User.username)
        .join(User, Token.user_id == User.id)
        .filter(Token.token_type == token_type_access)
        .all()
    )
    
    admin_username = token_data.get("sub")
    logger.info(f"Admin {admin_username} listed all access tokens")
    
    # Format response
    result = [
        AccessTokenResponse(
            id=token.id,
            username=username,
            scopes=token.scopes,
            expires_at=token.expires_at,
            revoked=token.revoked,
            created_at=token.created_at
        )
        for token, username in tokens
    ]
    
    return result


@admin_router.post("/access/{username}", response_model=AccessTokenResponse)
async def create_access_token_for_user(
    username: str = Path(..., description="Username to create token for"),
    token_request: AccessTokenCreate = Depends(),
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Create an access token for a user.
    
    Args:
        username: Username to create token for
        token_request: Access token creation request
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Returns:
        AccessTokenResponse: Created access token details
        
    Raises:
        HTTPException: If token creation fails
    """

    # Check if user exists
    user = get_user_by_username(db, username)
    if user is None:
        admin_username = token_data.get("sub")
        logger.warning(f"Admin {admin_username} attempted to create token for non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )
    
    # Determine if token is for admin user based on requested scopes
    from ..scopes import Scopes
    is_admin = Scopes.ADMIN.value in token_request.scopes
    
    # Create access token
    token = create_access_token(
        username=username,
        scopes=token_request.scopes,
        is_admin=is_admin,
        expires_days=token_request.expires_days,
        never_expires=token_request.never_expires
    )
    
    # Calculate expiration time
    expires_at = None
    token_payload = decode_token(token)
    if "exp" in token_payload:
        expires_at = datetime.fromtimestamp(token_payload["exp"])    # Save token in database and revoke old access tokens
    db_token = create_token_for_user(
        db=db,
        username=username,
        token_value=token,
        token_type=token_type_access,
        scopes=token_request.scopes,
        expires_at=expires_at,
        metadata={"created_by_admin": token_data.get("sub")},  # This is passed as metadata param but stored as token_metadata
        delete_old_access_tokens=True  # Explicitly revoke any existing access tokens for this user
    )
    
    if db_token is None:
        admin_username = token_data.get("sub")
        logger.error(f"Admin {admin_username} failed to create token for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create access token"
        )
    
    admin_username = token_data.get("sub")
    logger.info(f"Admin {admin_username} created access token for user: {username}")
    
    return AccessTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
        scopes=token_request.scopes
    )


@admin_router.delete("/access/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_access_token(
    username: str = Path(..., description="Username of the token owner"),
    token_id: int = Query(..., description="ID of the token to revoke"),
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Revoke an access token for a user.
    
    Args:
        username: Username of the token owner
        token_id: ID of the token to revoke
        token_data: Verified token data (must have admin scope)
        db: Database session
        
    Raises:
        HTTPException: If token revocation fails
    """
    # Check if user exists
    user = get_user_by_username(db, username)
    if user is None:
        admin_username = token_data.get("sub")
        logger.warning(f"Admin {admin_username} attempted to revoke token for non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )
    
    # Revoke token
    success = delete_user_token(db=db, username=username, token_id=token_id)
    if not success:
        admin_username = token_data.get("sub")
        logger.error(f"Admin {admin_username} failed to revoke token {token_id} for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token {token_id} not found for user {username} or could not be revoked"
        )
    
    admin_username = token_data.get("sub")
    logger.info(f"Admin {admin_username} revoked token {token_id} for user: {username}")


@admin_router.get("/scopes", response_model=List[str])
async def get_available_scopes(
    token_data: Dict[str, Any] = Security(verify_scopes, scopes=["admin"]),
    db: Session = Depends(get_db)
):
    """
    Get all available scopes.

    Args:
        token_data: Verified token data (must have admin scope)
        db: Database session

    Returns:
        List[str]: List of available scopes
    """
    logger.info(f"Admin {token_data.get('sub')} retrieved available scopes")
    return available_scopes
