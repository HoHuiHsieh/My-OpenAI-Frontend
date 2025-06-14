"""
Home Made AI Agent Support Module.

This module defines types and functions that are specific to the home made AI agent.

The module is organized into submodules for better code organization:
- formatting.py: Functions for formatting messages in custom format
- utils.py: Utility functions for working with custom models
"""

# Import all relevant components
from .formatting import format_messages_for_home_made_agent
from .utils import is_home_made_agent_model
