/**
 * Access Management API Service
 * This module provides endpoints for managing access tokens in the application.
 * It includes functionality for refreshing tokens, generating tokens for users,
 * checking token status, and revoking tokens.
 * It is used by both regular users and administrators to manage their access tokens.
 */

import api from './api';


export interface ApiKey {
    apiKey: string;
    expires_in: number;
}

export interface ApiKeyInfo {
    user_id: number;
    scopes: string[];
    exp: string; // ISO format date
}

// Access API endpoints
export const apiKeyApi = {
    refreshApiKey: (accessToken: string): Promise<ApiKey> => {
        return api.post('/apikey', {}, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
        });
    },

    getApiKeyStatus: (accessToken: string): Promise<ApiKeyInfo> => {
        return api.get('/apikey', {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
        });
    },
}