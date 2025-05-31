import React, { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { sessionApi } from '@/services/session';
import { accessApi, TokenInfo } from '@/services/access';

// Define interfaces for user and authentication context
interface UserScopes {
  [scope: string]: boolean;
}

interface User {
  username: string;
  email?: string;
  full_name?: string;
  isAdmin: boolean;
  token: string;
  scopes: string[];
  tokenExpiration?: string | null;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (access_token: string) => Promise<void>;
  logout: () => void;
  hasScope: (scope: string) => boolean;
  getTokenInfo: () => Promise<TokenInfo>;
}

// Create the authentication context
const AuthContext = createContext<AuthContextType | null>(null);

// Hook to use the authentication context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

// Constants
const AUTH_USER_STORAGE_KEY = 'authUser';

// AuthProvider component to manage authentication state
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  // Load user from localStorage on app initialization
  useEffect(() => {
    const storedUser = localStorage.getItem(AUTH_USER_STORAGE_KEY);
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        setUser(parsedUser);

        // Validate token if available
        if (parsedUser.token) {
          // Check token status
          accessApi.getTokenStatus({ token: parsedUser.token })
            .then(info => {
              if (!info.active) {
                logout();
              }
            })
            .catch(() => logout()); // Assume invalid token if check fails
        }
      } catch (error) {
        console.error('Failed to parse stored user data', error);
        localStorage.removeItem(AUTH_USER_STORAGE_KEY);
      }
    }
  }, []);

  // Check if the user has a specific scope
  /**
   * Checks if the authenticated user has a specific scope.
   * @param scope - The scope to check.
   * @returns True if the user has the scope, false otherwise.
   */
  const hasScope = (scope: string): boolean => user?.scopes?.includes(scope) || false;

  // Handle user login
  /**
   * Logs in the user by sending credentials to the server and retrieving an access token.
   * Fetches user information and stores it in localStorage.
   * @param access_token - The access token to use for authentication.
   * @throws Error if login fails due to invalid credentials or server issues.
   */
  const login = async (access_token: string) => {
    try {

      if (access_token) {
        // Store the access token in localStorage
        const tempUser = {
          username: "",
          email: "",
          full_name: "",
          isAdmin: "",
          token: access_token,
          scopes: "",
        };
        localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(tempUser));

        // Get user info
        const userInfo = await sessionApi.getUserInfo();
        const newUser = {
          username: userInfo.username,
          email: userInfo.email,
          full_name: userInfo.full_name,
          isAdmin: userInfo.scopes?.includes('admin') || false,
          token: access_token,
          scopes: userInfo.scopes || [],
        };
        localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(newUser));
        setUser(newUser);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw new Error('Invalid credentials or server error');
    }
  };

  // Handle user logout
  /**
   * Logs out the user by clearing the authentication state and removing user data from localStorage.
   */
  const logout = () => {
    localStorage.removeItem(AUTH_USER_STORAGE_KEY);
    setUser(null);
  };

  // Fetch token information
  /**
   * Retrieves information about the user's token from the server.
   * @returns Token information including expiration status.
   */
  const getTokenInfo = async (): Promise<TokenInfo> => {
    if (!user?.token) throw new Error('No active session');

    try {
      return await accessApi.getTokenStatus({ token: user.token });
    } catch (error) {
      console.error('Get token info error:', error);
      throw new Error('Failed to get token information');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        logout,
        hasScope,
        getTokenInfo,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export default AuthProvider;
