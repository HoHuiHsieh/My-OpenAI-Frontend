"""
This module defines the API router and endpoints for usage statistics.

It provides routes for:
- User-specific usage statistics
- Admin endpoints for all users and specific user statistics
- Admin dashboard summary statistics
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Security
from oauth2 import get_current_active_user, User

from .models import (TimePeriod, UsageStatistics,
                     AllUsersStatistics, UserStatistics, StatisticsSummary,
                     RecentActivity)
from .database import (
    get_user_statistics_by_id,
    get_user_statistics_by_username,
    get_all_users_statistics,
    get_statistics_summary
)
from .activity import get_recent_activity

# Create a dedicated logger for router
_stats_router_logger = logging.getLogger("statistics.router")

# Create routers
router = APIRouter(prefix="/usage", tags=["usage"])


# API Routes for user statistics
@router.get("/me/{period}", response_model=List[UsageStatistics])
async def get_my_usage(
    period: TimePeriod,
    num_periods: Optional[int] = 30,
    api_type: Optional[str] = None,
    model: Optional[str] = None,
    current_user: User = Security(get_current_active_user)
):
    """
    Get usage statistics for the current user by time period.

    Args:
        period: The time period to group by (day, week, month)
        num_periods: Number of periods to include (default 30)
        api_type: Optional filter by API type (e.g., 'chat', 'embeddings')
        model: Optional filter by model name

    Returns:
        Usage statistics for the current user
    """
    return await get_user_statistics_by_username(current_user.full_name, period, num_periods, api_type, model)


@router.get("/admin/user/{username}/{period}", response_model=List[UsageStatistics])
async def get_user_usage_by_username(
    username: str,
    period: TimePeriod,
    num_periods: Optional[int] = 30,
    api_type: Optional[str] = None,
    model: Optional[str] = None,
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get usage statistics for a specific user by username (admin only).

    Args:
        username: The username to get statistics for
        period: The time period to group by (day, week, month)
        num_periods: Number of periods to include (default 30)
        api_type: Optional filter by API type (e.g., 'chat', 'embeddings')
        model: Optional filter by model name

    Returns:
        Usage statistics for the specified username
    """
    return await get_user_statistics_by_username(username, period, num_periods, api_type, model)


@router.get("/admin/all/{period}", response_model=AllUsersStatistics)
async def get_all_users_usage(
    period: TimePeriod,
    num_periods: Optional[int] = 30,
    username: Optional[str] = None,
    api_type: Optional[str] = None,
    model: Optional[str] = None,
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get usage statistics for all users or a specific user (admin only).

    Args:
        period: The time period to group by (day, week, month)
        num_periods: Number of periods to include (default 30)
        username: Optional specific username to filter by
        api_type: Optional filter by API type (e.g., 'chat', 'embeddings')
        model: Optional filter by model name

    Returns:
        Aggregated usage statistics for all users
    """
    result = await get_all_users_statistics(
        period,
        num_periods,
        user_id=None,
        username=username,
        api_type=api_type,
        model=model
    )

    # Convert the dictionary to a Pydantic model
    return AllUsersStatistics(
        users=[UserStatistics(**user) for user in result["users"]],
        total_prompt_tokens=result["total_prompt_tokens"],
        total_completion_tokens=result["total_completion_tokens"],
        total_tokens=result["total_tokens"],
        total_request_count=result["total_request_count"]
    )


# Admin statistics summary endpoint
@router.get("/admin/summary", response_model=StatisticsSummary)
async def get_admin_statistics_summary(
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get summary statistics for the admin dashboard.

    Returns:
        Summary statistics including total users, active users today,
        API requests today, and total tokens used today.
    """
    _stats_router_logger.debug("Retrieving admin statistics summary")
    return await get_statistics_summary()


@router.get("/admin/recent", response_model=List[RecentActivity])
async def get_admin_recent_activity(
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get recent activity statistics for the admin dashboard.

    Returns:
        Summary statistics including total users, active users today,
        API requests today, and total tokens used today.
    """
    _stats_router_logger.debug("Retrieving admin statistics summary")
    recent_activities = await get_recent_activity()
    return recent_activities
