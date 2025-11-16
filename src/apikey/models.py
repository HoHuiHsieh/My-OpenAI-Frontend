"""
API key data models
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# Import ApiKeyDB from centralized database schema
from database.schema import ApiKeyDB


class ApiKey(BaseModel):
    """API key response model"""
    apiKey: str
    expires_in: int


class ApiKeyData(BaseModel):
    """API key data extracted from JWT payload"""
    user_id: int
    scopes: List[str] = []
    exp: Optional[datetime] = None