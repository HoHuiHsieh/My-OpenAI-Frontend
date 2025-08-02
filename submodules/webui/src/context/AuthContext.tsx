
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { userApi, AccessToken, User } from '@/services/user';
import { log } from 'console';


interface AuthContextProps {
  user: User;
  isAuthenticated: boolean;
  accessToken: string;
  setAccessToken: (token: string) => void;
  login: (response: AccessToken) => void;
  logout: () => void;
}

// Create a context for the Auth
const AuthContext = createContext<AuthContextProps | undefined>(undefined);

/**
 * Custom hook to use the AuthContext.
 * It provides access to the Auth's position and zoom level.
 * This hook should be used within a AuthProvider component.
 * @see useAuthContext
 * @throws Error if used outside of AuthProvider
 * @returns 
 */
export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within a AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * AuthProvider component that provides Auth context to its children.
 * It manages the user's current position and zoom level.
 * The position is updated based on the user's geolocation.
 * The position is initialized to a default value and updated every 5 seconds.
 * @param param0 
 * @returns 
 */
export function AuthProvider({ children }: AuthProviderProps) {
  // Access token state
  const [accessToken, setAccessToken] = useState<string>('');
  const isAuthenticated = !!accessToken; // Check if user is authenticated based on access token
  const [user, setUser] = useState<User>({
    id: 0,
    username: '',
    email: '',
    fullname: '',
    active: false,
    scopes: [],
    hashed_password: '',
    created_at: '',
  }); // User state to store user details

  // Function to handle token refresh
  // This function is called to refresh the access token using the refresh token
  const handleRefreshToken = async (): Promise<AccessToken | void> => {
    // Get the refresh token from local storage
    const refreshToken = localStorage.getItem('refreshToken') || '';

    // If no refresh token is found, do not proceed
    if (!refreshToken) {
      return;
    }

    try {
      // Call the API to refresh the token
      const response = await userApi.refreshToken(refreshToken);
      if (!response || !response.access_token) {
        return ; // Invalid response, do not proceed
      }

      // Update access token state
      localStorage.setItem('refreshToken', response.refresh_token);
      setAccessToken(response.access_token);
      return response;

    } catch (error) {
      console.error('Failed to refresh token:', error);
      // Clear tokens on error
      localStorage.removeItem('refreshToken');
      setAccessToken('');
      throw error;
    }
  };

  // Access token is refreshed on mount and before expiration
  React.useEffect(() => {
    let refreshTimeoutId: NodeJS.Timeout | null = null;
    let expiresIn: number = 3600; // Default to 1 hour

    // Function to schedule the next token refresh
    const scheduleTokenRefresh = async () => {
      try {
        // Call the handler to refresh the token
        const response = await handleRefreshToken();
        if (!response || !response.expires_in) {
          throw new Error('Invalid response from token refresh');
        }

        // Get access token expiration time (sec)
        expiresIn = response.expires_in;

      } catch (error) {
        console.error('Failed to refresh token:', error);
        // Clear any existing timeout on error
        if (refreshTimeoutId) {
          clearTimeout(refreshTimeoutId);
          refreshTimeoutId = null;
        }
        // Set a default expiration time
        expiresIn = 3600; // 1 hour

      } finally {
        // Schedule next refresh 5 minutes before expiration (or at 80% of the expiration time, whichever is shorter)
        const refreshBuffer = Math.min(3600, expiresIn * 0.2); // 5 minutes or 20% of expiration time
        const refreshTime = (expiresIn - refreshBuffer) * 1000; // Convert to milliseconds

        // Clear any existing timeout
        if (refreshTimeoutId) {
          clearTimeout(refreshTimeoutId);
        }

        // Schedule the next refresh
        refreshTimeoutId = setTimeout(() => {
          scheduleTokenRefresh();
        }, refreshTime);

        // Log the next refresh time
        console.log(`Token refreshed. Next refresh in ${Math.round(refreshTime / 1000)} seconds`);
      }
    };

    // Initial token refresh on mount
    scheduleTokenRefresh();

    // Cleanup function to clear timeout
    return () => {
      if (refreshTimeoutId) {
        clearTimeout(refreshTimeoutId);
        refreshTimeoutId = null;
      }
    };
  }, []);

  // Refresh user details on access token change
  React.useEffect(() => {
    if (accessToken) {
      userApi.getCurrentUser(accessToken).then(setUser);
    }
  }, [accessToken]);

  // Function to handle login
  // This function is called when the user logs in successfully
  const handleLogin = (response: AccessToken) => {
    setAccessToken(response.access_token);
    localStorage.setItem('refreshToken', response.refresh_token);
  };

  // Function to handle logout
  // This function is called when the user logs out
  // It clears the access token and removes the refresh token from local storage
  const handleLogout = () => {
    setAccessToken('');
    localStorage.removeItem('refreshToken');
  };

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated,
      accessToken,
      setAccessToken,
      login: handleLogin,
      logout: handleLogout,
    }}>
      {children}
    </AuthContext.Provider>
  );
}