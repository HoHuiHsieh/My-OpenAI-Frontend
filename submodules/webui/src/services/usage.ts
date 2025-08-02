
/**
 * Usage Statistics API
 * This module provides endpoints for retrieving usage statistics for users and admins.
 * It includes methods to get usage data by period, specific user usage, all users' usage,
 * admin summaries, and recent activity. Matches the API endpoints defined in src/usage/routes.py.
 */
import api from './api';

interface UsageSummary {
  total_users: number;
  active_users_today: number;
  requests_today: number;
  tokens_today: number;
}

interface UsageEntry {
  id?: number;
  timestamp: string; // ISO date string
  api_type: string;
  user_id: string;
  model: string;
  request_id?: string;
  prompt_tokens: number;
  completion_tokens?: number;
  total_tokens: number;
  input_count?: number;
  extra_data?: Record<string, any>;
}

interface UsageResponse {
  time_period: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  request_count: number;
  model?: string; // Optional model name if filtered
  start_date?: string; // ISO format date
  end_date?: string; // ISO format date
  user_count?: number; // For admin reports
}


// Usage Statistics API endpoints
export const usageApi = {
  // User endpoints - for authenticated users to get their own usage stats
  getModels: (accessToken: string): Promise<string[]> => {
    return api.get('/usage/models', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  getUserUsage: (
    time: 'day' | 'week' | 'month' | 'all' = 'all',
    period: number = 7,
    model: string = 'all',
    accessToken: string
  ): Promise<UsageResponse[]> => {
    return api.get(`/usage/${time}`, {
      params: { period, model },
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  // Admin endpoints - require admin authentication
  getSpecificUserUsage: (
    username: string,
    time: 'day' | 'week' | 'month' | 'all' = 'all',
    period: number = 7,
    model: string = 'all',
    accessToken: string
  ): Promise<UsageResponse[]> => {
    return api.get(`/admin/usage/user/${username}/${time}`, {
      params: { period, model },
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  getAllUsersUsage: (
    time: 'day' | 'week' | 'month' | 'all' = 'all',
    period: number = 7,
    model: string = 'all',
    accessToken: string
  ): Promise<UsageResponse[]> => {
    return api.get(`/admin/usage/all/${time}`, {
      params: { period, model },
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  getUsageSummary: (accessToken: string): Promise<UsageSummary> => {
    return api.get('/admin/usage/summary', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  getUserRequestList: (
    username: string,
    period: string,
    limit: number = 100,
    accessToken: string
  ): Promise<UsageEntry[]> => {
    return api.get(`/admin/usage/list/user/${username}/${period}`, {
      params: { limit },
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  }
};
