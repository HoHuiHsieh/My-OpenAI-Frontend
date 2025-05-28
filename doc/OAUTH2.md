# OAuth2 Authentication API Documentation

## Overview

This document provides detailed information about the OAuth2 authentication service implemented in the My OpenAI Frontend API. The authentication system supports token-based authentication with different token lifetimes, role-based access control through scopes, and comprehensive user management.

## Configuration

Authentication settings can be configured in `asset/config.yml`:

```yaml
oauth2:
  secret_key: "your-secret-key-placeholder"  # CHANGE THIS IN PRODUCTION!
  algorithm: "HS256"
  access_token_expire_minutes: 30  # Short-lived token for regular sessions
  user_token_expire_days: 180      # 6 months expiration for user tokens
  admin_token_never_expires: true  # Admin tokens never expire
  enable_authentication: true      # Set to false to disable authentication (for development)
  exclude_paths:
    - "/token"
    - "/models"
    - "/favicon.ico"
    - "/static/*"
  default_admin:                   # Configuration for default admin user
    username: "admin"
    email: "admin@example.com"
    full_name: "Admin User"
    password: "secret"
    disabled: false
  scopes:                          # Available scopes in the system
    - "models:read"
    - "models:write"
    - "chat:read"
    - "chat:write"
    - "embeddings:read"
```

The system also requires a database configuration in the same config file:

```yaml
database:
  engine: "postgresql"
  host: "localhost"  
  port: 5432
  username: "postgres"    
  password: "password" 
  name: "ai_platform_auth"        
  ssl_mode: "prefer"
```

## Authentication Middleware

The authentication system implements a middleware that checks every request to protected paths:

1. **Path Validation**:
   - Requests to excluded paths (like `/token`, `/docs`, `/redoc`, `/openapi.json`) bypass authentication
   - All other paths require a valid authentication token
   - Unauthorized requests to `admin.html` are redirected to `index.html`

2. **Token Validation**:
   - Checks for a valid `Authorization: Bearer {token}` header
   - Validates the token signature
   - Verifies the token hasn't expired (with special handling for admin tokens)
   - Checks the user exists and isn't disabled
   - For long-lived tokens, validates against last refresh time to detect invalidated tokens

3. **Admin Token Handling**:
   - Admin tokens can be configured to never expire
   - Special logic handles expired admin tokens when `admin_token_never_expires` is set to true

4. **User Information**:
   - Adds user information and scopes to the request state for downstream handlers
   - Logs successful authentication with token type information
   - Includes token lifetime information in logs (short-lived vs. long-lived)

The middleware can be configured to exclude certain paths from authentication by modifying the `exclude_paths` list in the configuration. It supports both exact path matching and path prefixes for exclusion.

## Authentication Endpoints

### Token Generation (Short-lived)

Obtain a standard short-lived access token (30 minutes by default). This endpoint follows the standard OAuth2 password flow format.

**Endpoint:** `POST /token`

**Request Format:**
```
username=string&password=string&scope=string
```

**Notes:** 
- Request should use `application/x-www-form-urlencoded` format, not JSON
- The `scope` parameter is a space-separated string, not an array
- The endpoint is OAuth2 compatible and accepts `OAuth2PasswordRequestForm` data

**Response Format:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:3000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=secret&scope=models:read"
```

### Long-lived Token Generation

Obtain a long-lived access token valid for 6 months (or never expiring for admins).

**Endpoint:** `POST /refresh-token`

**Headers:**
- `Authorization: Bearer {token}` (Requires a valid token)

**Response Format:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_at": "string" // ISO format date or "never" for admin tokens
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:3000/refresh-token" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### User Information

Get information about the currently authenticated user.

**Endpoint:** `GET /users/me`

**Headers:**
- `Authorization: Bearer {token}`

**Response Format:**
```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false,
  "scopes": ["string"]
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:3000/users/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Information

Get detailed information about the current token.

**Endpoint:** `GET /token-info`

