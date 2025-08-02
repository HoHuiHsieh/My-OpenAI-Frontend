import React, { useState } from 'react';
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
} from '@mui/material';
import { useAuthContext } from '@/context/AuthContext';
import { userApi } from '@/services/user';

/**
 * LoginModal component provides a dialog for user authentication.
 * Users can enter their username, password, and optionally select scopes for access.
 * The modal handles login functionality and displays errors if login fails.
 */
const LoginModal: React.FC<LoginModalProps> = ({ open, onClose }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuthContext();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      // Call the authApi login endpoint directly
      const response = await userApi.login(username, password);
      // Update user information in local storage
      login(response)
      onClose();
    } catch (err) {
      console.error('Login error:', err);
      setError('Login failed: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <form onSubmit={handleSubmit}>
        <DialogTitle>Login</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Box sx={{ mt: 1 }}>
            <TextField
              autoFocus
              margin="dense"
              label="Username"
              type="text"
              fullWidth
              variant="outlined"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
            <TextField
              margin="dense"
              label="Password"
              type="password"
              fullWidth
              variant="outlined"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={isLoading}
          >
            {isLoading ? 'Logging in...' : 'Login'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

/**
 * Props for the LoginModal component.
 * @property open - Boolean indicating whether the modal is open.
 * @property onClose - Callback function to close the modal.
 */
interface LoginModalProps {
  open: boolean;
  onClose: () => void;
}

export default LoginModal;
