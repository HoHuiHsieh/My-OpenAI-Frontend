# OAuth2 Authentication API Documentation

## Overview

This document provides detailed information about the OAuth2 authentication service implemented in the My OpenAI Frontend API. The authentication system supports token-based authentication with different token lifetimes, role-based access control through scopes, comprehensive user management, and token verification.

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
  "token_type": "short_lived",  // "short_lived" or "long_lived"
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

### API Access Management

These endpoints manage API access tokens with fine-grained scope control.

#### Refresh Access Token

Create a new API access token for the authenticated user.

**Endpoint:** `POST /access/refresh`

**Headers:**
- `Authorization: Bearer {token}`

**Response Format:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_at": "string" // ISO format date
}
```

**cURL Example:**
```bash
curl -X POST "http://localhost:3000/access/refresh" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### Token Information

Get detailed information about a specific token by providing the token in the request.

**Endpoint:** `POST /access/info`

**Headers:**
- `Authorization: Bearer {token}` (For authentication)

**Request Format:**
```json
{
  "token": "string" // The token to verify, NOT the authentication token
}
```

**Response Format:**
```json
{
  "username": "string",
  "type": "string",
  "scopes": ["string"],
  "expires_at": "string", // ISO format date
  "issued_at": "string", // ISO format date
  "active": boolean // Whether the token is active (not expired and not revoked)
}
```

**Note:** This endpoint checks if the provided token has been revoked in the database.

**cURL Example:**
```bash
curl -X POST "http://localhost:3000/access/info" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
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
  "last_refresh": "string", // ISO format date of last token refresh
  "last_login": "string", // ISO format date of last login
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
    "last_refresh": "string", // ISO format date of last token refresh
    "last_login": "string", // ISO format date of last login
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
This endpoint revokes a user's long-lived token by removing their `last_token_refresh` timestamp and setting the `revoked` flag to true on their associated tokens in the database. This forces the user to request a new token through the standard authentication flow.

All token verification endpoints will check if a token has been revoked before allowing access. The system maintains a record of revoked tokens to prevent their reuse, even if the JWT itself has not expired.

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
    last_token_refresh VARCHAR,
    last_login VARCHAR
);
```

Key fields explained:
- `username`: Unique identifier for the user
- `email`: Optional email address 
- `full_name`: Optional full name
- `disabled`: If true, the user's access is revoked
- `hashed_password`: Bcrypt-hashed password (using bcrypt scheme)
- `scopes`: Array of permission scopes granted to the user
- `last_token_refresh`: ISO format datetime of the last long-lived token refresh
- `last_login`: ISO format datetime of the last login with short-lived token

### Tokens Table

```sql
CREATE TABLE myopenaiapi_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR UNIQUE NOT NULL,
    token_type VARCHAR NOT NULL,
    user_id INTEGER REFERENCES myopenaiapi_users(id) ON DELETE CASCADE,
    scopes JSONB NOT NULL DEFAULT '[]',
    token_metadata JSONB,
    expires_at TIMESTAMP,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Key fields explained:
- `id`: Unique identifier for the token
- `token`: The actual JWT token value (hashed for security)
- `token_type`: Type of token (either "session" or "access")
- `user_id`: Foreign key reference to the user who owns this token
- `scopes`: JSON array of the permission scopes granted in this token
- `token_metadata`: Additional metadata about the token (creation reason, admin who created it, etc.)
- `expires_at`: When the token expires (null for never-expiring tokens)
- `revoked`: Boolean flag indicating if the token has been explicitly revoked
- `created_at`: When the token was created

For security purposes:
- When a new access token is generated for a user, all their previous access tokens are automatically revoked
- This "one active token per user" model helps prevent security issues from multiple active tokens
- Tokens can be explicitly revoked via the admin interface or API
- The system checks if a token has been revoked on each authenticated request

Key fields explained:
- `token`: The actual token value (JWT)
- `token_type`: Type of token ("session" or "access")
- `user_id`: Foreign key reference to the user who owns the token
- `scopes`: JSON array of permission scopes for this specific token
- `token_metadata`: Additional JSON metadata about the token
- `expires_at`: Expiration timestamp for the token
- `revoked`: Flag indicating if the token has been explicitly revoked

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
- When generated, updates the user's `last_login` timestamp
- Works with authentication middleware like long-lived tokens

### Long-lived Tokens
- Used for persistent API access
- Default lifetime: 180 days (6 months) (configurable via `user_token_expire_days`)
- Obtained through `/refresh-token` endpoint
- Regular users must refresh their tokens before expiration
- Token refresh history is tracked to invalidate old tokens
- When refreshed, updates the user's `last_token_refresh` timestamp

### Admin Tokens
- Can have unlimited lifetime if `admin_token_never_expires` is set to true
- Special privileges for user management
- Can generate tokens for other users
- Tokens can be revoked by an administrator

### Token Revocation
- Any token can be explicitly revoked even before its expiration
- Revoked tokens are marked in the database with a `revoked` flag
- The system checks if tokens are revoked during verification
- Token revocation is permanent and requires generating a new token
- Administrators can revoke any user's tokens
- The `/access/info` endpoint can verify if a token has been revoked

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
6. Promptly revoke tokens when they are no longer needed or if a security breach is suspected
7. Use the `/access/info` endpoint to verify token status and validity
8. Implement proper error handling for token revocation scenarios
9. Regularly monitor and clean up expired and revoked tokens
10. Be aware that the system automatically revokes all previous access tokens for a user when a new token is generated, maintaining a one-active-token-per-user security model
10. Consider implementing rate limiting for token verification and generation requests