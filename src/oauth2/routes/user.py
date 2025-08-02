"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Annotated

from ..token_manager import TokenManager, Token
from ..user_management import UserManager, User, UserUpdate, SCOPES
from .middleware import get_current_active_user, get_db


class CustomOAuth2PasswordRequestForm:
    """Custom OAuth2 password request form without password pattern validation"""
    
    def __init__(
        self,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        scope: Annotated[str, Form()] = "",
    ):
        self.username = username
        self.password = password
        self.scopes = scope.split() if scope else []

# Initialize managers
token_manager = TokenManager()
user_manager = UserManager()

# Create router
user_router = APIRouter(prefix="/user", tags=["user"])


@user_router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: CustomOAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = user_manager.authenticate_user(
        db, form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = token_manager.create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )
    
    # Create refresh token
    refresh_token = token_manager.create_refresh_token(db, user.id)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=token_manager.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token
    )


@user_router.get("/", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user information
    """
    return current_user


@user_router.put("/", response_model=User)
async def update_current_user_info(
    user_update: UserUpdate, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user information
    """
    updated_user = user_manager.update_user(
        db, current_user.username, user_update
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user


@user_router.get("/scopes", response_model=list[str])
async def get_scopes():
    """
    Get the scopes
    """
    return SCOPES.keys()