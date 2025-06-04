"""
User usage statistics routes.

This module defines the endpoints for retrieving usage statistics for the current user.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from oauth2 import get_current_active_user, User
from .. import operations as ops
from .. import models

router = APIRouter()


@router.get("/usage/{time}", 
           response_model=List[models.UsageResponse],
           summary="Get usage statistics for the current user")
async def get_user_usage(
    time: Optional[str] = "all",
    period: Optional[int] = 7,
    model: Optional[str] = "all",
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
    if time not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time. Must be one of {', '.join(valid_periods)}"
        )
    
    # Get user by username
    
    # Get usage data for all users
    return ops.get_usage_data(
        user_id=current_user.id if hasattr(current_user, 'id') and current_user.id else None,
        time=time,
        period=period,
        model=model,
    )
