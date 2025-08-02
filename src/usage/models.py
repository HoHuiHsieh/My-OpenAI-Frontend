"""
Usage Statistics Models

This module defines Pydantic models for usage statistics data.
"""
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator, computed_field
from enum import Enum


class APIType(str, Enum):
    """Supported API types for usage tracking."""
    CHAT = "chat"
    EMBEDDINGS = "embeddings"
    AUDIO = "audio"


class TimePeriod(str, Enum):
    """Supported time periods for usage statistics."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"


class TokenUsage(BaseModel):
    """Token usage statistics with validation."""
    prompt_tokens: int = Field(
        ge=0, description="Number of tokens in the prompt")
    completion_tokens: Optional[int] = Field(
        None, ge=0, description="Number of tokens in the completion")
    total_tokens: int = Field(ge=0, description="Total number of tokens used")

    @field_validator('total_tokens')
    @classmethod
    def validate_total_tokens(cls, v, info):
        """Ensure total_tokens is consistent with prompt + completion tokens."""
        prompt_tokens = info.data.get('prompt_tokens', 0)
        completion_tokens = info.data.get('completion_tokens', 0) or 0

        # Allow some tolerance for floating point arithmetic
        expected_total = prompt_tokens + completion_tokens
        if abs(v - expected_total) > 1:  # Allow 1 token difference for rounding
            raise ValueError(
                f"total_tokens ({v}) should equal prompt_tokens ({prompt_tokens}) + "
                f"completion_tokens ({completion_tokens}) = {expected_total}"
            )
        return v

    @computed_field
    @property
    def efficiency_ratio(self) -> Optional[float]:
        """Calculate the ratio of completion tokens to prompt tokens."""
        if self.prompt_tokens > 0 and self.completion_tokens is not None:
            return round(self.completion_tokens / self.prompt_tokens, 3)
        return None


class UsageEntry(BaseModel):
    """Individual usage log entry with enhanced validation."""
    id: Optional[int] = Field(
        None, description="Unique identifier for the usage entry")
    timestamp: datetime = Field(
        description="Timestamp when the usage occurred")
    # Keep as string for backward compatibility
    api_type: str = Field(description="Type of API that was used")
    user_id: str = Field(
        min_length=1, description="ID of the user who made the request")
    model: str = Field(
        min_length=1, description="Name of the model that was used")
    request_id: Optional[str] = Field(
        None, description="Unique identifier for the request")
    prompt_tokens: int = Field(
        ge=0, description="Number of tokens in the prompt")
    completion_tokens: Optional[int] = Field(
        None, ge=0, description="Number of tokens in the completion")
    total_tokens: int = Field(ge=0, description="Total number of tokens used")
    input_count: Optional[int] = Field(
        None, ge=0, description="Number of inputs processed (e.g., for embeddings)")
    extra_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata for the request")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        """Ensure timestamp is not in the future."""
        if v > datetime.utcnow():
            raise ValueError("Timestamp cannot be in the future")
        return v

    @field_validator('total_tokens')
    @classmethod
    def validate_total_tokens(cls, v, info):
        """Ensure total_tokens is consistent with prompt + completion tokens."""
        prompt_tokens = info.data.get('prompt_tokens', 0)
        completion_tokens = info.data.get('completion_tokens', 0) or 0

        expected_total = prompt_tokens + completion_tokens
        if abs(v - expected_total) > 1:  # Allow 1 token difference for rounding
            raise ValueError(
                f"total_tokens ({v}) should equal prompt_tokens ({prompt_tokens}) + "
                f"completion_tokens ({completion_tokens}) = {expected_total}"
            )
        return v

    @computed_field
    @property
    def cost_estimate(self) -> Optional[float]:
        """Estimate cost based on token usage (placeholder implementation)."""
        # This would typically use model-specific pricing
        # For now, use a generic rate of $0.001 per 1K tokens
        if self.total_tokens > 0:
            return round(self.total_tokens * 0.001 / 1000, 6)
        return None

    @computed_field
    @property
    def usage_type(self) -> str:
        """Determine usage pattern based on token distribution."""
        if self.completion_tokens is None or self.completion_tokens == 0:
            return "input_only"  # e.g., embeddings
        elif self.prompt_tokens == 0:
            return "generation_only"  # unusual case
        elif self.completion_tokens > self.prompt_tokens * 3:
            return "high_generation"
        elif self.completion_tokens < self.prompt_tokens * 0.5:
            return "low_generation"
        else:
            return "balanced"


class UsageResponse(BaseModel):
    """
    Model for usage statistics response with enhanced metadata.

    Attributes:
        time_period: Time period for the statistics (day, week, month, etc.)
        prompt_tokens: Total number of prompt tokens used
        completion_tokens: Total number of completion tokens used
        total_tokens: Total number of tokens used (prompt + completion)
        request_count: Total number of API requests made
        model: Optional model name if filtered by model
        start_date: Start date of the time period
        end_date: End date of the time period
        user_count: Number of unique users (for admin reports)
    """
    time_period: Optional[str] = Field(
        None, description="Time period identifier (e.g., '2025-01-15')")
    prompt_tokens: int = Field(
        default=0, ge=0, description="Total prompt tokens used")
    completion_tokens: int = Field(
        default=0, ge=0, description="Total completion tokens used")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens used")
    request_count: int = Field(
        default=0, ge=0, description="Total number of requests")
    model: Optional[str] = Field(
        None, description="Model name if filtered by model")
    start_date: Optional[datetime] = Field(
        None, description="Start of the time period")
    end_date: Optional[datetime] = Field(
        None, description="End of the time period")
    user_count: Optional[int] = Field(
        None, ge=0, description="Number of unique users (admin only)")

    @field_validator('total_tokens')
    @classmethod
    def validate_total_tokens(cls, v, info):
        """Ensure total_tokens is consistent with prompt + completion tokens."""
        prompt_tokens = info.data.get('prompt_tokens', 0)
        completion_tokens = info.data.get('completion_tokens', 0)

        expected_total = prompt_tokens + completion_tokens
        if v > 0 and expected_total > 0 and abs(v - expected_total) > 1:
            raise ValueError(
                f"total_tokens ({v}) should equal prompt_tokens ({prompt_tokens}) + "
                f"completion_tokens ({completion_tokens}) = {expected_total}"
            )
        return v

    @computed_field
    @property
    def average_tokens_per_request(self) -> Optional[float]:
        """Calculate average tokens per request."""
        if self.request_count > 0:
            return round(self.total_tokens / self.request_count, 2)
        return None

    @computed_field
    @property
    def completion_ratio(self) -> Optional[float]:
        """Calculate ratio of completion tokens to total tokens."""
        if self.total_tokens > 0:
            return round(self.completion_tokens / self.total_tokens, 3)
        return None

    @computed_field
    @property
    def estimated_cost(self) -> Optional[float]:
        """Estimate total cost for the period (placeholder implementation)."""
        if self.total_tokens > 0:
            return round(self.total_tokens * 0.001 / 1000, 4)
        return None


class UsageSummary(BaseModel):
    """Enhanced summary of usage statistics."""
    total_users: int = Field(
        ge=0, description="Total number of registered users")
    active_users_today: int = Field(
        ge=0, description="Number of users active today")
    requests_today: int = Field(ge=0, description="Total requests made today")
    tokens_today: int = Field(ge=0, description="Total tokens used today")

    @computed_field
    @property
    def user_activity_ratio(self) -> Optional[float]:
        """Calculate percentage of users that were active today."""
        if self.total_users > 0:
            return round(self.active_users_today / self.total_users * 100, 2)
        return None

    @computed_field
    @property
    def avg_tokens_per_request_today(self) -> Optional[float]:
        """Calculate average tokens per request today."""
        if self.requests_today > 0:
            return round(self.tokens_today / self.requests_today, 2)
        return None
