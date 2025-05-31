import React from 'react';
import { AppBar, Toolbar, Typography, Box, Container, Button } from '@mui/material';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { getServiceIcon } from '@/utils/serviceIcons';

interface HeaderProps {
  isAuthenticated: boolean;
  isAdmin?: boolean;
  username?: string;
  onLogin: () => void;
  onLogout: () => void;
  onChangePassword?: () => void;
  onRefreshToken?: () => void;
}


const TitleIcon = getServiceIcon('title');

/**
 * Header Component
 * 
 * This functional component renders the application's header bar. It dynamically adjusts its content
 * based on the user's authentication status, admin privileges, and the current page. The header includes:
 * - A logo and title indicating the current page (Admin Panel or Portal).
 * - User-specific actions such as login, logout, change password, and refresh token.
 * - Navigation links to switch between the portal and admin panel.
 * 
 * Props:
 * - isAuthenticated: Boolean indicating if the user is logged in.
 * - isAdmin: Optional boolean indicating if the user has admin privileges.
 * - username: Optional string representing the username of the authenticated user.
 * - onLogin: Function to handle login action.
 * - onLogout: Function to handle logout action.
 * - onChangePassword: Optional function to handle password change action.
 * - onRefreshToken: Optional function to handle token refresh action.
 */
const Header: React.FC<HeaderProps> = ({
  isAuthenticated,
  isAdmin = false,
  username,
  onLogin,
  onLogout,
  onChangePassword,
  onRefreshToken,
}) => {
  const router = useRouter();
  const isAdminPage = router.pathname.includes('/admin');

  return (
    <AppBar position="static">
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          <Box sx={{ position: 'relative', width: 40, height: 40, marginRight: 2 }}>
            <Image
              src={TitleIcon}
              alt="AI Platform Logo"
              fill
              sizes="40px"
              style={{ objectFit: "contain" }}
              priority
            />
          </Box>
          <Typography variant="h6" component="div">
            {isAdminPage ? 'AI Platform Admin Panel' : 'AI Platform Portal'}
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          {isAuthenticated && (
            <Typography variant="body1" component="span" sx={{ mr: 2 }}>
              {username}
            </Typography>
          )}
          
          {isAdminPage ? (
            <Button color="inherit" component={Link} href="/">
              Return to Portal
            </Button>
          ) : isAdmin && isAuthenticated ? (
            <Button color="inherit" component={Link} href="/admin">
              Admin Panel
            </Button>
          ) : null}
          
          {isAuthenticated ? (
            <>
              {onChangePassword && (
                <Button color="inherit" onClick={onChangePassword}>
                  Change Password
                </Button>
              )}
              {onRefreshToken && (
                <Button color="inherit" onClick={onRefreshToken}>
                  Refresh Token
                </Button>
              )}
              <Button color="inherit" onClick={onLogout}>
                Logout
              </Button>
            </>
          ) : (
            <Button color="inherit" onClick={onLogin}>
              Login
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;
