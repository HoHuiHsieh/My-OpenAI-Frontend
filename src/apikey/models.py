"""
API key data models
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class ApiKey(BaseModel):
    """API key response model"""
    apiKey: str
    expires_in: int


class ApiKeyData(BaseModel):
    """API key data extracted from JWT payload"""
    user_id: int
    scopes: List[str] = []
    exp: Optional[datetime] = None


class ApiKeyDB(BaseModel):
    """API key DB model for ORM"""
    id: int
    apiKey: str
    user_id: int
    expires_at: datetime
    revoked: bool = False
    created_at: datetime

    class Config:
        from_attributes = True