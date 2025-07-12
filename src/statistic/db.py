# -*- coding: utf-8 -*-
"""
Database access and query functions for statistics.

This module provides database interaction functions specifically for retrieving
and analyzing usage statistics from the logging database.
"""

import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Literal
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from config import get_config
from logger import get_logger
from oauth2.db import get_db
from oauth2.db.operations import get_all_users
from .models import UsageResponse


# Initialize the enhanced logging system
logger = get_logger(__name__)

# Load configuration
config = get_config()
db_config = config.get("database", {})
logging_config = config.get("logging", {})
table_prefix = logging_config.get("table_prefix", "myopenaiapi")
usage_table = f"{table_prefix}_usage"


def get_db_connection():
    """Get a connection to the database."""
    try:
        connection = psycopg2.connect(
            dbname=db_config.get("name"),
            user=db_config.get("username"),
            password=db_config.get("password"),
            host=db_config.get("host"),
            port=db_config.get("port"),
            sslmode=db_config.get("ssl_mode", "prefer"),
        )
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise


def get_user_request_list(user_id: Union[str, int], period: str = "day", limit: int = 100) -> List[Dict]:
    """
    Get a list of API requests made by a user.

    Args:
        user_id: User ID to filter by (will be converted to string)
        period: Time period to filter by (day, week, month)
        limit: Maximum number of records to return

    Returns:
        List of API request records
    """
    connection = None
    try:
        connection = get_db_connection()

        # Calculate the date range
        end_date = datetime.now().date()
        if period == "day":
            start_date = end_date
        elif period == "week":
            start_date = end_date - timedelta(days=7)
        elif period == "month":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)  # Default to week

        query = sql.SQL("""
            SELECT 
                id, timestamp, api_type, user_id, model, request_id,
                prompt_tokens, completion_tokens, total_tokens, input_count, extra_data
            FROM {table}
            WHERE user_id = %s AND DATE(timestamp) >= %s AND DATE(timestamp) <= %s
            ORDER BY timestamp DESC
            LIMIT %s
        """)

        # Format query with table name
        query = query.format(table=sql.Identifier(usage_table))

        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Ensure user_id is a string
            cursor.execute(query, [str(user_id), start_date, end_date, limit])
            results = cursor.fetchall()

        return [dict(row) for row in results]

    except Exception as e:
        logger.error(f"Error getting user request list: {str(e)}")
        logger.error(traceback.format_exc())
        return []
    finally:
        if connection:
            connection.close()


