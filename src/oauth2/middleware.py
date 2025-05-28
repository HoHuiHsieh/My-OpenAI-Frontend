"""
OAuth2 Authentication Middleware

This module provides a middleware for FastAPI applications to handle
OAuth2 authentication for protected endpoints.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import jwt
from typing import List
from datetime import datetime
from . import SECRET_KEY, ALGORITHM, ADMIN_TOKEN_NEVER_EXPIRES, USER_TOKEN_EXPIRE_DAYS
from .database import SessionLocal, DBUser
from logger import get_logger

logger = get_logger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exclude_paths: List[str] = None):
        """
        Initialize the auth middleware with paths to exclude from authentication
        
        Args:
            app: The FastAPI application
            exclude_paths: List of paths to exclude from authentication checks (e.g. ["/docs", "/token"])
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/token", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request through the middleware
        
        Args:
            request: The incoming FastAPI request
            call_next: The next middleware or route handler
            
        Returns:
            Response from the next handler or an error response
        """
        # Skip authentication for excluded paths
        path = request.url.path
        
        # Check exact matches or prefixes
        if any(
            path == exclude or 
            path.startswith(exclude) or 
            (exclude.endswith('/') and path.startswith(exclude))
            for exclude in self.exclude_paths
        ):
            logger.debug(f"Skipping authentication for excluded path: {path}")
            return await call_next(request)
            
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            # Check if this is an HTML request to the admin page
            path = request.url.path
            if path.endswith('admin.html'):
                logger.debug(f"Unauthenticated request to admin page, redirecting to index.html")
                # Redirect to index.html with login required
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url="/share/index.html")
            
            # Otherwise return standard 401 response
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Validate token format
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Decode and validate the token
        try:
            # First try to decode without verifying expiration for potential admin or long-lived tokens
            try:
                # Try to decode without verifying expiration
                payload_without_exp = jwt.decode(
                    token, 
                    SECRET_KEY, 
                    algorithms=[ALGORITHM], 
                    options={"verify_exp": False}
                )
                username = payload_without_exp.get("sub")
                token_scopes = payload_without_exp.get("scopes", [])
                
                # Check if this is an admin token (admins can have non-expiring tokens if configured)
                is_admin = "admin" in token_scopes
                
                # Get expiration info if present
                exp = payload_without_exp.get("exp")
                now = datetime.now().timestamp()
                
                # If token is expired, it may still be valid if it's an admin token
                if exp and exp < now and is_admin and ADMIN_TOKEN_NEVER_EXPIRES:
                    # This is an expired admin token, but admin tokens never expire if configured
                    pass
                else:
                    # For non-admin tokens or if admin tokens do expire, verify normally
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    username = payload.get("sub")
                    token_scopes = payload.get("scopes", [])
            except jwt.ExpiredSignatureError:
                # Token is expired and not an admin token that bypasses expiration
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if user exists in database
            db = SessionLocal()
            try:
                user = db.query(DBUser).filter(DBUser.username == username).first()
                if user is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                    
                # Check if the user is disabled
                if user.disabled:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User is disabled",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # Check if token is long-lived (by checking if exp is more than 1 day in the future)
                # If so, verify that user hasn't been forced to refresh their tokens
                exp = payload_without_exp.get("exp")
                if exp and exp > datetime.now().timestamp() + 86400:  # More than 1 day
                    is_admin = "admin" in token_scopes
                    
                    # Skip this check for admin users if admin tokens never expire
                    if not (is_admin and ADMIN_TOKEN_NEVER_EXPIRES) and user.last_token_refresh:
                        # Calculate when the token was issued (roughly)
                        token_issue_time = datetime.fromtimestamp(
                            exp - (USER_TOKEN_EXPIRE_DAYS * 86400)  # Subtract token lifetime
                        )
                        
                        # If token was issued before the last refresh time, it's invalid
                        if user.last_token_refresh and token_issue_time < datetime.fromisoformat(user.last_token_refresh):
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token was invalidated by a newer refresh",
                                headers={"WWW-Authenticate": "Bearer"},
                            )
            finally:
                db.close()
                
            # Add user info to request state
            request.state.user = username
            request.state.scopes = token_scopes
            
            # Log successful authentication
            is_long_lived = exp and exp > datetime.now().timestamp() + 86400
            logger.info(
                f"User '{username}' authenticated successfully on path '{request.url.path}' "
                f"using {'long-lived' if is_long_lived else 'short-lived'} token"
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format or signature",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Continue processing the request
        return await call_next(request)