**Headers:**
- `Authorization: Bearer {token}`

**Response Format:**
```json
{
  "username": "string",
  "scopes": ["string"],
  "expiration": "string",  // ISO format date
  "is_expired": false,
  "is_admin": false,
  "is_long_lived": false,
  "never_expires": false
}
```

**cURL Example:**
```bash
curl -X GET "http://localhost:3000/token-info" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Change Password

Change the password for the currently authenticated user.

**Endpoint:** `POST /change-password`

**Headers:**
- `Authorization: Bearer {token}`

**Request Format:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Response Format:**
```json
{
  "message": "Password changed successfully"
}
```

**Status Codes:**
- `200 OK`: Password changed successfully
- `401 Unauthorized`: Current password is incorrect
- `404 Not Found`: User not found

**cURL Example:**
```bash
curl -X POST "http://localhost:3000/change-password" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"current_password": "oldpassword", "new_password": "newpassword"}'
```

## Admin API Endpoints

These endpoints are only accessible to users with the `admin` scope.

### List All Users

**Endpoint:** `GET /admin/users`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Response Format:**
```json
[
  {
    "username": "string",
    "email": "string",
    "full_name": "string",
    "disabled": false,
    "scopes": ["string"]
  }
]
```

### Get Specific User

**Endpoint:** `GET /admin/users/{username}`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Response Format:**
```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false,
  "scopes": ["string"]
}
```

### Create User

**Endpoint:** `POST /admin/users`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Request Format:**
```json
{
  "username": "string",
  "email": "string", // Optional
  "full_name": "string", // Optional
  "password": "string",
  "disabled": false, // Optional
  "scopes": ["string"] // Optional
}
```

**Response Format:**
```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false,
  "scopes": ["string"]
}
```

### Update User

**Endpoint:** `PUT /admin/users/{username}`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Request Format:**
```json
{
  "email": "string", // Optional
  "full_name": "string", // Optional
  "disabled": false, // Optional
  "scopes": ["string"] // Optional
}
```

**Response Format:**
```json
{
  "username": "string",
  "email": "string",
  "full_name": "string",
  "disabled": false,
  "scopes": ["string"]
}
```

### Delete User

**Endpoint:** `DELETE /admin/users/{username}`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Response:** 204 No Content

### Generate Token for User

Admins can generate tokens for any user in the system.

**Endpoint:** `POST /admin/token/{username}`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Request Format (Optional):**
```json
{
  "scopes": ["string"] // Optional - If not provided, all user's scopes will be used
}
```

**Response Format:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_at": "string" // ISO format date or "never" for admin tokens
}
```

### Get User Token Status

**Endpoint:** `GET /admin/tokens/{username}`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Response Format:**
```json
{
  "username": "string",
  "last_refresh": "string", // ISO format date
  "next_refresh_required": "string" // ISO format date or "never" for admin users
}
```

### List All Token Status

**Endpoint:** `GET /admin/tokens`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Response Format:**
```json
[
  {
    "username": "string",
    "last_refresh": "string", // ISO format date
    "next_refresh_required": "string" // ISO format date or "never" for admin users
  }
]
```

### Revoke User Token

**Endpoint:** `DELETE /admin/token/{username}/revoke`

**Headers:**
- `Authorization: Bearer {token}` (Requires admin token)

**Response:** 204 No Content

**Description:**
This endpoint revokes a user's long-lived token by removing their `last_token_refresh` timestamp. This forces the user to request a new token through the standard authentication flow.

## Database Schema

The authentication system uses a PostgreSQL database with the following main schema:

### Users Table

```sql
CREATE TABLE myopenaiapi_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE,
    full_name VARCHAR,
    disabled BOOLEAN DEFAULT FALSE,
    hashed_password VARCHAR NOT NULL,
    scopes VARCHAR[] DEFAULT '{}',
    last_token_refresh VARCHAR
);
```

