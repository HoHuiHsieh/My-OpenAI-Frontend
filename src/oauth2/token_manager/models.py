"""
Token data models
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class Token(BaseModel):
    """OAuth2 token response model"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class TokenData(BaseModel):
    """Token data extracted from JWT payload"""
    username: str
    scopes: List[str] = []
    exp: Optional[datetime] = None


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # subject (username)
    scopes: List[str] = []
    iat: datetime  # issued at
    exp: datetime  # expiration time
    jti: str  # JWT ID


class RefreshTokenDB(BaseModel):
    """Refresh token DB model for ORM"""
    id: int
    token: str
    user_id: int
    expires_at: datetime
    revoked: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class RefreshToken(BaseModel):
    """Refresh token model"""
    token: str
    user_id: int
    expires_at: datetime
