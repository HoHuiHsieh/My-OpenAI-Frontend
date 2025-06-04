"""
Business logic for aggregating and formatting statistics.

This module provides functions for transforming raw database data
into structured usage statistics.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Union

from . import db
from . import models


def get_usage_data(
    user_id: Optional[Union[str, int]] = None,
    time: str = 'day',
    period: int = 7,
    model: str = 'all'
) -> List[models.UsageResponse]:
    """
    Get usage statistics with flexible filtering options.
    
    Args:
        user_id: Optional user ID to filter by (will be converted to string)
        time: Time period type ('day', 'week', 'month', 'all')
        period: Number of time periods to retrieve data for
        model: Optional model name to filter by
        
    Returns:
        List of usage data objects (either TimeUsage or ModelUsage)
    """
    # Convert user_id to string if provided
    user_id_str = None
    if user_id is not None:
        user_id_str = str(user_id)
    
    # Get raw data from database using the unified get_usage function
    return db.get_usage(
        user_id=user_id_str,
        time=time,
        period=period,
        model=model
    )   


# def get_user_daily_usage(user_id: Union[str, int], days: int = 7) -> List[models.DailyUsage]:
#     """
#     Get daily usage statistics for a specific user.
    
#     Args:
#         user_id: The user ID to get statistics for (will be converted to string)
#         days: Number of days to retrieve data for
        
#     Returns:
#         List of daily usage data
#     """
#     # Use the new unified get_usage function with time_period='day'
#     raw_data = get_usage_data(
#         user_id=user_id,
#         time_period='day',
#         period=days
#     )
    
#     # Convert to DailyUsage model objects
#     result = []
#     for item in raw_data:
#         # Try to parse the time_period string as a date
#         try:
#             usage_date = datetime.strptime(item.time_period, '%Y-%m-%d').date()
#             result.append(models.DailyUsage(
#                 date=usage_date,
#                 total_tokens=item.total_tokens,
#                 prompt_tokens=item.prompt_tokens,
#                 completion_tokens=item.completion_tokens,
#                 request_count=item.request_count
#             ))
#         except ValueError:
#             # Skip items where time_period is not in expected format
#             continue
    
#     # Fill in missing days with zero values
#     if result:
#         end_date = datetime.now().date()
#         start_date = end_date - timedelta(days=days-1)
        
#         # Create a map of existing dates
#         date_map = {item.date: item for item in result}
        
#         # Fill in missing dates
#         current_date = start_date
#         complete_result = []
#         while current_date <= end_date:
#             if current_date in date_map:
#                 complete_result.append(date_map[current_date])
#             else:
#                 complete_result.append(models.DailyUsage(date=current_date))
#             current_date += timedelta(days=1)
        
#         return complete_result
    
#     return result


# def get_user_weekly_usage(user_id: Union[str, int], weeks: int = 4) -> List[models.WeeklyUsage]:
#     """
#     Get weekly usage statistics for a specific user.
    
#     Args:
#         user_id: The user ID to get statistics for (will be converted to string)
#         weeks: Number of weeks to retrieve data for
        
#     Returns:
#         List of weekly usage data
#     """
#     # Use the new unified get_usage function with time_period='week'
#     raw_data = get_usage_data(
#         user_id=user_id,
#         time_period='week',
#         period=weeks
#     )
    
#     # Convert to WeeklyUsage model objects
#     result = []
#     for item in raw_data:
#         # Parse the time_period string which is in format 'YYYY-MM-DD to YYYY-MM-DD'
#         try:
#             dates = item.time_period.split(' to ')
#             if len(dates) == 2:
#                 week_start = datetime.strptime(dates[0], '%Y-%m-%d').date()
#                 week_end = datetime.strptime(dates[1], '%Y-%m-%d').date()
                
#                 result.append(models.WeeklyUsage(
#                     week_start=week_start,
#                     week_end=week_end,
#                     total_tokens=item.total_tokens,
#                     prompt_tokens=item.prompt_tokens,
#                     completion_tokens=item.completion_tokens,
#                     request_count=item.request_count
#                 ))
#         except (ValueError, IndexError):
#             # Skip items where time_period is not in expected format
#             continue
    
#     return result


# def get_user_monthly_usage(user_id: Union[str, int], months: int = 6) -> List[models.MonthlyUsage]:
#     """
#     Get monthly usage statistics for a specific user.
    
#     Args:
#         user_id: The user ID to get statistics for (will be converted to string)
#         months: Number of months to retrieve data for
        
#     Returns:
#         List of monthly usage data
#     """
#     # Use the new unified get_usage function with time_period='month'
#     raw_data = get_usage_data(
#         user_id=user_id,
#         time_period='month',
#         period=months
#     )
    