Key fields explained:
- `username`: Unique identifier for the user
- `email`: Optional email address 
- `full_name`: Optional full name
- `disabled`: If true, the user's access is revoked
- `hashed_password`: Bcrypt-hashed password (using bcrypt scheme)
- `scopes`: Array of permission scopes granted to the user
- `last_token_refresh`: ISO format datetime of the last token refresh

### Logs Table (when logging to database is enabled)

```sql
CREATE TABLE myopenaiapi_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    level VARCHAR(10) NOT NULL,
    logger VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    username VARCHAR(100),
    request_path VARCHAR(2000),
    ip_address VARCHAR(50)
);
```

This table stores authentication events and can be used for security auditing and monitoring. The table prefix (`myopenaiapi`) is configurable through the logging configuration.

## Token Types and Lifetimes

### Short-lived Tokens
- Used for temporary access (interactive sessions, testing)
- Default lifetime: 30 minutes (configurable via `access_token_expire_minutes`)
- Obtained through standard OAuth2 flow (`/token` endpoint)

### Long-lived Tokens
- Used for persistent API access
- Default lifetime: 180 days (6 months) (configurable via `user_token_expire_days`)
- Obtained through `/refresh-token` endpoint
- Regular users must refresh their tokens before expiration
- Token refresh history is tracked to invalidate old tokens

### Admin Tokens
- Can have unlimited lifetime if `admin_token_never_expires` is set to true
- Special privileges for user management
- Can generate tokens for other users
- Tokens can be revoked by an administrator

## Scopes

Scopes control access to specific API features. Common scopes include:

- `admin`: Full administrative access
- `models:read`: Access to read model information
- `models:write`: Access to modify models
- `chat:read`: Access to use chat functionality
- `chat:write`: Access to modify chat settings
- `embeddings:read`: Access to embeddings functionality

A user with multiple scopes can perform actions allowed by any of their scopes. For example, a user with both `models:read` and `chat:read` can both read model information and use chat functionality.

When requesting a token, you can optionally specify which scopes you want to include in the token. The server will only include scopes that the user actually has permission to use.

Example token request with specific scopes:
```bash
curl -X POST "http://localhost:3000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user1&password=secret&scope=models:read chat:read"
```

## Authentication Flow

1. **Initial Authentication**:
   - Client submits username/password to `/token` endpoint
   - Server validates credentials and returns a short-lived token

2. **Long-lived Access**:
   - Client uses valid token to request a long-lived token via `/refresh-token`
   - Server validates the token and returns a long-lived token

3. **API Access**:
   - Client includes token in Authorization header for all protected API calls
   - Server validates the token and grants access based on the token's scopes

4. **Token Management**:
   - Regular users refresh their tokens before expiration
   - Admins can generate tokens for any user as needed

## Logging and Auditing

The authentication system includes comprehensive logging to track authentication events through a centralized logging system:

```yaml
logging:
  level: "INFO"  # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  use_database: true  # Whether to log to the database
  async_logging: true  # Use asynchronous logging for better performance
  table_prefix: "myopenaiapi"  # Prefix for log tables in the database
  log_retention_days: 30  # How many days to keep logs in the database
  console:
    enabled: true  # Always log to console as a fallback
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  components:
    auth: "INFO"
    database: "INFO"
    middleware: "INFO"
    controller: "WARNING"
```

The system logs important security events including:
- Failed login attempts
- Token validation failures
- Token generation events (including token type: short-lived vs. long-lived)
- Admin operations on user accounts
- Token refresh events
- Token revocation events
- Authentication middleware validations and rejections

When `use_database` is enabled, authentication logs are stored in the database for auditing purposes, with automatic cleanup based on the `log_retention_days` setting. The logs also capture context information like request paths and usernames where available.

## Security Considerations

1. Always use HTTPS in production
2. Change the default secret key in production
3. Restrict admin access to trusted users only
4. Regularly audit user accounts and token usage
5. Consider shortening token lifetimes for higher security requirements