def get_usage_summary() -> Dict:
    """
    Get overall usage summary statistics.

    Returns:
        Dictionary with summary statistics
    """
    connection = None
    try:
        connection = get_db_connection()
        today = datetime.now().date()

        # Get total number of unique users from the users table
        # Import SQLAlchemy session to access the users table
        # Get database session
        db = next(get_db())

        # Get all users (without limit to count total)
        # Set a high limit to get all users
        users = get_all_users(db, limit=10000)
        total_users = len(users)

        # Get number of active users today from the usage table
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM {table} 
                    WHERE DATE(timestamp) = %s
                """).format(table=sql.Identifier(usage_table)),
                [today]
            )
            active_users_today = cursor.fetchone()[0]

        # Get number of API requests today
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("""
                    SELECT COUNT(*) 
                    FROM {table} 
                    WHERE DATE(timestamp) = %s
                """).format(table=sql.Identifier(usage_table)),
                [today]
            )
            requests_today = cursor.fetchone()[0]

        # Get total tokens used today
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("""
                    SELECT SUM(total_tokens) 
                    FROM {table} 
                    WHERE DATE(timestamp) = %s
                """).format(table=sql.Identifier(usage_table)),
                [today]
            )
            result = cursor.fetchone()[0]
            tokens_today = result if result is not None else 0

        return {
            "total_users": total_users,
            "active_users_today": active_users_today,
            "requests_today": requests_today,
            "tokens_today": tokens_today
        }

    except Exception as e:
        logger.error(f"Error getting usage summary: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "total_users": 0,
            "active_users_today": 0,
            "requests_today": 0,
            "tokens_today": 0
        }
    finally:
        if connection:
            connection.close()


def get_usage(
        user_id: Optional[Union[str, int]] = None,
        time: Optional[Literal['day', 'week', 'month', 'all']] = 'all',
        period: Optional[int] = 7,
        model: Optional[str] = 'all'
) -> List[UsageResponse]:
    """
    Get usage statistics for a user or all users.

    Args:
        user_id: Optional user ID to filter by (will be converted to string)
        time: Time period to filter by (day, week, month, all)
        period: Number of days/weeks/months to retrieve data for
        model: Optional model name to filter by (default: 'all')

    Returns:
        List of usage statistics dictionaries based on specified parameters
    """
    connection = None
    try:
        connection = get_db_connection()

        # Define UTC+8 timezone
        tz_utc8 = timezone(timedelta(hours=8))
        
        # Calculate the date range using UTC+8
        end_date = datetime.now(tz=tz_utc8).date() + timedelta(days=1)  # Include today

        # Determine start date based on time period
        if time == 'day':
            # For daily stats, we look back 'period' number of days
            start_date = end_date - timedelta(days=period-1)
            date_trunc = "DATE(timestamp)"
            group_by = "DATE(timestamp)"

        elif time == 'week':
            # For weekly stats, we look back 'period' number of weeks
            start_date = end_date - timedelta(weeks=period)
            date_trunc = "DATE_TRUNC('week', timestamp)"
            group_by = "DATE_TRUNC('week', timestamp)"

        elif time == 'month':
            # For monthly stats, we look back 'period' number of months
            start_date = end_date - timedelta(days=30 * period)
            date_trunc = "DATE_TRUNC('month', timestamp)"
            group_by = "DATE_TRUNC('month', timestamp)"

        else:  # 'all' or any other value
            # Default to looking back 365 days if not specified otherwise
            start_date = end_date - timedelta(days=365)
            date_trunc = None  # No grouping by time for 'all'
            group_by = None

        # Base query construction
        if model != 'all':
            # If a specific model is requested, group by time period (if specified)
            if date_trunc:
                query = sql.SQL("""
                    SELECT
                        {date_trunc} as time_period,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM {table}
                    WHERE model = %s AND timestamp >= %s AND timestamp <= %s
                """).format(
                    date_trunc=sql.SQL(date_trunc),
                    table=sql.Identifier(usage_table)
                )
                params = [model, start_date, end_date]
            else:
                # If no time grouping ('all'), just get aggregated stats for the model
                query = sql.SQL("""
                    SELECT
                        model,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM {table}
                    WHERE model = %s AND timestamp >= %s AND timestamp <= %s
                """).format(table=sql.Identifier(usage_table))
                params = [model, start_date, end_date]
        else:
            # If no specific model is requested
            if time == 'all':
                # Group by model
                query = sql.SQL("""
                    SELECT
                        model,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM {table}
                    WHERE timestamp >= %s AND timestamp <= %s
                """).format(table=sql.Identifier(usage_table))
                params = [start_date, end_date]

                # Add user filter if specified
                if user_id:
                    query = sql.SQL(query.as_string(
                        connection) + " AND user_id = %s")
                    params.append(str(user_id))  # Ensure user_id is a string

                # Group by model
                query = sql.SQL(query.as_string(connection) +
                                " GROUP BY model ORDER BY total_tokens DESC")
            else:
                # Group by time period
                query = sql.SQL("""
                    SELECT
                        {date_trunc} as time_period,
                        SUM(prompt_tokens) as prompt_tokens,
                        SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                        SUM(total_tokens) as total_tokens,
                        COUNT(*) as request_count
                    FROM {table}
                    WHERE timestamp >= %s AND timestamp <= %s
                """).format(
                    date_trunc=sql.SQL(date_trunc),
                    table=sql.Identifier(usage_table)
                )
                params = [start_date, end_date]

        # Add user filter if specified and not already added
        if user_id and 'user_id' not in query.as_string(connection):
            query = sql.SQL(query.as_string(connection) + " AND user_id = %s")
            params.append(str(user_id))  # Ensure user_id is a string

        # Add group by and order by clauses if not already added and if time grouping is needed
        if group_by and 'GROUP BY' not in query.as_string(connection):
            query = sql.SQL(query.as_string(connection) +
                            f" GROUP BY {group_by} ORDER BY {group_by}")
        elif 'GROUP BY' not in query.as_string(connection) and time == 'all':
            # For 'all' with no specific model, we've already set up the grouping by model above
            pass

        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        # Format results
        formatted_results = []
        for row in results:
            result_dict = dict(row)
            
            # Format time_period if it exists
            if 'time_period' in result_dict and result_dict['time_period']:
                # Always format as YYYY-MM-DD for day, week, and month
                result_dict['time_period'] = result_dict['time_period'].strftime(
                    '%Y-%m-%d')

            formatted_results.append(result_dict)

        return formatted_results

    except Exception as e:
        logger.error(f"Error getting usage statistics: {str(e)}")
        logger.error(traceback.format_exc())
        return []
    finally:
        if connection:
            connection.close()
