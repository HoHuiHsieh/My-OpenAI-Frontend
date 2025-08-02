"""
User data models
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user model"""
    username: str
    email: EmailStr
    fullname: str
    active: bool = True
    scopes: List[str] = []


class UserCreate(UserBase):
    """User creation model"""
    password: str


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    fullname: Optional[str] = None
    password: Optional[str] = None
    active: Optional[bool] = None
    scopes: Optional[List[str]] = None


class User(UserBase):
    """User model with all fields"""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
