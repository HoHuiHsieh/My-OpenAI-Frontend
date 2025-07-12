/**
 * Admin User Management API Service
 * This module provides endpoints for managing users in the application.
 * It includes functionality for listing users, retrieving user details,
 * creating new users, updating existing users, and deleting users.
 * It is intended for use by administrators to manage user accounts and permissions.
 */
import api from './api';


interface UserCreate {
  username: string;
  password: string;
  email?: string;
  full_name?: string;
  disabled?: boolean; // Default to false if not provided
}
interface UserUpdate {
  email?: string;
  full_name?: string;
  password?: string;
  disabled?: boolean; // Optional, can be used to disable/enable user
}
interface UserResponse {
  username: string;
  email?: string;
  full_name?: string;
  disabled: boolean; // Default to false if not provided
  scopes: string[]; // Added scopes property
  created_at: string; // ISO format date
  updated_at: string; // ISO format date
}
interface AccessTokenCreateData {
  scopes: string[]; // List of scopes for the access token
  expires_days?: number; // Optional, number of days until expiration
  never_expires?: boolean; // Optional, if true, token will not expire
}
interface AccessTokenResponse {
  id: number; // Unique identifier for the access token
  username: string; // Username of the user associated with the token
  scopes: string[]; // List of scopes granted by the token
  expires_at?: string; // Optional, ISO format date of expiration
  revoked: boolean; // Indicates if the token has been revoked
  created_at: string; // ISO format date of creation
}

// New interface for token creation response
interface AccessTokenCreateResponse {
  access_token: string; // The actual token string
  token_type: string; // Always "bearer"
  expires_at?: string; // Optional, ISO format date of expiration
  scopes: string[]; // List of scopes granted by the token
}

// Admin User Management API endpoints
export const adminApi = {
  listUsers: (skip: number = 0, limit: number = 100): Promise<UserResponse[]> => {
    return api.get('/admin/users', { params: { skip, limit } });
  },

  getUser: (username: string): Promise<UserResponse> => {
    return api.get(`/admin/users/${username}`);
  },

  createUser: (userData: UserCreate): Promise<UserResponse> => {
    return api.post('/admin/users', userData);
  },

  updateUser: (username: string, userUpdate: UserUpdate): Promise<UserResponse> => {
    return api.put(`/admin/users/${username}`, userUpdate);
  },

  deleteUser: (username: string): Promise<void> => {
    return api.delete(`/admin/users/${username}`);
  },

  listAccessTokens: (): Promise<AccessTokenResponse[]> => {
    return api.get(`/admin/access`);
  },

  createAccessToken: (username: string, tokenData: AccessTokenCreateData): Promise<AccessTokenCreateResponse> => {
    return api.post(`/admin/access/${username}`, tokenData);
  },

  deleteAccessToken: (username: string, token_id: number): Promise<void> => {
    return api.delete(`/admin/access/${username}`, { params: { token_id } });
  },

  getAvailableScopes: (): Promise<string[]> => {
    return api.get(`/admin/scopes`);
  }
};

