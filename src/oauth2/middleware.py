"""
Authentication middleware for FastAPI.

This module provides middleware to handle authentication for all API requests,
including token validation and user identification.
"""

from fastapi import Request, HTTPException, status
from fastapi.security import SecurityScopes
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import jwt
from typing import List, Optional, Callable, Union

from logger import get_logger
from config import get_config
from .token_manager import verify_token, token_type_session

# Initialize logger
logger = get_logger(__name__)

# Load configuration
config = get_config()
oauth2_config = config.get("oauth2", {})


class OAuth2Middleware(BaseHTTPMiddleware):
    """
    Middleware for OAuth2 token validation and authorization.
    
    This middleware intercepts all requests and validates authentication
    tokens, skipping validation for excluded paths.
    """
    
    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        enable_auth: bool = True
    ):
        """
        Initialize the middleware.
        
        Args:
            app: The FastAPI application
            exclude_paths: List of paths to exclude from authentication
            enable_auth: Whether authentication is enabled
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or oauth2_config.get("exclude_paths", [])
        self.enable_auth = enable_auth if enable_auth is not None else oauth2_config.get("enable_authentication", True)
        
        logger.info(f"OAuth2 middleware initialized. Authentication enabled: {self.enable_auth}")
        logger.info(f"Excluded paths: {self.exclude_paths}")
        
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Union[Response, JSONResponse]:
        """
        Process the request and apply authentication validation.
        
        Args:
            request: The FastAPI request object
            call_next: The next middleware or endpoint in the chain
            
        Returns:
            Response: The HTTP response
        """
        # Skip authentication if disabled
        if not self.enable_auth:
            logger.debug("Authentication disabled, skipping token validation")
            return await call_next(request)
        
        # Skip authentication for excluded paths
        path = request.url.path
        for excluded_path in self.exclude_paths:
            if path.startswith(excluded_path):
                logger.debug(f"Skipping authentication for excluded path: {path}")
                return await call_next(request)
        
        # Skip OPTIONS requests (preflight for CORS)
        if request.method == "OPTIONS":
            logger.debug("Skipping authentication for OPTIONS request")
            return await call_next(request)
        
        # Check for authentication header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"Authentication header missing for path: {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Not authenticated"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token format
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                logger.warning(f"Invalid authentication scheme: {scheme}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Invalid authentication scheme"},
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except ValueError:
            logger.warning("Invalid authorization header format")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token
        try:
            payload = verify_token(token)
            # Add the token payload to the request state for use in endpoints
            request.state.user = payload
            logger.debug(f"Authenticated user: {payload.get('sub')}")
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expired for path: {path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Token expired"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token for path: {path}: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid token"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication error"},
            )
        
        return await call_next(request)
