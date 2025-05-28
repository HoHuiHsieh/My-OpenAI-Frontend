"""
OAuth2 Authentication and Authorization Module

This module handles authentication and authorization using OAuth2 protocol
for the My OpenAI Frontend service. It provides functionality for:
- Token validation
- User authentication
- Role-based access control
- Integration with various identity providers
- PostgreSQL database integration for user management
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import BaseModel
from typing import List, Optional
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import logging
from config import get_config
from .database import get_db, DBUser, initialize_db
from logger import get_logger


# Initialize the enhanced logging system
logger = get_logger(__name__)

# Load OAuth2 config
config = get_config()
oauth2_config = config.get("oauth2", {})

# Token URL - this is the endpoint where clients can request tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Get configuration from config.yml
SECRET_KEY = oauth2_config.get("secret_key", "your-secret-key-placeholder")
ALGORITHM = oauth2_config.get("algorithm", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = oauth2_config.get(
    "access_token_expire_minutes", 30)
USER_TOKEN_EXPIRE_DAYS = oauth2_config.get(
    "user_token_expire_days", 180)  # 6 months by default
ADMIN_TOKEN_NEVER_EXPIRES = oauth2_config.get(
    "admin_token_never_expires", True)

# Define pydantic models for requests and responses


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    scopes: List[str] = []


# Password context for hashing and verifying passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize database on module import
try:
    initialize_db()
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to initialize database: {str(e)}")


def verify_password(plain_password, hashed_password):
    """
    Verify a password against its hash using passlib's CryptContext.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_user(db_session: Session, username: str):
    """
    Get user from database
    """
    # Make sure we're using the actual session object, not the context manager
    db_user = db_session.query(DBUser).filter(
        DBUser.username == username).first()
    if db_user:
        return User(
            username=db_user.username,
            email=db_user.email,
            full_name=db_user.full_name,
            disabled=db_user.disabled,
            scopes=db_user.scopes
        )
    return None


def authenticate_user(db_session: Session, username: str, password: str):
    """
    Authenticate a user by username and password
    """
    db_user = db_session.query(DBUser).filter(
        DBUser.username == username).first()
    if not db_user:
        return False
    if not verify_password(password, db_user.hashed_password):
        return False

    return User(
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        scopes=db_user.scopes
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, is_admin: bool = False, is_long_lived: bool = False):
    """
    Create an access token with configurable expiration

    Args:
        data: The data payload to encode in the token
        expires_delta: Optional explicit expiration time
        is_admin: Whether this token is for an admin user
        is_long_lived: Whether this token is a long-lived token

    Returns:
        str: JWT access token
    """
    to_encode = data.copy()

    # Handle token expiration based on parameters
    if expires_delta:
        # Use explicit expiration if provided
        expire = datetime.now() + expires_delta
    elif is_admin and ADMIN_TOKEN_NEVER_EXPIRES:
        # Admin tokens never expire if configured
        # We don't set the "exp" claim at all, making it a non-expiring token
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    elif is_long_lived:
        # Long-lived user tokens (6 months by default)
        expire = datetime.now() + timedelta(days=USER_TOKEN_EXPIRE_DAYS)
    else:
        # Regular short-lived session tokens
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Decode and validate the JWT token to get the current user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": f"Bearer scope=\"{security_scopes.scope_str}\""},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except jwt.PyJWTError:
        raise credentials_exception

    # The db object here is the actual Session, not the context manager
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception

    # Check if the token has the required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required scope: {scope}",
                headers={
                    "WWW-Authenticate": f"Bearer scope=\"{security_scopes.scope_str}\""},
            )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Check if the current user is active
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
