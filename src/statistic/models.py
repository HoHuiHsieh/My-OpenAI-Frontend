"""
Usage Statistics Models

This module defines Pydantic models for usage statistics data.
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: Optional[int] = None
    total_tokens: int


class UsageEntry(BaseModel):
    """Individual usage log entry."""
    id: Optional[int] = None
    timestamp: datetime
    api_type: str
    user_id: str
    model: str
    request_id: Optional[str] = None
    prompt_tokens: int
    completion_tokens: Optional[int] = None
    total_tokens: int
    input_count: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None


class UsageResponse(BaseModel):
    """
    Model for usage statistics response.
    
    Attributes:
        time_period: Time period for the statistics (day, week, month, etc.)
        prompt_tokens: Total number of prompt tokens used
        completion_tokens: Total number of completion tokens used
        total_tokens: Total number of tokens used (prompt + completion)
        request_count: Total number of API requests made
    """
    time_period: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0    
    
class UsageSummary(BaseModel):
    """Summary of usage statistics."""
    total_users: int
    active_users_today: int
    requests_today: int
    tokens_today: int
