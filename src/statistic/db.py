"""
Database access and query functions for statistics.

This module provides database interaction functions specifically for retrieving
and analyzing usage statistics from the logging database.
"""

import traceback
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from config import get_config
from logger import get_logger
from oauth2.db import get_db
from oauth2.db.operations import get_all_users

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


def get_daily_usage(user_id: Optional[Union[str, int]] = None, days: int = 7) -> List[Dict]:
    """
    Get daily usage statistics for a user or all users.

    Args:
        user_id: Optional user ID to filter by (will be converted to string)
        days: Number of days to retrieve data for

    Returns:
        List of daily usage data
    """
    connection = None
    try:
        connection = get_db_connection()

        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)

        query = sql.SQL("""
            SELECT 
                DATE(timestamp) as date,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count
            FROM {table}
            WHERE timestamp >= %s AND timestamp < %s + INTERVAL '1 day'
        """)

        # Add user filter if specified
        params = [start_date, end_date]
        if user_id:
            query = sql.SQL(query.as_string(connection) + " AND user_id = %s")
            params.append(str(user_id))  # Ensure user_id is a string

        # Group by date and order by date
        query = sql.SQL(query.as_string(connection) +
                        " GROUP BY date ORDER BY date")

        # Format query with table name
        query = query.format(table=sql.Identifier(usage_table))

        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        return [dict(row) for row in results]

    except Exception as e:
        logger.error(f"Error getting daily usage: {str(e)}")
        logger.error(traceback.format_exc())
        return []
    finally:
        if connection:
            connection.close()


def get_weekly_usage(user_id: Optional[Union[str, int]] = None, weeks: int = 4) -> List[Dict]:
    """
    Get weekly usage statistics for a user or all users.

    Args:
        user_id: Optional user ID to filter by (will be converted to string)
        weeks: Number of weeks to retrieve data for

    Returns:
        List of weekly usage data
    """
    connection = None
    try:
        connection = get_db_connection()

        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(weeks=weeks)

        query = sql.SQL("""
            SELECT 
                DATE_TRUNC('week', timestamp) as week_start,
                DATE_TRUNC('week', timestamp) + INTERVAL '6 days' as week_end,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count
            FROM {table}
            WHERE timestamp >= %s AND timestamp <= %s
        """)

        # Add user filter if specified
        params = [start_date, end_date]
        if user_id:
            query = sql.SQL(query.as_string(connection) + " AND user_id = %s")
            params.append(str(user_id))  # Ensure user_id is a string

        # Group by week and order by week
        query = sql.SQL(query.as_string(connection) +
                        " GROUP BY week_start, week_end ORDER BY week_start")

        # Format query with table name
        query = query.format(table=sql.Identifier(usage_table))

        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        return [dict(row) for row in results]

    except Exception as e:
        logger.error(f"Error getting weekly usage: {str(e)}")
        logger.error(traceback.format_exc())
        return []
    finally:
        if connection:
            connection.close()


def get_monthly_usage(user_id: Optional[Union[str, int]] = None, months: int = 6) -> List[Dict]:
    """
    Get monthly usage statistics for a user or all users.

    Args:
        user_id: Optional user ID to filter by (will be converted to string)
        months: Number of months to retrieve data for

    Returns:
        List of monthly usage data
    """
    connection = None
    try:
        connection = get_db_connection()

        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30 * months)

        query = sql.SQL("""
            SELECT 
                EXTRACT(YEAR FROM timestamp) as year,
                EXTRACT(MONTH FROM timestamp) as month,
                SUM(prompt_tokens) as prompt_tokens,
                SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                SUM(total_tokens) as total_tokens,
                COUNT(*) as request_count
            FROM {table}
            WHERE timestamp >= %s AND timestamp <= %s
        """)

        # Add user filter if specified
        params = [start_date, end_date]
        if user_id:
            query = sql.SQL(query.as_string(connection) + " AND user_id = %s")
            params.append(str(user_id))  # Ensure user_id is a string

        # Group by month and year, order by year and month
        query = sql.SQL(query.as_string(connection) +
                        " GROUP BY year, month ORDER BY year, month")

        # Format query with table name
        query = query.format(table=sql.Identifier(usage_table))

        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, params)
            results = cursor.fetchall()

        return [dict(row) for row in results]

    except Exception as e:
        logger.error(f"Error getting monthly usage: {str(e)}")
        logger.error(traceback.format_exc())
        return []
    finally:
        if connection:
            connection.close()


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
