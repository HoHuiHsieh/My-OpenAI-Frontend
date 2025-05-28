"""
Shared data models for authentication API endpoints
"""

from pydantic import BaseModel
from typing import List, Optional

class PasswordChangeRequest(BaseModel):
    """Request model for changing a user's password"""
    current_password: str
    new_password: str
