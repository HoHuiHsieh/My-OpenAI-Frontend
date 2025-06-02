"""
Business logic for aggregating and formatting statistics.

This module provides functions for transforming raw database data
into structured usage statistics.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union

from . import db
from . import models


def get_user_daily_usage(user_id: Union[str, int], days: int = 7) -> List[models.DailyUsage]:
    """
    Get daily usage statistics for a specific user.
    
    Args:
        user_id: The user ID to get statistics for (will be converted to string)
        days: Number of days to retrieve data for
        
    Returns:
        List of daily usage data
    """
    # Get raw data from database
    raw_data = db.get_daily_usage(user_id=str(user_id), days=days)
    
    # Convert to model objects
    result = []
    for item in raw_data:
        result.append(models.DailyUsage(
            date=item["date"],
            total_tokens=item["total_tokens"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            request_count=item["request_count"]
        ))
    
    # Fill in missing days with zero values
    if result:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        # Create a map of existing dates
        date_map = {item.date: item for item in result}
        
        # Fill in missing dates
        current_date = start_date
        complete_result = []
        while current_date <= end_date:
            if current_date in date_map:
                complete_result.append(date_map[current_date])
            else:
                complete_result.append(models.DailyUsage(date=current_date))
            current_date += timedelta(days=1)
            
        return complete_result
    
    return result


def get_user_weekly_usage(user_id: Union[str, int], weeks: int = 4) -> List[models.WeeklyUsage]:
    """
    Get weekly usage statistics for a specific user.
    
    Args:
        user_id: The user ID to get statistics for (will be converted to string)
        weeks: Number of weeks to retrieve data for
        
    Returns:
        List of weekly usage data
    """
    # Get raw data from database
    raw_data = db.get_weekly_usage(user_id=str(user_id), weeks=weeks)
    
    # Convert to model objects
    result = []
    for item in raw_data:
        result.append(models.WeeklyUsage(
            week_start=item["week_start"].date(),
            week_end=item["week_end"].date(),
            total_tokens=item["total_tokens"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            request_count=item["request_count"]
        ))
    
    return result


def get_user_monthly_usage(user_id: Union[str, int], months: int = 6) -> List[models.MonthlyUsage]:
    """
    Get monthly usage statistics for a specific user.
    
    Args:
        user_id: The user ID to get statistics for (will be converted to string)
        months: Number of months to retrieve data for
        
    Returns:
        List of monthly usage data
    """
    # Get raw data from database
    raw_data = db.get_monthly_usage(user_id=str(user_id), months=months)
    
    # Convert to model objects
    result = []
    for item in raw_data:
        result.append(models.MonthlyUsage(
            year=int(item["year"]),
            month=int(item["month"]),
            total_tokens=item["total_tokens"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            request_count=item["request_count"]
        ))
    
    return result


def get_user_detailed_usage(user_id: Union[str, int], username: str, days: int = 7, weeks: int = 4, months: int = 6) -> models.UserDetailedUsage:
    """
    Get detailed usage statistics for a specific user across different time periods.
    
    Args:
        user_id: The user ID to get statistics for (will be converted to string)
        username: The username for the user
        days: Number of days to retrieve daily data for
        weeks: Number of weeks to retrieve weekly data for
        months: Number of months to retrieve monthly data for
        
    Returns:
        UserDetailedUsage object with usage data
    """
    daily = get_user_daily_usage(user_id, days)
    weekly = get_user_weekly_usage(user_id, weeks)
    monthly = get_user_monthly_usage(user_id, months)
    
    return models.UserDetailedUsage(
        username=username,
        daily_usage=daily,
        weekly_usage=weekly,
        monthly_usage=monthly
    )


def get_all_users_usage(days: int = 7, weeks: int = 4, months: int = 6) -> models.AllUsersUsage:
    """
    Get usage statistics for all users.
    
    Args:
        days: Number of days to retrieve daily data for
        weeks: Number of weeks to retrieve weekly data for
        months: Number of months to retrieve monthly data for
        
    Returns:
        AllUsersUsage object with combined usage data
    """
    # Get raw data from database
    daily_data = db.get_daily_usage(days=days)
    weekly_data = db.get_weekly_usage(weeks=weeks)
    monthly_data = db.get_monthly_usage(months=months)
    
    # Convert to model objects
    daily_result = []
    for item in daily_data:
        daily_result.append(models.DailyUsage(
            date=item["date"],
            total_tokens=item["total_tokens"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            request_count=item["request_count"]
        ))
    
    weekly_result = []
    for item in weekly_data:
        weekly_result.append(models.WeeklyUsage(
            week_start=item["week_start"].date(),
            week_end=item["week_end"].date(),
            total_tokens=item["total_tokens"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            request_count=item["request_count"]
        ))
    
    monthly_result = []
    for item in monthly_data:
        monthly_result.append(models.MonthlyUsage(
            year=int(item["year"]),
            month=int(item["month"]),
            total_tokens=item["total_tokens"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            request_count=item["request_count"]
        ))
    
    return models.AllUsersUsage(
        daily_usage=daily_result,
        weekly_usage=weekly_result,
        monthly_usage=monthly_result
    )


def get_usage_summary() -> models.UsageSummary:
    """
    Get overall usage summary statistics.
    
    Returns:
        UsageSummary object with summary statistics
    """
    data = db.get_usage_summary()
    
    return models.UsageSummary(
        total_users=data["total_users"],
        active_users_today=data["active_users_today"],
        requests_today=data["requests_today"],
        tokens_today=data["tokens_today"]
    )


def get_user_request_list(user_id: Union[str, int], period: str, limit: int = 100) -> List[models.UsageEntry]:
    """
    Get a list of API requests made by a user.
    
    Args:
        user_id: User ID to filter by (will be converted to string)
        period: Time period to filter by (day, week, month)
        limit: Maximum number of records to return
        
    Returns:
        List of UsageEntry objects
    """
    raw_data = db.get_user_request_list(str(user_id), period, limit)
    
    result = []
    for item in raw_data:
        result.append(models.UsageEntry(
            id=item["id"],
            timestamp=item["timestamp"],
            api_type=item["api_type"],
            user_id=item["user_id"],
            model=item["model"],
            request_id=item["request_id"],
            prompt_tokens=item["prompt_tokens"],
            completion_tokens=item["completion_tokens"],
            total_tokens=item["total_tokens"],
            input_count=item["input_count"],
            extra_data=item["extra_data"]
        ))
    
    return result
