"""
OAuth2 Authentication and Authorization Module

This module handles authentication and authorization using OAuth2 protocol
for the My OpenAI Frontend service. It provides functionality for:
- Token validation
- User authentication
- Role-based access control
- Integration with various identity providers
- PostgreSQL database integration for user management

Token Management:
- Dual token system:
  - Session tokens for webpage access (short-lived authentication)
  - Access tokens for model APIs access with fine-grained scope control
- Token configuration settings available in assets/config.yml

Module Structure:
- auth.py:                     Core authentication functionality
- token_manager/
  - __init__.py:               Token manager package initialization
  - base.py:                   Common token functionality
  - session.py:                Short-lived session tokens for web access
  - access.py:                 API access tokens with scope control
- db/
  - __init__.py:               Database package initialization
  - models.py:                 User and token data models
  - operations.py:             Database operations
- rbac.py:                     Role-based access control
- scopes.py:                   API scope definitions and management
- middleware.py:               Authentication middleware
- routes/
  - __init__.py:               Routes package initialization
  - session.py:                Session token endpoints (/session, /session/user)
  - access.py:                 Access token endpoints (/access/*)
  - admin.py:                  Admin endpoints (/admin/*)
  - validator.py:              Request validation middleware


API Endpoints:
- POST /session:            Login endpoint to obtain session tokens

API Endpoints (require login):
- GET  /session/user:       Endpoint to get current user information with session token
- POST /access/refresh:     Endpoint to refresh access tokens
- POST /access/info:        Endpoint to get access token information

Admin API Endpoints (require admin role):
- GET  /admin/users:                List all users
- GET  /admin/users/{username}:     Get user information by username
- POST /admin/users:                Create a new user
- PUT  /admin/users/{username}:     Update user information
- DELETE /admin/users/{username}:   Delete a user
- GET  /admin/access:               List all access tokens
- POST /admin/access/{username}:    Create access token for a user
- DELETE /admin/access/{username}:  Revoke access token for a user

"""

from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from passlib.context import CryptContext
from config import get_config
from logger import get_logger
from .scopes import available_scopes


# Initialize the enhanced logging system
logger = get_logger(__name__)

# Load OAuth2 config
config = get_config()
oauth2_config = config.get("oauth2", {})

# Initialize OAuth2 components
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="session",
    scopes={scope: scope for scope in available_scopes},
)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Import token managers first to avoid circular imports
from .token_manager import (
    create_session_token,
    create_access_token, 
    verify_token,
    decode_token,
    token_type_session,
    token_type_access
)

# Import auth and middleware
from .auth import verify_password, get_password_hash, authenticate_user
from .middleware import OAuth2Middleware
from .rbac import RoleBasedAccessControl, verify_scopes
from .scopes import Scopes, available_scopes

# Import database models and operations
from .db.models import User, Token
from .db.operations import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    update_user,
    delete_user,
    get_all_users,
    get_user_tokens,
    create_token_for_user,
    delete_user_token,
    check_token_revoked
)

# Import user dependencies for v1 API
from .dependencies import get_current_user, get_current_active_user

# Create router objects and export them
from .routes import session_router, access_router, admin_router

__all__ = [
    # Core auth functions
    "verify_password", "get_password_hash", "authenticate_user",
    
    # Middleware
    "OAuth2Middleware",
    
    # Role-based access control
    "RoleBasedAccessControl", "verify_scopes",
    
    # Scopes
    "Scopes", "available_scopes", "admin_scopes", "user_scopes",
    
    # Token management
    "create_session_token", "create_access_token", 
    "verify_token", "decode_token",
    "token_type_session", "token_type_access",
      # Database models and operations
    "User", "Token",
    "get_user_by_username", "get_user_by_email",
    "create_user", "update_user", "delete_user",
    "get_all_users", "get_user_tokens",
    "create_token_for_user", "delete_user_token", "check_token_revoked",
    
    # User dependencies
    "get_current_user", "get_current_active_user",
    
    # Routers
    "session_router", "access_router", "admin_router",
    
    # FastAPI requirements
    "oauth2_scheme", "SecurityScopes"
]