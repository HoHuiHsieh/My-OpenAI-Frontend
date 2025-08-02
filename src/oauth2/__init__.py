"""
OAuth2 Authentication and Authorization Module

This module handles authentication and authorization using OAuth2 protocol
for the My OpenAI Frontend service. 


It provides:
- User Management
  - With user information: 'username', 'password', 'scopes', 'email', 'fullname', 'active', etc. fields
  - User registration, login, and management
  - Scope-based access control
  - PostgreSQL database integration for user data
  - Add default admin user if not exists
  - User password hashing and verification
- Token Management
  - JWT token support
  - OAuth2 token generation and validation
  - PostgreSQL database integration for refresh tokens

OAuth2 configuration settings available in src/config module

Module Structure:
- __init__.py:                 This file initializes the OAuth2 module
- token_manager/
  - __init__.py:               Token manager package initialization
  - manager.py:                Token management logic
  - models.py:                 Token data models
  - database.py:               Database setup and token model
- user_management/
  - __init__.py:               User management package initialization
  - manager.py:                User management logic
  - models.py:                 User data models
  - database.py:               Database setup and user model
  - scopes.py:                 User scopes ('admin', 'models:read', 'chat:base', 'embeddings:base', etc.)
- routes/
  - __init__.py:               Routes package initialization
  - auth.py:                   Oauth2 tokens validation and refresh endpoints
  - user.py:                   User management endpoints
  - admin.py:                  Admin management endpoints
  - middleware.py:             Middleware for user information extraction from access token

API Endpoints:
- POST /auth/refresh:         Refresh access token endpoint
- POST /user/login:           User login endpoint

API Endpoints (require access token in header):
- GET /auth:                  Access token validation endpoint
- GET /user:                  Get current user information endpoint
- GET /user/scopes:           Get all available scopes endpoint
- PUT /user:                  Update current user information endpoint
- GET /admin/users:           List all users endpoint
- POST /admin/users:          Create new user endpoint
- GET /admin/users/{username}: Get user information by username endpoint
- PUT /admin/users/{username}: Update user information endpoint
- DELETE /admin/users/{username}: Delete user endpoint
"""

# Export routers and middleware for application integration
from .routes import auth_router, user_router, admin_router
from .routes.middleware import get_current_user, get_current_active_user, get_admin_user
from .token_manager import TokenManager
from .user_management import UserManager, SCOPES, User, UserDB


# Initialize managers for direct usage
token_manager = TokenManager()
user_manager = UserManager()


def setup_database():
    """Initialize all database tables"""
    from .token_manager.database import init_database as init_token_db
    from .user_management.database import init_database as init_user_db
    
    # Initialize databases
    init_token_db()
    init_user_db()


__all__ = [
    "auth_router",
    "user_router", 
    "admin_router",
    "get_current_user",
    "get_current_active_user", 
    "get_admin_user",
    "token_manager",
    "user_manager",
    "setup_database",
    "SCOPES"
]