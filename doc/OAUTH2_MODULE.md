# OAUTH2 Module Documentation

## Overview

The OAUTH2 module provides comprehensive authentication and authorization functionality using the OAuth2 protocol with JWT tokens. It handles user management, token generation and validation, scope-based access control, and secure database integration for the application.

## Features

- **OAuth2 Compliance**: Standard OAuth2 implementation with JWT tokens
- **User Management**: Complete user lifecycle management (CRUD operations)
- **Token Management**: Access and refresh token generation, validation, and rotation
- **Scope-Based Authorization**: Fine-grained permission control with user scopes
- **PostgreSQL Integration**: Persistent storage for users and refresh tokens
- **Password Security**: BCrypt hashing with secure password handling
- **Admin Management**: Administrative endpoints for user management
- **Middleware Integration**: FastAPI middleware for automatic authentication
- **Default Admin Setup**: Automatic creation of default admin user

## Module Structure

```
src/oauth2/
├── __init__.py              # Module initialization and exports
├── token_manager/
│   ├── __init__.py         # Token manager package
│   ├── manager.py          # TokenManager class
│   ├── models.py           # Token data models
│   └── database.py         # Token database operations
├── user_management/
│   ├── __init__.py         # User management package
│   ├── manager.py          # UserManager class
│   ├── models.py           # User data models
│   ├── database.py         # User database operations
│   └── scopes.py           # User scope definitions
└── routes/
    ├── __init__.py         # Routes package
    ├── auth.py             # Authentication endpoints
    ├── user.py             # User endpoints
    ├── admin.py            # Admin endpoints
    └── middleware.py       # Authentication middleware
```

## Data Models

### User Models

#### UserBase
Base user information:
```python
class UserBase(BaseModel):
    username: str              # Unique username
    email: EmailStr           # Email address with validation
    fullname: str             # Full display name
    active: bool = True       # Account active status
    scopes: List[str] = []    # User permissions/scopes
```

#### UserCreate
User creation model with password:
```python
class UserCreate(UserBase):
    password: str             # Plain text password (will be hashed)
```

#### UserUpdate
Partial user update model:
```python
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None      # Optional email update
    fullname: Optional[str] = None        # Optional fullname update
    password: Optional[str] = None        # Optional password update
    active: Optional[bool] = None         # Optional active status update
    scopes: Optional[List[str]] = None    # Optional scopes update
```

#### User
Complete user model with all fields:
```python
class User(UserBase):
    id: int                   # Unique user ID
    hashed_password: str      # BCrypt hashed password
    created_at: datetime      # Account creation timestamp
    updated_at: Optional[datetime] = None  # Last update timestamp
```

### Token Models

#### Token
OAuth2 token response:
```python
class Token(BaseModel):
    access_token: str         # JWT access token
    token_type: str          # Always "bearer"
    expires_in: int          # Token expiration in seconds
    refresh_token: str       # Refresh token for renewal
```

#### TokenData
Extracted token payload:
```python
class TokenData(BaseModel):
    username: str            # Token subject (username)
    scopes: List[str] = []   # User permissions
    exp: Optional[datetime] = None  # Expiration time
```

#### TokenPayload
Complete JWT payload:
```python
class TokenPayload(BaseModel):
    sub: str                 # Subject (username)
    scopes: List[str] = []   # User permissions
    iat: datetime           # Issued at time
    exp: datetime           # Expiration time
    jti: str                # JWT ID (unique token identifier)
```

## User Scopes

The system supports hierarchical permission scopes:

```python
class SCOPES:
    ADMIN_SCOPE = "admin"                    # Full administrative access
    MODELS_READ = "models:read"              # Read model information
    CHAT_BASE = "chat:base"                  # Access chat APIs
    EMBEDDINGS_BASE = "embeddings:base"      # Access embedding APIs
    AUDIO_TRANSCRIBE = "audio:transcribe"    # Access audio APIs
```

## Database Schema

### Users Table
```sql
CREATE TABLE {prefix}_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    fullname VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    scopes TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### Refresh Tokens Table
```sql
CREATE TABLE {prefix}_refresh_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES {prefix}_users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Examples

### Basic Authentication Setup
```python
from oauth2 import setup_database, auth_router, user_router, admin_router
from fastapi import FastAPI

app = FastAPI()

# Initialize database tables
setup_database()

# Include OAuth2 routes
app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
```

### User Authentication
```python
from oauth2 import get_current_active_user, User
from fastapi import Depends

@app.get("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_active_user)
):
    return {"username": current_user.username, "scopes": current_user.scopes}
```

### Admin-Only Endpoints
```python
from oauth2 import get_admin_user, User
from fastapi import Depends

@app.get("/admin-only")
async def admin_endpoint(
    admin_user: User = Depends(get_admin_user)
):
    return {"message": "Admin access granted"}
```

### Direct Manager Usage
```python
from oauth2 import user_manager, token_manager
from oauth2.user_management import UserCreate

# Create a new user
new_user_data = UserCreate(
    username="testuser",
    email="test@example.com",
    fullname="Test User",
    password="securepassword",
    scopes=["chat:base", "models:read"]
)

with user_manager.SessionLocal() as db:
    new_user = user_manager.create_user(db, new_user_data)
    print(f"Created user: {new_user.username}")
```

## API Endpoints

### Authentication Endpoints

#### POST /user/login
User login with OAuth2 credentials.

**Request Body:**
```json
{
    "username": "string",
    "password": "string",
    "scope": "string"  // Space-separated scopes
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "very-long-secure-token"
}
```

