/**
 * Access Management API Service
 * This module provides endpoints for managing access tokens in the application.
 * It includes functionality for refreshing tokens, generating tokens for users,
 * checking token status, and revoking tokens.
 * It is used by both regular users and administrators to manage their access tokens.
 */

import api from './api';


export interface TokenRequest {
    token: string;
}
interface AccessToken {
    access_token: string;
    token_type: string;
    expires_at?: string; // ISO format date
}
export interface TokenInfo {
    username: string;
    type: string;
    scopes: string[];
    expires_at?: string; // ISO format date
    issued_at: string; // ISO format date
    active: boolean;
}

// Access API endpoints
export const accessApi = {
    refreshToken: (): Promise<AccessToken> => {
        return api.post('/access/refresh');
    },

    getTokenStatus: (body: TokenRequest): Promise<TokenInfo> => {
        return api.post('/access/info', body);
    },
}