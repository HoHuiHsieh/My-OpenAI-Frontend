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
import { useAuthContext } from '@/context/AuthContext';
import { apiKeyApi, ApiKey, ApiKeyInfo } from '@/services/apikey';

/**
 * ApiKeyModel component provides a dialog for users to generate or refresh their long-live apikey.
 * The modal allows users to generate a apikey, copy it, and view the information associated with it.
 * @param open - Boolean to control the visibility of the modal.
 * @param onClose - Function to call when the modal is closed.
 * @returns JSX Element representing the ApiKeyModel.
 */
const ApiKeyModel: React.FC<ApiKeyModelProps> = ({ open, onClose }) => {
  const [apikey, setApiKey] = useState<string>('');
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyInfo | null>(null);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isApiKeyCopied, setIsApiKeyCopied] = useState<boolean>(false);
  const { isAuthenticated, accessToken } = useAuthContext();

  // Fetch API key status when modal is opened
  useEffect(() => {
    if (open && isAuthenticated) {
      fetchApiKeyStatus();
    }
  }, [open, isAuthenticated]);

  const fetchApiKeyStatus = async (updatedApiKey?: string) => {
    if(!updatedApiKey && !apikey) {
      return;
    }
    try {
      setIsLoading(true);
      const status = await apiKeyApi.getApiKeyStatus(accessToken);
      setApiKeyStatus(status);
      setError('');
    } catch (err) {
      console.error('Error fetching apikey status:', err);
      setError('Failed to fetch apikey status: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefreshApiKey = async () => {
    try {
      setIsLoading(true);
      setError('');
      const response = await apiKeyApi.refreshApiKey(accessToken);
      await fetchApiKeyStatus(response.apiKey); // Refresh apikey status after apikey refresh
      setApiKey(response.apiKey);
      setIsApiKeyCopied(false);
    } catch (err) {
      console.error('Error refreshing apikey:', err);
      setError('Failed to refresh apikey: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyApiKey = () => {
    if (apikey) {
      // Try to use Clipboard API with fallback
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(apikey)
          .then(() => {
            setIsApiKeyCopied(true);
            setTimeout(() => setIsApiKeyCopied(false), 3000); // Reset after 3 seconds
          })
          .catch(err => {
            console.error('Failed to copy apikey:', err);
            fallbackCopyToClipboard(apikey);
          });
      } else {
        // Use fallback approach if Clipboard API not available
        fallbackCopyToClipboard(apikey);
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
        setIsApiKeyCopied(true);
        setTimeout(() => setIsApiKeyCopied(false), 3000);
      } else {
        setError('Failed to copy apikey: Browser does not support copying');
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
      <DialogTitle>Manage API Key</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {isApiKeyCopied && (
          <Alert severity="success" sx={{ mb: 2 }}>
            API key copied to clipboard!
          </Alert>
        )}

        {apiKeyStatus && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2">
              Scopes: {apiKeyStatus.scopes.length > 0 ? apiKeyStatus.scopes.join(', ') : 'None'}
            </Typography>
            <Typography variant="body2">
              Expires: {apiKeyStatus.exp ? formatDate(apiKeyStatus.exp) : 'Never'}
            </Typography>
          </Box>
        )}

        {apikey && (
          <Box sx={{ mb: 3 }}>
            <TextField
              label="Your API Key"
              fullWidth
              value={apikey}
              variant="outlined"
              InputProps={{
                readOnly: true,
              }}
              sx={{ mb: 1 }}
            />
            <Button
              variant="outlined"
              color="primary"
              onClick={handleCopyApiKey}
              disabled={!apikey}
            >
              Copy API Key
            </Button>
          </Box>
        )}

        <Box sx={{ mt: 2, color: 'text.secondary', fontSize: '0.875rem' }}>
          Click "Refresh API Key" to generate a new access API key. This will invalidate any previously issued API key.
          Keep your API key secure and do not share it with others.
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleRefreshApiKey}
          disabled={isLoading}
        >
          {isLoading ? 'Processing...' : 'Refresh API Key'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

/**
 * Props for the ApiKeyModel component.
 * @property open - Boolean indicating whether the modal is open.
 * @property onClose - Callback function to close the modal.
 */
interface ApiKeyModelProps {
  open: boolean;
  onClose: () => void;
}

export default ApiKeyModel;