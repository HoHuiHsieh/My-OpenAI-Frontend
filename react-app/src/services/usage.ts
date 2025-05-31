
/**
 * Usage Statistics API
 * This module provides endpoints for retrieving usage statistics for users and admins.
 * It includes methods to get usage data by period, specific user usage, all users' usage,
 * admin summaries, and recent activity.
 */
import api from './api';

interface UsageStatistics {
  period_start: string; // ISO format date
  period_end: string; // ISO format date
  prompt_tokens: number;
  completion_tokens?: number; // Optional, can be null
  total_tokens: number;
  request_count: number;
  models?: Record<string, number>; // Model name -> token count
  api_types?: Record<string, number>; // API type -> token count
}

interface AllUsersStatistics {
  users: UsageStatistics[];
  total_prompt_tokens: number;
  total_completion_tokens?: number; // Optional, can be null
  total_tokens: number;
  total_request_count: number;
}

interface StatisticsSummary {
  total_users: number;
  active_users_today: number;
  api_requests_today: number;
  total_tokens_today: number;
}

interface RecentActivity {
  timestamp: string; // ISO format date
  username: string;
  action: string; // e.g., "login", "token refresh", etc.
  details?: string; // Optional, additional details about the action
}

// Usage Statistics API endpoints
export const usageApi = {
  // User endpoints
  getUserUsageByPeriod: (period: 'day' | 'week' | 'month', params?: {
    num_periods?: number;
    api_type?: string;
    model?: string;
  }): Promise<UsageStatistics[]> => {
    return api.get(`/usage/me/${period}`, { params });
  },

  // Admin endpoints
  getSpecificUserUsage: (username: string, period: 'day' | 'week' | 'month', params?: {
    num_periods?: number;
    api_type?: string;
    model?: string;
  }): Promise<UsageStatistics[]> => {
    return api.get(`/usage/admin/user/${username}/${period}`, { params });
  },

  getAllUsersUsage: (period: 'day' | 'week' | 'month', params?: {
    num_periods?: number;
    username?: string;
    api_type?: string;
    model?: string;
  }): Promise<AllUsersStatistics> => {
    return api.get(`/usage/admin/all/${period}`, { params });
  },

  getAdminSummary: (): Promise<StatisticsSummary> => {
    return api.get('/usage/admin/summary');
  },

  getRecentActivity: (): Promise<RecentActivity> => {
    return api.get('/usage/admin/recent');
  },
};
