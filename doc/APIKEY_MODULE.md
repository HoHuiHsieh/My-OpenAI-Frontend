# APIKEY Module Documentation

## Overview

The APIKEY module provides JWT-based API key management functionality for the application. It handles API key generation, validation, storage, and middleware integration with PostgreSQL database support.

## Features

- **JWT-based API Keys**: Secure token generation using JWT (JSON Web Tokens)
- **Database Integration**: PostgreSQL storage for API key persistence and management
- **Scope-based Authorization**: Support for user permissions and access control
- **Middleware Integration**: FastAPI middleware for automatic API key validation
- **Expiration Management**: Configurable API key expiration (default: 30 days)
- **Revocation Support**: Ability to revoke API keys before expiration

## Module Structure

```
src/apikey/
├── __init__.py          # Module initialization and exports
├── config.py            # Configuration settings
├── database.py          # Database operations and models
├── manager.py           # Core API key management logic
├── middleware.py        # FastAPI middleware for validation
├── models.py            # Pydantic data models
└── routes.py            # API endpoints
```

## Data Models

### ApiKey
Response model for API key creation:
```python
{
    "apiKey": "jwt_token_string",
    "expires_in": 2592000  # seconds (30 days)
}
```

### ApiKeyData
Extracted data from validated JWT:
```python
{
    "user_id": 123,
    "scopes": ["read", "write"],
    "exp": "2025-08-30T12:00:00Z"
}
```

### ApiKeyDB
Database model for API key storage:
```python
{
    "id": 1,
    "apiKey": "jwt_token_string",
    "user_id": 123,
    "expires_at": "2025-08-30T12:00:00Z",
    "revoked": false,
    "created_at": "2025-07-31T12:00:00Z"
}
```

## API Endpoints

### POST /apikey
**Create API Key**
- **Authentication**: Requires OAuth2 user authentication
- **Description**: Generates a new API key for the authenticated user
- **Response**: Returns `ApiKey` model with token and expiration info
- **Error Cases**: 
  - 400: Missing user ID
  - 500: API key generation failure

### GET /apikey
**Validate API Key**
- **Authentication**: Requires valid API key in header
- **Description**: Validates the provided API key
- **Response**: HTTP 200 on successful validation
- **Error Cases**:
  - 401: Missing, invalid, or expired API key
  - 403: Insufficient permissions/scopes

## Authentication Methods

The module supports Bearer token format in the Authorization header:

```http
# Bearer format (required)
Authorization: Bearer <jwt_token>
```

## Usage Examples

### Creating an API Key via HTTP
```http
POST /apikey
Authorization: Bearer <oauth2_access_token>
Content-Type: application/json

# Response:
{
    "apiKey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 2592000
}
```

### Using an API Key
```http
GET /protected-endpoint
Authorization: Bearer <api_key_jwt_token>
```

### Creating an API Key Programmatically
```python
from apikey import api_key_manager

# Generate API key for user
api_key = api_key_manager.generate_api_key(
    user_id=123,
    scopes=["read", "write"]
)
print(f"API Key: {api_key.apiKey}")
print(f"Expires in: {api_key.expires_in} seconds")
```

### Validating an API Key in FastAPI
```python
from apikey import validate_api_key
from fastapi import Depends, FastAPI

app = FastAPI()

@app.get("/protected")
async def protected_endpoint(
    api_key_data: ApiKeyData = Depends(validate_api_key)
):
    return {"user_id": api_key_data.user_id}
```

### Optional API Key Validation
```python
from typing import Optional
from apikey import get_optional_api_key, ApiKeyData
from fastapi import Depends

@app.get("/optional-auth")
async def optional_auth_endpoint(
    api_key_data: Optional[ApiKeyData] = Depends(get_optional_api_key)
):
    if api_key_data:
        return {"authenticated": True, "user_id": api_key_data.user_id}
    return {"authenticated": False}
```

## Configuration

### API Key Expiration
Default expiration time is set in `config.py`:
```python
API_KEY_EXPIRE_TIME = 2592000  # 30 days in seconds
```

### Required Dependencies
- JWT secret key and algorithm from main config module
- PostgreSQL database connection
- OAuth2 user authentication system

## Security Features

- **JWT Signing**: All API keys are signed JWT tokens
- **Database Verification**: Double validation against database records
- **Scope Checking**: Automatic permission verification
- **Expiration Handling**: Both JWT and database expiration checks
- **Revocation Support**: Immediate key invalidation capability

## Integration

The module integrates with:
- **Config Module**: For JWT secrets and database configuration
- **OAuth2 Module**: For user authentication during key creation
- **Database**: PostgreSQL for persistent storage
- **FastAPI**: Middleware and dependency injection

## Error Handling

The module provides comprehensive error handling for:
- Invalid JWT tokens
- Expired API keys
- Missing authentication
- Insufficient permissions
- Database connection issues
- Malformed requests