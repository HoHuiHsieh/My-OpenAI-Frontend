"""
Middleware for user information extraction from access token
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from database import get_session_factory
from ..token_manager import TokenManager, TokenData
from ..user_management import UserManager, User, SCOPES

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/login")

# Initialize managers
token_manager = TokenManager()
user_manager = UserManager()


def get_db():
    """Get database session"""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Get the current user from the access token in the Authorization header
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = token_manager.decode_token(token)
        if payload is None:
            raise credentials_exception
            
        username: str = payload.sub
        if username is None:
            raise credentials_exception
            
        token_data = TokenData(username=username, scopes=payload.scopes)
    except JWTError:
        raise credentials_exception
        
    user = user_manager.get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
        
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Check if the current user is active
    """
    if not current_user.active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Check if the current user has admin scope
    """
    if SCOPES.ADMIN_SCOPE not in current_user.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
