"""
Usage logs logic
"""
import sys
import logging
import secrets
from datetime import datetime, timedelta
import threading
from typing import Dict, Optional, List
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from config import Config
from database import get_db_session
from database.schema import UsageLogDB
from .models import UsageResponse, UsageSummary, UsageEntry
from .sqlalchemy_handler import create_usage_log_handler


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
        if not self._initialized:
            print("Usage manager not initialized", file=sys.stderr)
            return []

        try:
            # Calculate time range based on period type
            end_date = datetime.now()
            
            if time == "day":
                start_date = end_date - timedelta(days=period)
                date_trunc_func = func.date_trunc('day', func.timezone('localtime', UsageLogDB.timestamp))
            elif time == "week":
                start_date = end_date - timedelta(weeks=period)
                date_trunc_func = func.date_trunc('week', func.timezone('localtime', UsageLogDB.timestamp))
            elif time == "month":
                start_date = end_date - timedelta(days=period * 30)
                date_trunc_func = func.date_trunc('month', func.timezone('localtime', UsageLogDB.timestamp))
            else:  # "all"
                start_date = datetime(2020, 1, 1)  # Far past date
                date_trunc_func = func.date_trunc('day', func.timezone('localtime', UsageLogDB.timestamp))

            with get_db_session() as session:
                # Build the query
                query = session.query(
                    date_trunc_func.label('time_period'),
                    func.sum(UsageLogDB.prompt_tokens).label('prompt_tokens'),
                    func.sum(func.coalesce(UsageLogDB.completion_tokens, 0)).label('completion_tokens'),
                    func.sum(UsageLogDB.total_tokens).label('total_tokens'),
                    func.count().label('request_count'),
                    func.count(func.distinct(UsageLogDB.user_id)).label('user_count'),
                    func.min(UsageLogDB.timestamp).label('start_date'),
                    func.max(UsageLogDB.timestamp).label('end_date')
                ).filter(
                    and_(
                        UsageLogDB.timestamp >= start_date,
                        UsageLogDB.timestamp <= end_date
                    )
                )

                # Add user filter if specified
                if user_id:
                    query = query.filter(UsageLogDB.user_id == user_id)

                # Add model filter if specified
                if model and model != "all":
                    query = query.filter(UsageLogDB.model == model)

                # Add grouping and ordering
                query = query.group_by(date_trunc_func).order_by(date_trunc_func.desc())

                # Add limit if not "all"
                if time != "all":
                    query = query.limit(period)

                rows = query.all()

                results = []
                for row in rows:
                    usage_response = UsageResponse(
                        time_period=row.time_period.isoformat() if row.time_period else None,
                        prompt_tokens=int(row.prompt_tokens or 0),
                        completion_tokens=int(row.completion_tokens or 0),
                        total_tokens=int(row.total_tokens or 0),
                        request_count=int(row.request_count or 0),
                        model=model if model != "all" else None,
                        start_date=row.start_date,
                        end_date=row.end_date,
                        user_count=int(row.user_count or 0) if not user_id else None
                    )
                    results.append(usage_response)

                return results

        except Exception as e:
            print(f"Error retrieving usage data: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []

    def get_usage_summary(
        self,
    ) -> UsageSummary:
        """
        Retrieve a summary of usage statistics.

        Returns a summary of usage statistics including total tokens, requests, and time-based aggregations.
        """
        if not self._initialized:
            print("Usage manager not initialized", file=sys.stderr)
            return UsageSummary(
                total_users=0,
                active_users_today=0,
                requests_today=0,
                tokens_today=0
            )

        try:
            today = datetime.now().date()
            
            with get_db_session() as session:
                # Get total number of unique users
                total_users = session.query(func.count(func.distinct(UsageLogDB.user_id))).scalar()
                total_users = int(total_users or 0)

                # Get today's statistics
                today_stats = session.query(
                    func.count(func.distinct(UsageLogDB.user_id)).label('active_users_today'),
                    func.count().label('requests_today'),
                    func.sum(UsageLogDB.total_tokens).label('tokens_today')
                ).filter(
                    func.date(UsageLogDB.timestamp) == today
                ).one()

                active_users_today = int(today_stats.active_users_today or 0)
                requests_today = int(today_stats.requests_today or 0)
                tokens_today = int(today_stats.tokens_today or 0)

                return UsageSummary(
                    total_users=total_users,
                    active_users_today=active_users_today,
                    requests_today=requests_today,
                    tokens_today=tokens_today
                )

        except Exception as e:
            print(f"Error retrieving usage summary: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
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
        if not self._initialized:
            print("Usage manager not initialized", file=sys.stderr)
            return []

        try:
            end_date = datetime.now()
            if period == "day":
                start_date = end_date - timedelta(days=1)
            elif period == "week":
                start_date = end_date - timedelta(weeks=1)
            elif period == "month":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime(2020, 1, 1)

            with get_db_session() as session:
                query = session.query(UsageLogDB).filter(
                    and_(
                        UsageLogDB.user_id == user_id,
                        UsageLogDB.timestamp >= start_date,
                        UsageLogDB.timestamp <= end_date
                    )
                ).order_by(UsageLogDB.timestamp.desc()).limit(limit)
                
                rows = query.all()
                entries = []
                for row in rows:
                    # Detach from session before returning
                    session.expunge(row)
                    entry = UsageEntry(
                        id=row.id,
                        timestamp=row.timestamp,
                        api_type=row.api_type,
                        user_id=row.user_id,
                        model=row.model,
                        request_id=row.request_id,
                        prompt_tokens=row.prompt_tokens,
                        completion_tokens=row.completion_tokens,
                        total_tokens=row.total_tokens,
                        input_count=row.input_count,
                        extra_data=row.extra_data
                    )
                    entries.append(entry)
                return entries
        except Exception as e:
            print(f"Error retrieving user request list: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []

    def get_model_list(self) -> List[str]:
        """Get a list of available models."""
        model_list = self.config.get_models()
        model_list = [m for m in model_list if m]  # Filter out empty models
        return model_list