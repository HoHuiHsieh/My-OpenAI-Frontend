"""
API key management logic
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Security
from fastapi.security import SecurityScopes


from config import get_config
from .config import API_KEY_EXPIRE_TIME
from .database import save_api_key_to_db, get_api_key_from_db, revoke_api_key_in_db, revoke_api_key_by_user, get_api_key_by_user
from .models import ApiKey, ApiKeyDB, ApiKeyData


class ApiKeyManager:
    """API key management class"""
    
    def __init__(self):
        self.config = get_config()
        self.secret_key = self.config.get_secret_key()
        self.algorithm = self.config.get_algorithm()
    
    def generate_api_key(self, user_id: int, scopes: List[str]) -> ApiKey:
        """Generate a new API key for a user"""
        expires_at = datetime.utcnow() + timedelta(seconds=API_KEY_EXPIRE_TIME)

        # Revoke old API keys for the user
        revoke_api_key_by_user(user_id)
        
        # Create JWT payload
        payload = {
            "user_id": user_id,
            "scopes": scopes,
            "exp": expires_at,
            "type": "api_key"
        }
        
        # Generate JWT token
        api_key = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        # Save to database
        save_api_key_to_db(api_key, user_id, expires_at)

        return ApiKey(
            apiKey=api_key,
            expires_in=API_KEY_EXPIRE_TIME
        )
    
    def validate_api_key(self, api_key: str) -> Optional[ApiKeyData]:
        """Validate an API key"""
        try:
            # First check if the API key exists in database and is not revoked
            db_api_key = get_api_key_from_db(api_key)
            if not db_api_key:
                return None
            
            # Check if expired in database
            if db_api_key.expires_at < datetime.utcnow():
                return None
            
            # Decode and validate JWT
            payload = jwt.decode(api_key, self.secret_key, algorithms=[self.algorithm])
            
            # Verify it's an API key token
            if payload.get("type") != "api_key":
                return None
            
            return ApiKeyData(
                user_id=payload.get("user_id"),
                scopes=payload.get("scopes", []),
                exp=datetime.fromtimestamp(payload.get("exp"))
            )
            
        except jwt.PyJWTError:
            return None
    

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        return revoke_api_key_in_db(api_key)
    

    def get_api_key_by_user(self, user_id: int) -> List[ApiKeyData]:
        """Get a API keys for a user"""
        data = get_api_key_by_user(user_id)
        if not data:
            return None
        
        return self.validate_api_key(data.api_key)