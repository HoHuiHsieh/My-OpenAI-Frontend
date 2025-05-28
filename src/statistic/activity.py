"""
This module handles database operations for user activity.

It provides functions for retrieving recent user activity from the usage logs.
"""

import logging
import psycopg2
import psycopg2.extras
from typing import List
from config import get_config
from fastapi import HTTPException, status

from .models import RecentActivity
from .database import get_db_connection, get_table_name

# Create a dedicated logger for activity operations
_activity_logger = logging.getLogger("statistics.activity")


async def get_recent_activity(limit: int = 10) -> List[RecentActivity]:
    """
    Get recent user activity from the usage log.

    Args:
        limit: Maximum number of recent activities to return (default: 10)

    Returns:
        List of recent activities
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

        with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Query the usage table for recent activities
            cursor.execute(f"""
                SELECT 
                    timestamp, 
                    user_id, 
                    api_type AS action,
                    CASE 
                        WHEN model IS NOT NULL THEN CONCAT('Model: ', model)
                        ELSE 'API request'
                    END AS details
                FROM {table_name}
                ORDER BY timestamp DESC
                LIMIT %s
            """, (limit,))

            activities = []
            for row in cursor.fetchall():
                try:
                    # Try to get the actual username for the user_id
                    username = row['user_id']
                    try:
                        cursor.execute(f"SELECT full_name FROM {users_table} WHERE full_name = %s", (row['user_id'],))
                        user_row = cursor.fetchone()
                        if user_row:
                            username = user_row['full_name']
                    except psycopg2.Error as e:
                        connection.rollback()  # Rollback transaction to recover
                        _activity_logger.warning(f"Failed to lookup username for user_id {row['user_id']}: {e}")

                    activities.append(RecentActivity(
                        timestamp=row['timestamp'].isoformat(),
                        username=username,
                        action=row['action'] or "API Request",
                        details=row['details'] or "No details"
                    ))
                except KeyError as e:
                    _activity_logger.warning(f"Missing key in activity row: {e}")
                except Exception as e:
                    _activity_logger.warning(f"Error processing activity for user_id {row['user_id']}: {str(e)}")

            return activities

    except psycopg2.Error as e:
        _activity_logger.error(f"Database error while fetching recent activity: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching recent activity")
    except Exception as e:
        _activity_logger.error(f"Unexpected error while fetching recent activity: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error occurred")
    finally:
        if connection:
            connection.close()
