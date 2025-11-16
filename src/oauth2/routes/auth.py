"""
OAuth2 tokens validation and refresh endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database.schema import UserDB
from ..token_manager import TokenManager, Token
from ..user_management import User
from .middleware import get_current_active_user, get_db

# Initialize token manager
token_manager = TokenManager()

# Create router
auth_router = APIRouter(prefix="/auth", tags=["auth"])


class RefreshRequest(BaseModel):
    """Refresh token request body"""
    refresh_token: str


@auth_router.get("/")
async def validate_token(current_user: User = Depends(get_current_active_user)):
    """
    Validate the access token
    """
    return {"username": current_user.username, "scopes": current_user.scopes}


@auth_router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh the access token using a refresh token
    """
    user_id = token_manager.verify_refresh_token(db,
                                                 refresh_request.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get the user from the database
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user or inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new tokens (revoke the old refresh token)
    access_token = token_manager.create_access_token(
        data={"sub": user.username, "scopes": user.scopes}
    )
    new_refresh_token = token_manager.create_refresh_token(
        db, user_id, refresh_request.refresh_token)

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=token_manager.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=new_refresh_token
    )