#### GET /auth/
Validate current access token.

**Headers:**
```http
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "username": "testuser",
    "scopes": ["chat:base", "models:read"]
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

**Request Body:**
```json
{
    "refresh_token": "very-long-secure-token"
}
```

**Response:** Same as login response with new tokens.

### User Management Endpoints

#### GET /user/
Get current user information.

**Authentication:** Requires valid access token

**Response:**
```json
{
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "fullname": "Test User",
    "active": true,
    "scopes": ["chat:base", "models:read"],
    "created_at": "2025-01-15T10:30:00Z"
}
```

#### PUT /user/
Update current user information.

**Authentication:** Requires valid access token

**Request Body:**
```json
{
    "email": "newemail@example.com",
    "fullname": "New Full Name",
    "password": "newpassword"
}
```

#### GET /user/scopes
Get all available scopes in the system.

**Response:**
```json
["admin", "models:read", "chat:base", "embeddings:base", "audio:transcribe"]
```

### Admin Endpoints

#### GET /admin/users
List all users (admin only).

**Authentication:** Requires admin scope

**Query Parameters:**
- `skip`: Number of records to skip (pagination)
- `limit`: Maximum records to return

#### POST /admin/users
Create a new user (admin only).

**Authentication:** Requires admin scope

**Request Body:**
```json
{
    "username": "newuser",
    "email": "newuser@example.com",
    "fullname": "New User",
    "password": "password",
    "active": true,
    "scopes": ["chat:base"]
}
```

#### GET /admin/users/{username}
Get specific user information (admin only).

#### PUT /admin/users/{username}
Update specific user (admin only).

#### DELETE /admin/users/{username}
Delete user (admin only).

## Configuration Integration

The module integrates with the CONFIG module for settings:

### Required Configuration
```yaml
oauth2:
  enable: true
  secret_key: "your-secret-key-here"
  algorithm: "HS256"
  access_token_expire_time: 3600        # 1 hour
  refresh_token_expire_time: 2592000    # 30 days
  default_admin:
    username: "admin"
    email: "admin@example.com"
    full_name: "Administrator"
    password: "admin_password"
```

### Database Configuration
Uses database settings from CONFIG module:
```yaml
database:
  host: "postgres"
  port: 5432
  username: "postgresql"
  password: "password"
  database: "ai_platform_auth"
  table_prefix: "myopenaiapi"
```

## Security Features

### Password Security
- **BCrypt Hashing**: Industry-standard password hashing
- **Salt Generation**: Automatic salt generation for each password
- **Hash Verification**: Secure password comparison without plaintext storage

### Token Security
- **JWT Signing**: All tokens are cryptographically signed
- **Token Expiration**: Short-lived access tokens with refresh capability
- **Token Rotation**: Refresh tokens are rotated on each use
- **Unique Token IDs**: Each token has a unique identifier (JTI)

### Access Control
- **Scope-Based Authorization**: Fine-grained permission control
- **Admin Protection**: Special admin-only endpoints and functions
- **Active User Validation**: Inactive users are automatically rejected
- **Token Revocation**: Refresh tokens can be revoked

## Middleware Features

### Automatic Authentication
The middleware provides dependency injection for:
- `get_current_user`: Extract user from token (allow inactive)
- `get_current_active_user`: Extract active user from token
- `get_admin_user`: Extract admin user from token

### Error Handling
Comprehensive error responses:
- **401 Unauthorized**: Invalid or expired tokens
- **403 Forbidden**: Insufficient permissions
- **400 Bad Request**: Inactive user accounts

## Advanced Features

### Default Admin Creation
Automatic creation of admin user on first startup:
- Reads admin credentials from configuration
- Creates admin user with all scopes
- Only creates if admin doesn't already exist

### Token Management
- **Refresh Token Rotation**: Old refresh tokens are revoked when new ones are issued
- **Token Cleanup**: Expired tokens can be cleaned from database
- **Concurrent Session Support**: Multiple refresh tokens per user

### User Management
- **Password Updates**: Secure password changing with re-hashing
- **Scope Management**: Dynamic scope assignment and updates
- **Account Activation**: Enable/disable user accounts

## Performance Considerations

### Database Optimization
- **Indexed Queries**: Primary keys and unique constraints
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Efficient user and token lookups

### Token Performance
- **JWT Stateless**: Access tokens don't require database lookups
- **Refresh Token Storage**: Only refresh tokens stored in database
- **Token Expiration**: Short access token lifetime reduces security risk

## Integration with Other Modules

### APIKEY Module
- Shared authentication concepts
- Compatible token validation patterns
- User identification consistency

### CONFIG Module
- JWT secret key configuration
- Database connection settings
- Token expiration settings

### Logger Module
- Authentication event logging
- Error logging and monitoring
- Security audit trails

## Troubleshooting

### Common Issues

**Login Failures**
- Verify username and password are correct
- Check if user account is active
- Confirm database connectivity

**Token Validation Errors**
- Check token expiration times
- Verify JWT secret key configuration
- Ensure proper Authorization header format

**Permission Denied**
- Verify user has required scopes
- Check admin scope for admin endpoints
- Confirm user account is active

**Database Connection Issues**
- Verify PostgreSQL server is running
- Check database credentials in configuration
- Confirm database and tables exist

### Debug Mode
Enable debug logging to troubleshoot:
```python
import logging
logging.getLogger("oauth2").setLevel(logging.DEBUG)
```