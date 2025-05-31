/**
 *  */
import { headers } from 'next/headers';
import api from './api';

interface Token {
  access_token: string;
  token_type: string;
}

interface User {
  username: string;
  email?: string;
  full_name?: string;
  disabled?: boolean;
  scopes?: string[];
}

interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}


// User Management API endpoints
export const sessionApi = {

  login: (username: string, password: string): Promise<Token> => {
    const body = new FormData();
    body.append('username', username);
    body.append('password', password);
    return api.post('/session', body)
  },

  getUserInfo: (): Promise<User> => {
    return api.get('/session/user');
  },

  changePassword: (body: PasswordChangeRequest): Promise<void> => {
    return api.post(`/session/changePwd`, body);
  }

};

