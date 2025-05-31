import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Chip,
  Typography,
} from '@mui/material';
import { useAuth } from '@/context/AuthContext';
import { accessApi, TokenInfo, TokenRequest } from '@/services/access';

/**
 * TokenModal component provides a dialog for users to generate or refresh their long-live token.
 * The modal allows users to generate a token, copy it, and view the information associated with it.
 * @param open - Boolean to control the visibility of the modal.
 * @param onClose - Function to call when the modal is closed.
 * @returns JSX Element representing the TokenModal.
 */
const TokenModal: React.FC<TokenModalProps> = ({ open, onClose }) => {
  const [token, setToken] = useState<string>('');
  const [tokenStatus, setTokenStatus] = useState<TokenInfo | null>(null);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isTokenCopied, setIsTokenCopied] = useState<boolean>(false);
  const { isAuthenticated } = useAuth();

  // Fetch token status when modal is opened
  useEffect(() => {
    if (open && isAuthenticated) {
      fetchTokenStatus();
    }
  }, [open, isAuthenticated]);

  const fetchTokenStatus = async (updatedToken?: string) => {
    if(!updatedToken && !token) {
      return;
    }
    try {
      setIsLoading(true);
      const tokenData: TokenRequest = { token: updatedToken || token }; // Empty token to fetch current status
      const status = await accessApi.getTokenStatus(tokenData);
      setTokenStatus(status);
      setError('');
    } catch (err) {
      console.error('Error fetching token status:', err);
      setError('Failed to fetch token status: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefreshToken = async () => {
    try {
      setIsLoading(true);
      setError('');
      const response = await accessApi.refreshToken();
      await fetchTokenStatus(response.access_token); // Refresh token status after token refresh
      setToken(response.access_token);      
      setIsTokenCopied(false);
    } catch (err) {
      console.error('Error refreshing token:', err);
      setError('Failed to refresh token: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyToken = () => {
    if (token) {
      // Try to use Clipboard API with fallback
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(token)
          .then(() => {
            setIsTokenCopied(true);
            setTimeout(() => setIsTokenCopied(false), 3000); // Reset after 3 seconds
          })
          .catch(err => {
            console.error('Failed to copy token:', err);
            fallbackCopyToClipboard(token);
          });
      } else {
        // Use fallback approach if Clipboard API not available
        fallbackCopyToClipboard(token);
      }
    }
  };

  // Fallback method for clipboard copy using a temporary textarea element
  const fallbackCopyToClipboard = (text: string) => {
    try {
      // Create temporary element
      const textArea = document.createElement('textarea');
      textArea.value = text;

      // Make the textarea out of viewport
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);

      // Select and copy
      textArea.focus();
      textArea.select();

      const successful = document.execCommand('copy');
      document.body.removeChild(textArea);

      if (successful) {
        setIsTokenCopied(true);
        setTimeout(() => setIsTokenCopied(false), 3000);
      } else {
        setError('Failed to copy token: Browser does not support copying');
      }
    } catch (err) {
      console.error('Fallback copy failed:', err);
      setError('Unable to copy to clipboard in this browser environment');
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    date.setHours(date.getHours() + 8);
    return date.toLocaleString();
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Manage Access Token</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {isTokenCopied && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Token copied to clipboard!
          </Alert>
        )}

        {tokenStatus && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom>Current Token Status</Typography>
            <Typography variant="body2">Username: {tokenStatus.username}</Typography>
            <Typography variant="body2">
              Scopes: {tokenStatus.scopes.length > 0 ? tokenStatus.scopes.join(', ') : 'None'}
            </Typography>
            <Typography variant="body2">
              Expires: {tokenStatus.expires_at ? formatDate(tokenStatus.expires_at) : 'Never'}
            </Typography>
            <Typography variant="body2">
              Issued At: {formatDate(tokenStatus.issued_at)}
            </Typography>
            <Typography variant="body2">
              Status: {tokenStatus.active ? 'Active' : 'Expired'}
            </Typography>
            <Typography variant="body2">
              Type: {tokenStatus.type}
            </Typography>
          </Box>
        )}

        {token && (
          <Box sx={{ mb: 3 }}>
            <TextField
              label="Your Token"
              fullWidth
              value={token}
              variant="outlined"
              InputProps={{
                readOnly: true,
              }}
              sx={{ mb: 1 }}
            />
            <Button
              variant="outlined"
              color="primary"
              onClick={handleCopyToken}
              disabled={!token}
            >
              Copy Token
            </Button>
          </Box>
        )}

        <Box sx={{ mt: 2, color: 'text.secondary', fontSize: '0.875rem' }}>
          Click "Refresh Token" to generate a new access token. This will invalidate any previously issued token.
          Keep your token secure and do not share it with others.
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleRefreshToken}
          disabled={isLoading}
        >
          {isLoading ? 'Processing...' : 'Refresh Token'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

/**
 * Props for the TokenModal component.
 * @property open - Boolean indicating whether the modal is open.
 * @property onClose - Callback function to close the modal.
 */
interface TokenModalProps {
  open: boolean;
  onClose: () => void;
}

export default TokenModal;