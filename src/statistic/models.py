"""
This module defines the data models for usage statistics.

It contains Pydantic models for:
- Response formats for usage statistics endpoints
- Enums for time periods and data types
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class TimePeriod(str, Enum):
    """Enum for time periods to group statistics by"""
    DAY = "day"
    WEEK = "week" 
    MONTH = "month"


class UsageStatistics(BaseModel):
    """Model for usage statistics data"""
    period_start: str
    period_end: str
    prompt_tokens: int
    completion_tokens: Optional[int]
    total_tokens: int
    request_count: int
    models: Dict[str, int] = {}  # Model name -> token count
    api_types: Dict[str, int] = {}  # API type -> token count


class UserStatistics(BaseModel):
    """Model for user-specific usage statistics"""
    user_id: str
    statistics: List[UsageStatistics]


class AllUsersStatistics(BaseModel):
    """Model for all users' usage statistics (admin only)"""
    users: List[UserStatistics]
    total_prompt_tokens: int
    total_completion_tokens: Optional[int]
    total_tokens: int
    total_request_count: int


class StatisticsSummary(BaseModel):
    """Model for dashboard statistics summary (admin only)"""
    total_users: int
    active_users_today: int
    api_requests_today: int
    total_tokens_today: int


class RecentActivity(BaseModel):
    """Model for recent user activity"""
    timestamp: str
    username: str
    action: str
    details: str
