"""
API key management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from oauth2 import get_current_active_user, User
from .manager import ApiKeyManager
from .models import ApiKey, ApiKeyData
from .middleware import validate_api_key


# Initialize API key manager
apikey_manager = ApiKeyManager()

# Create router
apikey_router = APIRouter(prefix="/apikey", tags=["apikey"])


@apikey_router.post("", response_model=ApiKey)
@apikey_router.post("/", response_model=ApiKey)
async def create_apikey(current_user: User = Depends(get_current_active_user)):
    """
    Create a new API key for the current user
    """
    try:
        user_id = getattr(current_user, 'id')
        scopes = getattr(current_user, 'scopes', [])
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User ID is required to create an API key"
            )

        # Generate API key with user ID and scopes
        api_key = apikey_manager.generate_api_key(
            user_id=user_id,
            scopes=scopes
        )
        return api_key
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@apikey_router.get("", response_model=ApiKeyData)
@apikey_router.get("/", response_model=ApiKeyData)
async def validate_apikey(
    current_user: User = Depends(get_current_active_user)
):
    """
    Validate the API key, reject if invalid or expired
    """
    return apikey_manager.get_api_key_by_user(current_user.id)
