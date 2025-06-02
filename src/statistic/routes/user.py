"""
User usage statistics routes.

This module defines the endpoints for retrieving usage statistics for the current user.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import SecurityScopes
from oauth2 import get_current_active_user, User
from oauth2.scopes import Scopes

from .. import operations as ops
from .. import models

router = APIRouter()


@router.get("/usage/{period}", 
           response_model=models.UserDetailedUsage,
           summary="Get usage statistics for the current user")
async def get_user_usage(
    period: str,
    days: Optional[int] = 7,
    weeks: Optional[int] = 4,
    months: Optional[int] = 6,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get usage statistics for the current authenticated user.
    
    Parameters:
    - **period**: Time period for which to retrieve usage data (day, week, month, all)
    - **days**: Number of days to retrieve daily data for (default: 7)
    - **weeks**: Number of weeks to retrieve weekly data for (default: 4)
    - **months**: Number of months to retrieve monthly data for (default: 6)
    
    Returns detailed usage statistics including:
    - Daily usage data (tokens and request counts)
    - Weekly usage data (tokens and request counts)
    - Monthly usage data (tokens and request counts)
    
    Authentication is required. User must be logged in.
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
        
    # Get usage data for the user
    return ops.get_user_detailed_usage(
        user_id=current_user.id,
        username=current_user.username,
        days=days,
        weeks=weeks,
        months=months
    )
