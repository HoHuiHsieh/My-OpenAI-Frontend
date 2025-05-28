"""
OAuth2 Admin Controller

This module provides admin-level functionality for user management
and authentication control within the My OpenAI Frontend service.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from . import User, pwd_context, create_access_token, USER_TOKEN_EXPIRE_DAYS
from .dependencies import require_admin
from .database import get_db, DBUser
from logger import get_logger

logger = get_logger(__name__)

# Create router with admin tag and prefix
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)]
)

# Models for requests and responses
class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: str
    disabled: bool = False
    scopes: List[str] = []

class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    scopes: Optional[List[str]] = None

class UserResponse(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: List[str] = []

# Models for token management
class GenerateTokenRequest(BaseModel):
    """Request model for generating a token for a user"""
    username: str
    scopes: Optional[List[str]] = None  # If None, use all user's allowed scopes

class TokenResponse(BaseModel):
    """Extended token response with expiration information"""
    access_token: str
    token_type: str
    expires_at: Optional[str] = None  # ISO format date or "never" for admin tokens

class TokenStatusResponse(BaseModel):
    """Response model for token status information"""
    username: str
    last_refresh: Optional[str] = None  # ISO format date
    next_refresh_required: Optional[str] = None  # ISO format date or "never" for admin

# Admin routes for user management
@router.get("/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    """
    Get all users (admin access required)
    """
    db_users = db.query(DBUser).all()
    return [
        UserResponse(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            scopes=user.scopes
        )
        for user in db_users
    ]

@router.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str, db: Session = Depends(get_db)):
    """
    Get a specific user by username (admin access required)
    """
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    return UserResponse(
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        scopes=db_user.scopes
    )

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user (admin access required)
    """
    # Check if user already exists
    existing_user = db.query(DBUser).filter(DBUser.username == user.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{user.username}' already exists"
        )
    
    # Hash the password using passlib
    hashed_password = pwd_context.hash(user.password)
    
    # Create user in database
    db_user = DBUser(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        disabled=user.disabled,
        scopes=user.scopes
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        scopes=db_user.scopes
    )

@router.put("/users/{username}", response_model=UserResponse)
async def update_user(username: str, user: UserUpdate, db: Session = Depends(get_db)):
    """
    Update an existing user (admin access required)
    """
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Update user fields
    if user.email is not None:
        db_user.email = user.email
        
    if user.full_name is not None:
        db_user.full_name = user.full_name
        
    if user.disabled is not None:
        db_user.disabled = user.disabled
        
    if user.scopes is not None:
        db_user.scopes = user.scopes
    
    # Commit changes to database
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        scopes=db_user.scopes
    )

@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(username: str, db: Session = Depends(get_db)):
    """
    Delete a user (admin access required)
    """
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Don't allow deleting the admin user
    if username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin user"
        )
    
    # Delete user
    db.delete(db_user)
    db.commit()

@router.post("/token/{username}", response_model=TokenResponse)
async def generate_token_for_user(
    username: str,
    request: Optional[GenerateTokenRequest] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate an access token for any registered user (admin access required)
    """
    # Find the user in the database
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Check if user is disabled
    if db_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{username}' is disabled"
        )
    
    # Determine scopes to include in the token
    scopes = request.scopes if request and request.scopes else db_user.scopes
    
    # Ensure scopes are a subset of what the user is allowed
    valid_scopes = [scope for scope in scopes if scope in db_user.scopes]
    
    # Check if user is an admin (for token expiration)
    is_admin = "admin" in valid_scopes
    
    # Create the token
    access_token = create_access_token(
        data={"sub": username, "scopes": valid_scopes},
        is_admin=is_admin,
        is_long_lived=True
    )
    
    # Update the last_token_refresh timestamp in database
    db_user.last_token_refresh = datetime.now().isoformat()
    db.commit()
    
    # Determine expiration for response
    if is_admin:
        expires_at = "never"  # Admin tokens never expire
    else:
        # Calculate expiration date for regular users
        expires_at = (datetime.now() + timedelta(days=USER_TOKEN_EXPIRE_DAYS)).isoformat()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": expires_at
    }

@router.get("/tokens", response_model=List[TokenStatusResponse])
async def get_all_tokens(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get token status information for all users (admin access required)
    """
    db_users = db.query(DBUser).all()
    token_statuses = []
    
    for db_user in db_users:
        # Check if user has admin scope
        is_admin = "admin" in db_user.scopes
        
        # Calculate next refresh date
        next_refresh = None
        if db_user.last_token_refresh:
            if is_admin:
                next_refresh = "never"
            else:
                # Convert ISO string to datetime
                try:
                    last_refresh = datetime.fromisoformat(db_user.last_token_refresh)
                    next_refresh = (last_refresh + timedelta(days=USER_TOKEN_EXPIRE_DAYS)).isoformat()
                except ValueError:
                    # Handle invalid ISO format gracefully
                    logger.warning(f"Invalid ISO format for user {db_user.username}'s last_token_refresh")
        
        token_statuses.append({
            "username": db_user.username,
            "last_refresh": db_user.last_token_refresh,
            "next_refresh_required": next_refresh
        })
    return token_statuses

@router.get("/tokens/{username}", response_model=TokenStatusResponse)
async def get_user_token_status(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get token status information for a user (admin access required)
    """
    # Find the user in the database
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Check if user has admin scope
    is_admin = "admin" in db_user.scopes
    
    # Calculate next refresh date
    next_refresh = None
    if db_user.last_token_refresh:
        if is_admin:
            next_refresh = "never"
        else:
            # Convert ISO string to datetime
            try:
                last_refresh = datetime.fromisoformat(db_user.last_token_refresh)
                next_refresh = (last_refresh + timedelta(days=USER_TOKEN_EXPIRE_DAYS)).isoformat()
            except ValueError:
                # Handle invalid ISO format gracefully
                logger.warning(f"Invalid ISO format for user {username}'s last_token_refresh")
    
    return {
        "username": db_user.username,
        "last_refresh": db_user.last_token_refresh,
        "next_refresh_required": next_refresh
    }

@router.delete("/token/{username}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_user_token(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Revoke a user's token by removing their last_token_refresh timestamp (admin access required)
    """
    # Find the user in the database
    db_user = db.query(DBUser).filter(DBUser.username == username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Clear the token refresh timestamp to revoke any existing token
    db_user.last_token_refresh = None
    db.commit()
    
    return None  # 204 No Content response
