#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Usage Statistics Module

This module provides interfaces for retrieving API usage statistics from the logging database.
It includes functions to get usage data by time periods (days, weeks, months) for specific users.
Admin users can retrieve usage data for all users or specific users.
"""

import logging

# Import the models and routes
from .models import TimePeriod, UsageStatistics, UserStatistics, AllUsersStatistics, StatisticsSummary
from .router import router

# Create a dedicated logger for statistics
_stats_logger = logging.getLogger("statistics")

# Export the router and types
__all__ = [
    "router",
    "TimePeriod",
    "UsageStatistics",
    "UserStatistics", 
    "AllUsersStatistics",
    "StatisticsSummary"
]
