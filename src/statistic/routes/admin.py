"""
Admin usage statistics routes.

This module defines the endpoints for retrieving usage statistics for administrators.
"""

from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import SecurityScopes
from oauth2 import get_current_active_user, User
from oauth2.scopes import Scopes
from oauth2.rbac import verify_scopes

from .. import operations as ops
from .. import models

router = APIRouter(prefix="/admin")


@router.get("/usage/user/{username}/{period}", 
           response_model=models.UserDetailedUsage,
           summary="Get usage statistics for a specific user")
async def get_user_usage(
    username: str,
    period: str,
    days: Optional[int] = 7,
    weeks: Optional[int] = 4,
    months: Optional[int] = 6,
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get usage statistics for a specific user.
    
    Parameters:
    - **username**: Username of the user to get statistics for
    - **period**: Time period for which to retrieve usage data (day, week, month, all)
    - **days**: Number of days to retrieve daily data for (default: 7)
    - **weeks**: Number of weeks to retrieve weekly data for (default: 4)
    - **months**: Number of months to retrieve monthly data for (default: 6)
    
    Returns detailed usage statistics including:
    - Daily usage data (tokens and request counts)
    - Weekly usage data (tokens and request counts)
    - Monthly usage data (tokens and request counts)
    
    Admin access required.
    """
    # Validate period
    valid_periods = ["day", "week", "month", "all"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of {', '.join(valid_periods)}"
        )
    
    # Adjust parameters based on the requested period
    if period == "day":
        weeks = 0
        months = 0
    elif period == "week":
        days = 0
        months = 0
    elif period == "month":
        days = 0
        weeks = 0
        
    # Get usage data for the specified user
    # Get the database session and retrieve user information
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
        
    return ops.get_user_detailed_usage(
        user_id=user.id,
        username=user.username,
        days=days,
        weeks=weeks,
        months=months
    )


@router.get("/usage/all/{period}", 
           response_model=models.AllUsersUsage,
           summary="Get usage statistics for all users")
async def get_all_users_usage(
    period: str,
    days: Optional[int] = 7,
    weeks: Optional[int] = 4,
    months: Optional[int] = 6,
    current_user: User = Security(
        get_current_active_user, scopes=["admin"])
):
    """
    Get usage statistics for all users.
    
    Parameters:
    - **period**: Time period for which to retrieve usage data (day, week, month, all)
    - **days**: Number of days to retrieve daily data for (default: 7)
    - **weeks**: Number of weeks to retrieve weekly data for (default: 4)
    - **months**: Number of months to retrieve monthly data for (default: 6)
    
    Returns combined usage statistics for all users including:
    - Daily usage data (tokens and request counts)
    - Weekly usage data (tokens and request counts)
    - Monthly usage data (tokens and request counts)
    
    Admin access required.
    """
    # Validate period
    valid_periods = ["day", "week", "month", "all"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of {', '.join(valid_periods)}"
        )
    
    # Adjust parameters based on the requested period
    if period == "day":
        weeks = 0
        months = 0
    elif period == "week":
        days = 0
        months = 0
    elif period == "month":
        days = 0
        weeks = 0
        
    # Get usage data for all users
    return ops.get_all_users_usage(
        days=days,
        weeks=weeks,
        months=months
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