#     # Convert to MonthlyUsage model objects
#     result = []
#     for item in raw_data:
#         # Parse the time_period string which is in format 'YYYY-MM'
#         try:
#             year_month = item.time_period.split('-')
#             if len(year_month) == 2:
#                 year = int(year_month[0])
#                 month = int(year_month[1])
                
#                 result.append(models.MonthlyUsage(
#                     year=year,
#                     month=month,
#                     total_tokens=item.total_tokens,
#                     prompt_tokens=item.prompt_tokens,
#                     completion_tokens=item.completion_tokens,
#                     request_count=item.request_count
#                 ))
#         except (ValueError, IndexError):
#             # Skip items where time_period is not in expected format
#             continue
    
#     return result


# def get_user_detailed_usage(
#     user_id: Union[str, int],
#     username: str,
#     days: int = 7,
#     weeks: int = 4,
#     months: int = 6
# ) -> models.UserDetailedUsage:
#     """
#     Get detailed usage statistics for a specific user.
    
#     Args:
#         user_id: The user ID to get statistics for (will be converted to string)
#         username: Username for the user
#         days: Number of days to retrieve daily data for
#         weeks: Number of weeks to retrieve weekly data for
#         months: Number of months to retrieve monthly data for
        
#     Returns:
#         UserDetailedUsage object with combined usage data
#     """
#     # Get data using our helper functions which now use the unified get_usage
#     daily_data = get_user_daily_usage(user_id=user_id, days=days)
#     weekly_data = get_user_weekly_usage(user_id=user_id, weeks=weeks)
#     monthly_data = get_user_monthly_usage(user_id=user_id, months=months)
    
#     return models.UserDetailedUsage(
#         username=username,
#         daily_usage=daily_data,
#         weekly_usage=weekly_data,
#         monthly_usage=monthly_data
#     )


# def get_all_users_usage(
#     days: int = 7,
#     weeks: int = 4,
#     months: int = 6
# ) -> models.AllUsersUsage:
#     """
#     Get combined usage statistics for all users.
    
#     Args:
#         days: Number of days to retrieve daily data for
#         weeks: Number of weeks to retrieve weekly data for
#         months: Number of months to retrieve monthly data for
        
#     Returns:
#         AllUsersUsage object with combined usage data
#     """
#     # Use the unified get_usage function directly for all users
#     daily_raw_data = get_usage_data(time_period='day', period=days)
#     weekly_raw_data = get_usage_data(time_period='week', period=weeks)
#     monthly_raw_data = get_usage_data(time_period='month', period=months)
    
#     # Convert to appropriate model objects
#     daily_result = []
#     for item in daily_raw_data:
#         try:
#             usage_date = datetime.strptime(item.time_period, '%Y-%m-%d').date()
#             daily_result.append(models.DailyUsage(
#                 date=usage_date,
#                 total_tokens=item.total_tokens,
#                 prompt_tokens=item.prompt_tokens,
#                 completion_tokens=item.completion_tokens,
#                 request_count=item.request_count
#             ))
#         except (ValueError, AttributeError):
#             continue
    
#     weekly_result = []
#     for item in weekly_raw_data:
#         try:
#             dates = item.time_period.split(' to ')
#             if len(dates) == 2:
#                 week_start = datetime.strptime(dates[0], '%Y-%m-%d').date()
#                 week_end = datetime.strptime(dates[1], '%Y-%m-%d').date()
                
#                 weekly_result.append(models.WeeklyUsage(
#                     week_start=week_start,
#                     week_end=week_end,
#                     total_tokens=item.total_tokens,
#                     prompt_tokens=item.prompt_tokens,
#                     completion_tokens=item.completion_tokens,
#                     request_count=item.request_count
#                 ))
#         except (ValueError, IndexError, AttributeError):
#             continue
    
#     monthly_result = []
#     for item in monthly_raw_data:
#         try:
#             year_month = item.time_period.split('-')
#             if len(year_month) == 2:
#                 year = int(year_month[0])
#                 month = int(year_month[1])
                
#                 monthly_result.append(models.MonthlyUsage(
#                     year=year,
#                     month=month,
#                     total_tokens=item.total_tokens,
#                     prompt_tokens=item.prompt_tokens,
#                     completion_tokens=item.completion_tokens,
#                     request_count=item.request_count
#                 ))
#         except (ValueError, IndexError, AttributeError):
#             continue
    
#     return models.AllUsersUsage(
#         daily_usage=daily_result,
#         weekly_usage=weekly_result,
#         monthly_usage=monthly_result
#     )


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
