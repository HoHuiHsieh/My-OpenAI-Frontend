"""
Routes package initialization
"""

from .auth import auth_router
from .user import user_router
from .admin import admin_router
from .middleware import get_current_user, get_current_active_user, get_admin_user

__all__ = ["auth_router", "user_router", "admin_router", "get_current_user", 
           "get_current_active_user", "get_admin_user"]
