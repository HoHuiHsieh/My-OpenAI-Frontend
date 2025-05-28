# Usage Statistics API

## Overview

The Usage Statistics API provides endpoints for retrieving API usage statistics organized by different time periods. Regular users can access their own usage data, while administrators can retrieve statistics for all users or specific users, as well as dashboard summary information and recent activity logs.

## Features

- Get usage statistics grouped by day, week, or month
- Track prompt tokens, completion tokens, and total tokens used
- View request counts and distribution by model and API type
- User-specific statistics for regular users
- System-wide statistics for administrators
- Admin dashboard with summary statistics and recent activity monitoring
- Time-based filtering with configurable lookback periods

## API Endpoints

### User Endpoints

These endpoints are available to all authenticated users:

- **GET /usage/me/{period}** - Get current user's usage statistics
  - Parameters:
    - `period`: Time period to group by (`day`, `week`, `month`)
    - `num_periods` (optional): Number of periods to include (default: 30)
    - `api_type` (optional): Filter by API type (e.g., 'chat', 'embeddings')
    - `model` (optional): Filter by model name (e.g., 'gpt-4', 'llama-7b')
  - Example: `/usage/me/day?num_periods=7&api_type=chat` (gets daily chat usage for the last 7 days)
  - Authentication: Required

### Admin Endpoints

These endpoints are only available to admin users:

- **GET /usage/admin/user/{username}/{period}** - Get specific user's usage statistics by username
  - Parameters:
    - `username`: Username to get statistics for
    - `period`: Time period to group by (`day`, `week`, `month`)
    - `num_periods` (optional): Number of periods to include (default: 30)
    - `api_type` (optional): Filter by API type (e.g., 'chat', 'embeddings')
    - `model` (optional): Filter by model name (e.g., 'gpt-4', 'llama-7b')
  - Example: `/usage/admin/user/john.doe/month?num_periods=12&model=gpt-4`
  - Authentication: Admin only (requires "admin" scope)

- **GET /usage/admin/all/{period}** - Get all users' usage statistics
  - Parameters:
    - `period`: Time period to group by (`day`, `week`, `month`)
    - `num_periods` (optional): Number of periods to include (default: 30)
    - `username` (optional): Filter by specific username
    - `api_type` (optional): Filter by API type (e.g., 'chat', 'embeddings')
    - `model` (optional): Filter by model name (e.g., 'gpt-4', 'llama-7b')
  - Example: `/usage/admin/all/month?username=john.doe`
  - Authentication: Admin only (requires "admin" scope)

- **GET /usage/admin/summary** - Get summary statistics for the admin dashboard
  - Returns dashboard summary information including total users, active users today, API requests today, and total tokens used today
  - No parameters required
  - Authentication: Admin only (requires "admin" scope)

- **GET /usage/admin/recent** - Get recent user activity
  - Returns a list of recent user activities with timestamps, usernames, actions, and details
  - No parameters required
  - Authentication: Admin only (requires "admin" scope)

## Response Format

### User Statistics Response

```json
[
  {
    "period_start": "2025-05-01T00:00:00",
    "period_end": "2025-05-02T00:00:00",
    "prompt_tokens": 5000,
    "completion_tokens": 2500,
    "total_tokens": 7500,
    "request_count": 100,
    "models": {
      "gpt-4": 5000,
      "gpt-3.5-turbo": 2500
    },
    "api_types": {
      "chat_completion": 6000,
      "embeddings": 1500
    }
  },
  // Additional periods...
]
```

### Admin All Users Response

```json
{
  "users": [
    {
      "user_id": "user1",
      "statistics": [
        // Array of usage statistics as shown above
      ]
    },
    {
      "user_id": "user2",
      "statistics": [
        // Array of usage statistics
      ]
    }
  ],
  "total_prompt_tokens": 50000,
  "total_completion_tokens": 25000,
  "total_tokens": 75000,
  "total_request_count": 500
}
```

### Admin Summary Response

```json
{
  "total_users": 50,
  "active_users_today": 15,
  "api_requests_today": 1200,
  "total_tokens_today": 75000
}
```

### Recent Activity Response

```json
[
  {
    "timestamp": "2025-05-28T15:45:30.123456",
    "username": "john.doe",
    "action": "chat_completion",
    "details": "Model: gpt-4"
  },
  {
    "timestamp": "2025-05-28T15:44:12.654321",
    "username": "jane.smith",
    "action": "embeddings",
    "details": "API request"
  }
]
```

## Integration With UsageLogger

The Usage Statistics API integrates seamlessly with the UsageLogger component:

- `UsageLogger` records usage data in the database
- The statistics API queries and aggregates this usage data
- Both components share the same database configuration
- The API uses table prefix from the logging configuration to locate usage data
- Date-based queries allow efficient analysis across different time periods

## Usage Examples

### JavaScript/Fetch Example

```javascript
// Get user's daily usage statistics for the last 7 days
async function getUserDailyStats() {
  const response = await fetch('/usage/me/day?num_periods=7', {
    headers: {
      'Authorization': 'Bearer ' + accessToken
    }
  });
  
  if (response.ok) {
    const stats = await response.json();
    console.log('Daily usage stats:', stats);
    return stats;
  } else {
    console.error('Failed to get usage stats:', await response.text());
  }
}
```

### Python Example

```python
# Get all users' monthly statistics (admin only)
import requests

def get_all_users_monthly_stats(admin_token):
    response = requests.get(
        'http://localhost:3000/usage/admin/all/month',
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get stats: {response.text}")
```

```python
# Get admin dashboard summary statistics
import requests

def get_admin_summary(admin_token):
    response = requests.get(
        'http://localhost:3000/usage/admin/summary',
        headers={'Authorization': f'Bearer {admin_token}'}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get summary stats: {response.text}")
```

## Testing

A test script (`test_usage_stats.py`) is provided to demonstrate how to use the API. You can run it to verify that the statistics API is working correctly:

```bash
python test_usage_stats.py
```

Make sure to update the credentials in the script before running it.
