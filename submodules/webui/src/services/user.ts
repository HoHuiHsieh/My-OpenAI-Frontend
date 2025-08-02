/**
 * Admin User Management API Service
 * This module provides endpoints for managing users in the application.
 * It includes functionality for listing users, retrieving user details,
 * creating new users, updating existing users, deleting users, and accessing
 * usage statistics. It is intended for use by administrators to manage 
 * user accounts, permissions, and monitor system usage.
 */
import api from './api';

export interface AccessToken {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  fullname: string;
  active: boolean;
  scopes: string[];
  hashed_password: string;
  created_at: string; // ISO format date
  updated_at?: string; // Optional ISO format date
}


export interface UserCreate {
  username: string;
  password: string;
  email: string;
  fullname: string;
  active?: boolean; // Default to true if not provided
  scopes?: string[]; // Optional scopes array
}

export interface UserUpdate {
  email?: string;
  fullname?: string;
  password?: string;
  active?: boolean; // Optional, can be used to disable/enable user
  scopes?: string[]; // Optional scopes array
}

export interface UserResponse {
  id: number; // Unique identifier for the user
  username: string;
  email: string;
  fullname: string;
  active: boolean; // User account status
  scopes: string[]; // User permission scopes
  hashed_password: string;
  created_at: string; // ISO format date
  updated_at?: string; // Optional ISO format date
}


// Admin User Management API endpoints
export const userApi = {
  // Web session management
  login: (username: string, password: string, scope: string = ""): Promise<AccessToken> => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('scope', scope);
    return api.post('/user/login', formData);
  },

  refreshToken: (
    refresh_token: string,
  ): Promise<AccessToken> => {
    return api.post('/auth/refresh', { refresh_token });
  },

  // User Management (user endpoints)
  getCurrentUser: (
    accessToken: string
  ): Promise<User> => {
    return api.get('/user/', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  updateCurrentUser: (userUpdate: UserUpdate, accessToken: string): Promise<User> => {
    return api.put('/user/', userUpdate, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  getScopes: (accessToken: string): Promise<string[]> => {
    return api.get('/user/scopes', {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },

  // User Management (admin endpoints)
  listUsers: (skip: number = 0, limit: number = 100, accessToken: string): Promise<UserResponse[]> => {
    return api.get('/admin/users', {
      params: { skip, limit },
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      }
    });
  },

  getUser: (username: string, accessToken: string): Promise<UserResponse> => {
    return api.get(`/admin/users/${username}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      }
    });
  },

  createUser: (userData: UserCreate, accessToken: string): Promise<UserResponse> => {
    return api.post('/admin/users', userData, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      }
    });
  },

  updateUser: (username: string, userUpdate: UserUpdate, accessToken: string): Promise<UserResponse> => {
    return api.put(`/admin/users/${username}`, userUpdate, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      }
    });
  },

  deleteUser: (
    username: string,
    accessToken: string
  ): Promise<{ detail: string }> => {
    return api.delete(`/admin/users/${username}`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
      },
    });
  },
};

