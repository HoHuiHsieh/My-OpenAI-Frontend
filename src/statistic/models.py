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


class DailyUsage(BaseModel):
    """Daily usage statistics."""
    date: date
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0


class WeeklyUsage(BaseModel):
    """Weekly usage statistics."""
    week_start: date
    week_end: date
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0


class MonthlyUsage(BaseModel):
    """Monthly usage statistics."""
    month: int  # 1-12
    year: int
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0


class UsageSummary(BaseModel):
    """Summary of usage statistics."""
    total_users: int
    active_users_today: int
    requests_today: int
    tokens_today: int


class UserDetailedUsage(BaseModel):
    """Detailed usage for a specific user."""
    username: str
    daily_usage: List[DailyUsage] = []
    weekly_usage: List[WeeklyUsage] = []
    monthly_usage: List[MonthlyUsage] = []


class AllUsersUsage(BaseModel):
    """Combined usage statistics for all users."""
    daily_usage: List[DailyUsage] = []
    weekly_usage: List[WeeklyUsage] = []
    monthly_usage: List[MonthlyUsage] = []
    by_user: Dict[str, UserDetailedUsage] = {}
