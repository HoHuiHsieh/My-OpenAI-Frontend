
/**
 * Usage Statistics API
 * This module provides endpoints for retrieving usage statistics for users and admins.
 * It includes methods to get usage data by period, specific user usage, all users' usage,
 * admin summaries, and recent activity.
 */
import api from './api';

interface DailyUsage {
  date: string; // ISO date string
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
}
interface WeeklyUsage {
  week_start: string; // ISO date string
  week_end: string; // ISO date string
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
}
interface MonthlyUsage {
  month: number; // 1-12
  year: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  request_count: number;
}
interface UserDetailedUsage {
  username: string;
  daily_usage: DailyUsage[];
  weekly_usage: WeeklyUsage[];
  monthly_usage: MonthlyUsage[];
}
interface AllUsersUsage {
  daily_usage: DailyUsage[];
  weekly_usage: WeeklyUsage[];
  monthly_usage: MonthlyUsage[];
  by_user: Record<string, UserDetailedUsage>;
}
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

// Usage Statistics API endpoints
export const usageApi = {
  // User endpoints
  getUserUsageByPeriod: (period: 'day' | 'week' | 'month' | 'all', params?: {
    days?: number;
    weeks?: number;
    months?: number;
  }): Promise<UserDetailedUsage> => {
    return api.get(`/usage/${period}`, { params });
  },

  // Admin endpoints
  getSpecificUserUsage: (username: string, period: 'day' | 'week' | 'month' | 'all', params?: {
    days?: number;
    weeks?: number;
    months?: number;
  }): Promise<UserDetailedUsage> => {
    return api.get(`/admin/usage/user/${username}/${period}`, { params });
  },

  // Get usage statistics for all users by period
  getAllUsersUsage: (period: 'day' | 'week' | 'month' | 'all', params?: {
    days?: number;
    weeks?: number;
    months?: number;
  }): Promise<AllUsersUsage> => {
    return api.get(`/admin/usage/all/${period}`, { params });
  },

  // Admin summary
  getAdminSummary: (): Promise<UsageSummary> => {
    return api.get('/admin/usage/summary');
  },

  // Get a list of API requests made by a specific user.
  getUserApiRequestsByPeriod: (
    username: string,
    period: 'day' | 'week' | 'month' | 'all',
    params?: { limit?: number }
  ): Promise<UsageEntry[]> => {
    return api.get(`/admin/usage/list/user/${username}/${period}`, { params });
  },
};
