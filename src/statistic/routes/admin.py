"""
Admin usage statistics routes.

This module defines the endpoints for retrieving usage statistics for administrators.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Security
from oauth2 import get_current_active_user, User
from oauth2.db import get_db
from oauth2.db.operations import get_user_by_username
from .. import operations as ops
from .. import models

router = APIRouter(prefix="/admin")


@router.get("/usage/user/{username}/{time}", 
           response_model=List[models.UsageResponse],
           summary="Get usage statistics for a specific user")
async def get_user_usage(
    username: str,
    time: Optional[str] = "all",
    period: Optional[int] = 7,
    model: Optional[str] = "all",
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
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
    db_generator = get_db()
    db = next(db_generator)
    user = get_user_by_username(db, username)
    
    # Get usage data for all users
    return ops.get_usage_data(
        user_id=user.id if user else None,
        time=time,
        period=period,
        model=model,
    )


@router.get("/usage/all/{time}", 
           response_model=List[models.UsageResponse],
           summary="Get usage statistics for all users")
async def get_all_users_usage(
    time: Optional[str] = "all",
    period: Optional[int] = 7,
    model: Optional[str] = "all",
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
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
    return ops.get_usage_data(
        time=time,
        period=period,
        model=model,
    )


@router.get("/usage/summary", 
           response_model=models.UsageSummary,
           summary="Get summary statistics")
async def get_usage_summary(
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get summary statistics including:
    - Total number of users
    - Number of active users today
    - Number of API requests today
    - Total tokens used today
    
    Admin access required.
    """
    return ops.get_usage_summary()


@router.get("/usage/list/user/{username}/{period}", 
           response_model=List[models.UsageEntry],
           summary="Get API requests list for a specific user")
async def get_user_request_list(
    username: str,
    period: str,
    limit: Optional[int] = 100,
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get a list of API requests made by a specific user.
    
    Parameters:
    - **username**: Username of the user to get requests for
    - **period**: Time period to filter by (day, week, month)
    - **limit**: Maximum number of records to return (default: 100)
    
    Returns a list of API request records with details about each request.
    
    Admin access required.
    """
    # Validate period
    valid_periods = ["day", "week", "month"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of {', '.join(valid_periods)}"
        )
    
    # Get user by username
    from oauth2.db import get_db
    from oauth2.db.operations import get_user_by_username
    
    # Get database session
    db = next(get_db())
    
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )
        
    # Get request list for the user
    return ops.get_user_request_list(
        user_id=user.id,
        period=period,
        limit=limit
    )
