"""
This module handles database operations for usage statistics.

It provides functions for:
- Establishing database connections
- Building SQL queries for statistics data
- Executing database queries to retrieve usage data
"""

import logging
import psycopg2
import psycopg2.extras
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from config import get_config
from fastapi import HTTPException, status

from .models import TimePeriod, UsageStatistics, StatisticsSummary, RecentActivity

# Create a dedicated logger for database operations
_stats_db_logger = logging.getLogger("statistics.database")


def get_db_connection():
    """Get a database connection using config settings"""
    config = get_config()
    db_config = config.get('database', {})
    
    try:
        connection = psycopg2.connect(
            dbname=db_config.get('name'),
            user=db_config.get('username'),
            password=db_config.get('password'),
            host=db_config.get('host'),
            port=db_config.get('port'),
            sslmode=db_config.get('ssl_mode', 'prefer')
        )
        return connection
    except Exception as e:
        _stats_db_logger.error(f"Failed to connect to database: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )


def get_table_name():
    """Get the usage table name from config"""
    config = get_config()
    logging_config = config.get('logging', {})
    table_prefix = logging_config.get('table_prefix', 'myopenaiapi')
    return f"{table_prefix}_usage"


def build_time_filter_query(period: TimePeriod, num_periods: int = 30) -> Tuple[str, str, str]:
    """
    Build time filter SQL based on time period
    
    Args:
        period: The time period type (day, week, month)
        num_periods: Number of periods to include (default 30)
    
    Returns:
        tuple: (SQL date_trunc string, interval string, SQL for grouping)
    """
    if period == TimePeriod.DAY:
        return ("day", f"{num_periods} days", "date_trunc('day', timestamp)")
    elif period == TimePeriod.WEEK:
        return ("week", f"{num_periods} weeks", "date_trunc('week', timestamp)")
    elif period == TimePeriod.MONTH:
        return ("month", f"{num_periods} months", "date_trunc('month', timestamp)")
    else:
        raise ValueError(f"Unsupported time period: {period}")


async def get_user_statistics_by_id(
    user_id: str, 
    period: TimePeriod,
    num_periods: int = 30,
    api_type: Optional[str] = None,
    model: Optional[str] = None
) -> List[UsageStatistics]:
    """
    Get usage statistics for a specific user by user ID
    
    Args:
        user_id: The user ID to get statistics for
        period: The time period to group by
        num_periods: Number of periods to include
        api_type: Optional filter by API type (e.g., 'chat', 'embeddings')
        model: Optional filter by model name
        
    Returns:
        List of usage statistics by period
    """
    connection = None
    try:
        connection = get_db_connection()
        table_name = get_table_name()
        period_type, interval, group_by = build_time_filter_query(period, num_periods)

        # Build WHERE clause with parameters
        where_clause = "user_id = %s AND timestamp >= NOW() - interval %s"
        params = [user_id, interval]
        
        if api_type:
            where_clause += " AND api_type = %s"
            params.append(api_type)
        
        if model:
            where_clause += " AND model = %s"
            params.append(model)

        # Base query for statistics by period
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(f"""
                SELECT
                    {group_by} AS period_start,
                    ({group_by} + interval '1 {period_type}')::timestamp AS period_end,
                    SUM(prompt_tokens) AS prompt_tokens,
                    SUM(completion_tokens) AS completion_tokens,
                    SUM(total_tokens) AS total_tokens,
                    COUNT(*) AS request_count,
                    json_object_agg(COALESCE(model, 'unknown'), total_tokens) 
                        FILTER (WHERE model IS NOT NULL) AS models,
                    json_object_agg(COALESCE(api_type, 'unknown'), total_tokens) 
                        FILTER (WHERE api_type IS NOT NULL) AS api_types
                FROM {table_name}
                WHERE {where_clause}
                GROUP BY period_start
                ORDER BY period_start DESC
            """, params)
            
            results = []
            for row in cursor.fetchall():
                stat = UsageStatistics(
                    period_start=row['period_start'].isoformat(),
                    period_end=row['period_end'].isoformat(),
                    prompt_tokens=row['prompt_tokens'] or 0,
                    completion_tokens=row['completion_tokens'] or 0,
                    total_tokens=row['total_tokens'] or 0,
                    request_count=row['request_count'] or 0,
                    models=row['models'] or {},
                    api_types=row['api_types'] or {}
                )
                results.append(stat)
                
            return results
    except Exception as e:
        _stats_db_logger.error(f"Error fetching user statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage statistics: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


async def get_user_statistics_by_username(
    username: str, 
    period: TimePeriod,
    num_periods: int = 30,
    api_type: Optional[str] = None,
    model: Optional[str] = None
) -> List[UsageStatistics]:
    """
    Get usage statistics for a specific user by username
    
    Args:
        username: The username to get statistics for (matches user_id in most cases)
        period: The time period to group by
        num_periods: Number of periods to include
        api_type: Optional filter by API type (e.g., 'chat', 'embeddings')
        model: Optional filter by model name
        
    Returns:
        List of usage statistics by period
    """
    # Currently the user_id in usage table is the username, so we can use the same function
    return await get_user_statistics_by_id(username, period, num_periods, api_type, model)


async def get_all_users_statistics(
    period: TimePeriod,
    num_periods: int = 30,
    user_id: Optional[str] = None,  # Optional filter by specific user ID
    username: Optional[str] = None,  # Optional filter by username
    api_type: Optional[str] = None,  # Optional filter by API type
    model: Optional[str] = None  # Optional filter by model
) -> Dict:
    """
    Get usage statistics for all users (admin only)
    
    Args:
        period: The time period to group by
        num_periods: Number of periods to include
        user_id: Optional user ID filter
        username: Optional username filter (takes precedence over user_id if both provided)
        api_type: Optional filter by API type (e.g., 'chat', 'embeddings')
        model: Optional filter by model name
    
    Returns:
        Usage statistics for all users
    """
    connection = None
    try:
        connection = get_db_connection()
        table_name = get_table_name()
        period_type, interval, group_by = build_time_filter_query(period, num_periods)
        
        # Build WHERE clause
        where_clause = "timestamp >= NOW() - interval %s"
        params = [interval]
        
        # Username takes precedence if both are provided
        if username:
            where_clause += " AND user_id = %s"  # user_id column in database contains username
            params.append(username)
        elif user_id:
            where_clause += " AND user_id = %s"
            params.append(user_id)
            
        # Add filters for API type and model if provided
        if api_type:
            where_clause += " AND api_type = %s"
            params.append(api_type)
            
        if model:
            where_clause += " AND model = %s"
            params.append(model)
        
        # First get a list of all users with their data
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Query to get distinct users first
            cursor.execute(f"""
                SELECT DISTINCT user_id 
                FROM {table_name}
                WHERE {where_clause}
                ORDER BY user_id
            """, params)
            
            users = [row['user_id'] for row in cursor.fetchall()]
            
            # Build complete result
            all_users_stats = []
            total_prompt = 0
            total_completion = 0
            total_tokens = 0
            total_requests = 0
            
            # Get stats for each user
            for user in users:
                user_stats = await get_user_statistics_by_id(user, period, num_periods, api_type, model)
                
                # Calculate user totals
                user_prompt = sum(stat.prompt_tokens for stat in user_stats)
                user_completion = sum(stat.completion_tokens or 0 for stat in user_stats)
                user_total = sum(stat.total_tokens for stat in user_stats)
                user_requests = sum(stat.request_count for stat in user_stats)
                
                # Add to global totals
                total_prompt += user_prompt
                total_completion += user_completion
                total_tokens += user_total
                total_requests += user_requests
                
                all_users_stats.append({
                    "user_id": user,
                    "statistics": user_stats
                })
            
            return {
                "users": all_users_stats,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "total_tokens": total_tokens,
                "total_request_count": total_requests
            }
            
    except Exception as e:
        _stats_db_logger.error(f"Error fetching all users statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve all users statistics: {str(e)}"
        )
    finally:
        if connection:
            connection.close()


async def get_statistics_summary() -> StatisticsSummary:
    """
    Get summary statistics for the admin dashboard.
    
    Returns:
        StatisticsSummary: Summary of usage statistics
    """
    connection = None
    try:
        connection = get_db_connection()
        table_name = get_table_name()
        # Load users table name from config or use default
        config = get_config()
        db_config = config.get('database', {})
        table_prefix = db_config.get('table_prefix', 'myopenaiapi')
        users_table = f"{table_prefix}_users"
        
        # Get today's date range
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        # Initialize default values
        total_users = 0
        active_users = 0
        api_requests = 0
        total_tokens = 0
        
        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get total users count - handle case where table might not exist
            try:
                cursor.execute(f"SELECT COUNT(*) AS total_users FROM {users_table}")
                total_users = cursor.fetchone()['total_users'] or 0
            except Exception as e:
                _stats_db_logger.warning(f"Failed to get user count: {str(e)}")
                # Default fallback value
                total_users = 0
            
            # Get active users today
            try:
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT user_id) AS active_users
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                """, (today_start, today_end))
                active_users = cursor.fetchone()['active_users'] or 0
            except Exception as e:
                _stats_db_logger.warning(f"Failed to get active users: {str(e)}")
                active_users = 0
            
            # Get API requests today
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) AS request_count
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                """, (today_start, today_end))
                api_requests = cursor.fetchone()['request_count'] or 0
            except Exception as e:
                _stats_db_logger.warning(f"Failed to get API request count: {str(e)}")
                api_requests = 0
            
            # Get total tokens today
            try:
                cursor.execute(f"""
                    SELECT SUM(total_tokens) AS total_tokens
                    FROM {table_name}
                    WHERE timestamp BETWEEN %s AND %s
                """, (today_start, today_end))
                total_tokens = cursor.fetchone()['total_tokens'] or 0
            except Exception as e:
                _stats_db_logger.warning(f"Failed to get total tokens: {str(e)}")
                total_tokens = 0
            
        _stats_db_logger.info(f"Retrieved statistics summary: users={total_users}, active={active_users}, requests={api_requests}, tokens={total_tokens}")
        return StatisticsSummary(
            total_users=total_users,
            active_users_today=active_users,
            api_requests_today=api_requests,
            total_tokens_today=total_tokens
        )
            
    except Exception as e:
        _stats_db_logger.error(f"Error fetching statistics summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics summary: {str(e)}"
        )
    finally:
        if connection:
            connection.close()
