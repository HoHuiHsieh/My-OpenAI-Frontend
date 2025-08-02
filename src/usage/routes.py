"""
Usage statistics routes.

This module defines the endpoints for retrieving usage statistics.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Security, status
from sqlalchemy.orm import Session
from oauth2 import get_current_active_user, User
from oauth2.routes.middleware import get_db as get_user_db
from oauth2.user_management import UserManager
from .manager import UsageManager
from .models import UsageResponse, UsageSummary, UsageEntry
from .dependencies import get_usage_manager

# Create routers
user_router = APIRouter(tags=["usage"])
admin_router = APIRouter(prefix="/admin", tags=["admin usage"])


def get_user_manager() -> UserManager:
    """Dependency injection for UserManager."""
    return UserManager()


# User routes
@user_router.get("/usage/models", response_model=List[str])
def get_model_list(
    current_user: User = Depends(get_current_active_user),
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    """
    Get a list of available models for usage statistics.

    Returns a list of model names.
    """
    return usage_manager.get_model_list()


@user_router.get("/usage/{time}",
                 response_model=List[UsageResponse],
                 summary="Get usage statistics for the current user")
async def get_user_usage(
    time: Optional[str] = "all",
    period: Optional[int] = 7,
    model: Optional[str] = "all",
    current_user: User = Depends(get_current_active_user),
    user_db: Session = Depends(get_user_db),
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    """
    Get usage statistics for the current authenticated user.

    Parameters:
    - **time**: Time period for which to retrieve usage data (day, week, month, all)
    - **period**: Number of periods to retrieve data for (default: 7)
    - **model**: Specific model to filter by (default: "all")

    Returns detailed usage statistics including:
    - Token usage data (prompt, completion, total tokens)
    - Request counts
    - Time-based aggregations

    Authentication is required. User must be logged in.
    """
    # Validate period
    valid_periods = ["day", "week", "month", "all"]
    if time not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time. Must be one of {', '.join(valid_periods)}"
        )

    # Get user id
    user_id = current_user.id if hasattr(
        current_user, 'id') and current_user.id else None
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated"
        )

    # Get usage data for current user
    return usage_manager.get_usage_data(
        user_id=user_id,
        time=time,
        period=period,
        model=model,
    )


# Admin routes
@admin_router.get("/usage/user/{username}/{time}",
                  response_model=List[UsageResponse],
                  summary="Get usage statistics for a specific user")
async def get_user_usage_admin(
    username: str,
    time: Optional[str] = "all",
    period: Optional[int] = 7,
    model: Optional[str] = "all",
    current_user: User = Security(get_current_active_user, scopes=["admin"]),
    user_db: Session = Depends(get_user_db),
    user_manager: UserManager = Depends(get_user_manager),
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    """
    Get usage statistics for a specific user.

    Parameters:
    - **username**: Username of the user to get statistics for
    - **time**: Time period to filter by (day, week, month, all)
    - **period**: Number of periods to retrieve data for (default: 7)
    - **model**: Specific model to filter by (default: "all")

    Returns detailed usage statistics for the specified user.

    Admin access required.
    """
    # Validate period
    valid_periods = ["day", "week", "month", "all"]
    if time not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time. Must be one of {', '.join(valid_periods)}"
        )

    # Get user by username
    user = user_manager.get_user(db=user_db, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )

    # Get usage data for specified user
    return usage_manager.get_usage_data(
        user_id=user.id if user else None,
        time=time,
        period=period,
        model=model,
    )


@admin_router.get("/usage/all/{time}",
                  response_model=List[UsageResponse],
                  summary="Get usage statistics for all users")
async def get_all_users_usage(
    time: Optional[str] = "all",
    period: Optional[int] = 7,
    model: Optional[str] = "all",
    current_user: User = Security(get_current_active_user, scopes=["admin"]),
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    """
    Get usage statistics for all users.

    Arguments:
    - **time**: Time period to filter by (day, week, month, all)
    - **period**: Number of periods to retrieve data for (default: 7)
    - **model**: Specific model to filter by (default: "all")

    Return:
    - List of usage statistics for all users, aggregated by the specified time period.
    """
    # Validate period
    valid_periods = ["day", "week", "month", "all"]
    if time not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time. Must be one of {', '.join(valid_periods)}"
        )

    # Get usage data for all users
    return usage_manager.get_usage_data(
        time=time,
        period=period,
        model=model,
    )


@admin_router.get("/usage/summary",
                  response_model=UsageSummary,
                  summary="Get summary statistics")
async def get_usage_summary(
    current_user: User = Security(get_current_active_user, scopes=["admin"]),
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    """
    Get summary statistics including:
    - Total number of users
    - Number of active users today
    - Number of API requests today
    - Total tokens used today

    Admin access required.
    """
    return usage_manager.get_usage_summary()


@admin_router.get("/usage/list/user/{username}/{period}",
                  response_model=List[UsageEntry],
                  summary="Get API requests list for a specific user")
async def get_user_request_list(
    username: str,
    period: str,
    limit: Optional[int] = 100,
    current_user: User = Security(get_current_active_user, scopes=["admin"]),
    user_db: Session = Depends(get_user_db),
    user_manager: UserManager = Depends(get_user_manager),
    usage_manager: UsageManager = Depends(get_usage_manager)
):
    """
    Get a list of API requests made by a specific user.

    Parameters:
    - **username**: Username of the user to get request list for
    - **period**: Time period to filter by (day, week, month)
    - **limit**: Maximum number of records to return (default: 100)

    Returns a list of individual API request records for the specified user.

    Admin access required.
    """
    # Get user by username
    user = user_manager.get_user(db=user_db, username=username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )

    # Get request list for the user
    return usage_manager.get_user_request_list(
        user_id=user.id,
        period=period,
        limit=limit
    )
