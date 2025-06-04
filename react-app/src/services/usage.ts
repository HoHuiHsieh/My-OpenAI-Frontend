
/**
 * Usage Statistics API
 * This module provides endpoints for retrieving usage statistics for users and admins.
 * It includes methods to get usage data by period, specific user usage, all users' usage,
 * admin summaries, and recent activity.
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
  time_period: string; // 'day', 'week', 'month', etc.
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  request_count: number;
}


// Usage Statistics API endpoints
export const usageApi = {
  // User endpoints
  getUserUsageByPeriod: (
    time: 'day' | 'week' | 'month' | 'all',
    period: Number = 7,
    model: string = 'all',
  ): Promise<UsageResponse[]> => {
    return api.get(`/usage/${time}`, { params: { period, model } });
  },

  // Admin endpoints
  getSpecificUserUsage: (
    username: string,
    time: 'day' | 'week' | 'month' | 'all' = 'day',
    period: Number = 7,
    model: string = 'all',
  ): Promise<UsageResponse[]> => {
    return api.get(`/admin/usage/user/${username}/${time}`, { params: { period, model } });
  },

  // Get usage statistics for all users by period
  getAllUsersUsage: (
    time: 'day' | 'week' | 'month' | 'all' = 'day',
    period: Number = 7,
    model: string = 'all',
  ): Promise<UsageResponse[]> => {
    return api.get(`/admin/usage/all/${time}`, { params: { period, model } });
  },

  // Admin summary
  getAdminSummary: (): Promise<UsageSummary> => {
    return api.get('/admin/usage/summary');
  },

  // Get a list of API requests made by a specific user.
  getUserApiRequestsByPeriod: (
    username: string,
    period: 'day' | 'week' | 'month' | 'all',
    limit: Number = 100,
  ): Promise<UsageEntry[]> => {
    return api.get(`/admin/usage/list/user/${username}/${period}`, { params: { limit } });
  },
};
