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
} from '@mui/material';
import { userApi } from '@/services/user';
import { useAuthContext } from '@/context/AuthContext';

interface PasswordModalProps {
  open: boolean;
  onClose: () => void;
}

/**
 * ChangePasswordModal Component
 * 
 * This functional component renders a modal dialog for changing the user's password. It includes:
 * - Input fields for the current password, new password, and confirmation of the new password.
 * - Validation to ensure the new password and confirmation match.
 * - Error handling to display appropriate messages if the password change fails.
 * - A loading state to indicate when the password change is in progress.
 * 
 * Props:
 * - open: Boolean indicating whether the modal is open.
 * - onClose: Function to handle closing the modal.
 * 
 * Context:
 * - Uses the `useAuthContext` hook to access the `changePassword` function for updating the password.
 */
const ChangePasswordModal: React.FC<PasswordModalProps> = ({ open, onClose }) => {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { accessToken } = useAuthContext();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      setIsLoading(false);
      return;
    }

    try {
      // Use the authApi directly with the expected request format
      await userApi.updateCurrentUser({
        password: newPassword,
      }, accessToken); // Pass the access token for authentication      
      setNewPassword('');
      setConfirmPassword('');
      onClose();
    } catch (err) {
      setError('Failed to change password: ' + (err instanceof Error ? err.message : 'Unknown error'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <form onSubmit={handleSubmit}>
        <DialogTitle>Change Password</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          <Box sx={{ mt: 1 }}>
            <TextField
              margin="dense"
              label="New Password"
              type="password"
              fullWidth
              variant="outlined"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
            <TextField
              margin="dense"
              label="Confirm New Password"
              type="password"
              fullWidth
              variant="outlined"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
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
            {isLoading ? 'Changing...' : 'Change Password'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default ChangePasswordModal;
