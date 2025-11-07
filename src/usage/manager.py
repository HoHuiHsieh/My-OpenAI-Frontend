"""
Usage logs logic
"""
import sys
import logging
import secrets
from datetime import datetime, timedelta
import threading
from typing import Dict, Optional, List
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from config import Config
from .models import UsageResponse, UsageSummary, UsageEntry
from .handler import create_usage_log_handler


class UsageManager:
    """Usage logs management functionality"""

    def __init__(self, config: Optional['Config'] = None):
        """
        Initialize usage manager with configuration.
        
        Args:
            config: Configuration object. If None, creates a new Config instance.
        """
        self.config = config if config is not None else Config()
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: Dict[str, logging.Handler] = {}
        self._initialized = False
        self._is_shutting_down = False
        self._lock = threading.RLock()
        self.connection = None  # psycopg2 connection

    def initialize(self) -> bool:
        """
        Initialize the usage logging system.
        
        Returns:
            bool: True if initialization successful
        """
        with self._lock:
            if self._initialized:
                return True
            
            try:
                # Add custom logging level for usage
                logging.addLevelName(25, "USAGE")

                # Set up usage logger with a specific name instead of root logger
                usage_logger = logging.getLogger("usage_tracker")

                # Clear any existing handlers for this specific logger
                usage_logger.handlers.clear()
                
                # Prevent propagation to root logger to avoid interference
                usage_logger.propagate = False

                # Add database handler if enabled and configured
                db_handler = create_usage_log_handler(self.config)
                if db_handler:
                    usage_logger.addHandler(db_handler)
                    self._handlers['database'] = db_handler
                    
                    # Get a connection from the handler's connection pool
                    self.connection = db_handler.connection_pool.getconn()
                else:
                    print("Database handler not configured or failed to create", file=sys.stderr)
                    return False
                
                self._initialized = True
                return True
                
            except Exception as e:
                print(f"Failed to initialize usage logging system: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                return False
        

    def get_usage_logger(self, api_type: str) -> logging.Logger:
        """
        Get a logger instance for usage logging.

        Parameters:
        - **api_type**: Name of the logger

        Returns a logging.Logger instance configured for usage logging.
        """
        with self._lock:
            # Allow getting loggers even during initialization
            if api_type in self._loggers:
                return self._loggers[api_type]

            logger = logging.getLogger(api_type)

            # Directly add handlers to this logger instead of relying on propagation
            for handler in self._handlers.values():
                if handler not in logger.handlers:
                    logger.addHandler(handler)
            
            # Set appropriate log level for usage logging
            logger.setLevel(25)  # USAGE level

            self._loggers[api_type] = logger
            return logger

    def shutdown(self):
        """
        Shutdown the usage manager, closing any open resources.
        """
        with self._lock:
            if self._is_shutting_down:
                return

            self._is_shutting_down = True

            # Return database connection to pool
            if self.connection and 'database' in self._handlers:
                try:
                    db_handler = self._handlers['database']
                    if hasattr(db_handler, 'connection_pool') and db_handler.connection_pool:
                        db_handler.connection_pool.putconn(self.connection)
                except Exception as e:
                    print(f"Error returning connection to pool: {e}", file=sys.stderr)

            # Close all handlers
            for handler in self._handlers.values():
                try:
                    handler.close()
                except Exception as e:
                    print(f"Error closing handler: {e}", file=sys.stderr)

            self._handlers.clear()
            self._loggers.clear()
            self._initialized = False


    def get_usage_data(
        self,
        user_id: Optional[str] = None,
        time: str = "all",
        period: int = 7,
        model: str = "all",
    ) -> List[UsageResponse]:
        """
        Retrieve usage data for a specific user or all users.

        Parameters:
        - **user_id**: ID of the user to filter by (optional)
        - **time**: Time period to filter by (day, week, month, all)
        - **period**: Number of periods to retrieve data for (default: 7)
        - **model**: Specific model to filter by (default: "all")

        Returns a list of usage statistics.
        """
        if not self._initialized or not self.connection:
            print("Usage manager not initialized", file=sys.stderr)
            return []

        try:
            # Calculate time range based on period type
            end_date = datetime.utcnow()
            
            if time == "day":
                start_date = end_date - timedelta(days=period)
                date_trunc = "day"
            elif time == "week":
                start_date = end_date - timedelta(weeks=period)
                date_trunc = "week"
            elif time == "month":
                start_date = end_date - timedelta(days=period * 30)
                date_trunc = "month"
            else:  # "all"
                start_date = datetime(2020, 1, 1)  # Far past date
                date_trunc = "day"

            # Build the query
            table_name = f"{self.config.get_table_prefix()}_usage"
            
            base_query = sql.SQL("""
                SELECT 
                    date_trunc(%s, timestamp) as time_period,
                    SUM(prompt_tokens) as prompt_tokens,
                    SUM(COALESCE(completion_tokens, 0)) as completion_tokens,
                    SUM(total_tokens) as total_tokens,
                    COUNT(*) as request_count,
                    COUNT(DISTINCT user_id) as user_count,
                    MIN(timestamp) as start_date,
                    MAX(timestamp) as end_date
                FROM {table}
                WHERE timestamp >= %s AND timestamp <= %s
            """).format(table=sql.Identifier(table_name))

            query_params = [date_trunc, start_date, end_date]

            # Add user filter if specified
            if user_id:
                base_query = sql.SQL(str(base_query) + " AND user_id = %s")
                query_params.append(user_id)

            # Add model filter if specified
            if model and model != "all":
                base_query = sql.SQL(str(base_query) + " AND model = %s")
                query_params.append(model)

            # Add grouping and ordering
            if time != "all":
                base_query = sql.SQL(str(base_query) + """
                    GROUP BY date_trunc(%s, timestamp)
                    ORDER BY time_period DESC
                    LIMIT %s
                """)
                query_params.extend([date_trunc, period])
            else:
                base_query = sql.SQL(str(base_query) + """
                    GROUP BY date_trunc(%s, timestamp)
                    ORDER BY time_period DESC
                """)
                query_params.append(date_trunc)

            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(base_query, query_params)
                rows = cursor.fetchall()

                results = []
                for row in rows:
                    usage_response = UsageResponse(
                        time_period=row['time_period'].isoformat() if row['time_period'] else None,
                        prompt_tokens=int(row['prompt_tokens'] or 0),
                        completion_tokens=int(row['completion_tokens'] or 0),
                        total_tokens=int(row['total_tokens'] or 0),
                        request_count=int(row['request_count'] or 0),
                        model=model if model != "all" else None,
                        start_date=row['start_date'],
                        end_date=row['end_date'],
                        user_count=int(row['user_count'] or 0) if not user_id else None
                    )
                    results.append(usage_response)

                return results

        except Exception as e:
            print(f"Error retrieving usage data: {e}", file=sys.stderr)
            return []

    def get_usage_summary(
        self,
    ) -> UsageSummary:
        """
        Retrieve a summary of usage statistics.

        Returns a summary of usage statistics including total tokens, requests, and time-based aggregations.
        """
        if not self._initialized or not self.connection:
            print("Usage manager not initialized", file=sys.stderr)
            return UsageSummary(
                total_users=0,
                active_users_today=0,
                requests_today=0,
                tokens_today=0
            )

        try:
            table_name = f"{self.config.get_table_prefix()}_usage"
            today = datetime.utcnow().date()
            
            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get total number of unique users
                cursor.execute(
                    sql.SQL("SELECT COUNT(DISTINCT user_id) as total_users FROM {table}").format(
                        table=sql.Identifier(table_name)
                    )
                )
                total_users_result = cursor.fetchone()
                total_users = int(total_users_result['total_users'] or 0)

                # Get today's statistics
                cursor.execute(
                    sql.SQL("""
                        SELECT 
                            COUNT(DISTINCT user_id) as active_users_today,
                            COUNT(*) as requests_today,
                            SUM(total_tokens) as tokens_today
                        FROM {table}
                        WHERE DATE(timestamp) = %s
                    """).format(table=sql.Identifier(table_name)),
                    [today]
                )
                today_stats = cursor.fetchone()

                active_users_today = int(today_stats['active_users_today'] or 0)
                requests_today = int(today_stats['requests_today'] or 0)
                tokens_today = int(today_stats['tokens_today'] or 0)

                return UsageSummary(
                    total_users=total_users,
                    active_users_today=active_users_today,
                    requests_today=requests_today,
                    tokens_today=tokens_today
                )

        except Exception as e:
            print(f"Error retrieving usage summary: {e}", file=sys.stderr)
            return UsageSummary(
                total_users=0,
                active_users_today=0,
                requests_today=0,
                tokens_today=0
            )

    def get_user_request_list(
        self,
        user_id: str,
        period: str = "all",
        limit: int = 100
    ) -> List[UsageEntry]:
        """
        Get a list of API requests made by a specific user.
        Parameters:
        - **user_id**: ID of the user
        - **period**: Time period to filter by (day, week, month, all)
        - **limit**: Maximum number of records to return
        Returns a list of UsageEntry objects.
        """
        if not self._initialized or not self.connection:
            print("Usage manager not initialized", file=sys.stderr)
            return []

        try:
            end_date = datetime.utcnow()
            if period == "day":
                start_date = end_date - timedelta(days=1)
            elif period == "week":
                start_date = end_date - timedelta(weeks=1)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime(2020, 1, 1)

            table_name = f"{self.config.get_table_prefix()}_usage"
            query = sql.SQL("""
                SELECT id, timestamp, api_type, user_id, model, request_id,
                       prompt_tokens, completion_tokens, total_tokens, input_count, extra_data
                FROM {table}
                WHERE user_id = %s AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp DESC
                LIMIT %s
            """).format(table=sql.Identifier(table_name))
            params = [user_id, start_date, end_date, limit]

            with self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                entries = []
                for row in rows:
                    entry = UsageEntry(**row)
                    entries.append(entry)
                return entries
        except Exception as e:
            print(f"Error retrieving user request list: {e}", file=sys.stderr)
            return []

    def get_model_list(self) -> List[str]:
        """Get a list of available models."""
        model_list = self.config.get_models()
        model_list = [m for m in model_list if m]  # Filter out empty models
        return model_list