/**
 * A component that displays and manages a table of tokens.
 * @module TokenMgmtTable
 * @version 1.0.0
 * @author Hsieh,HoHui 
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  IconButton,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  Chip,
  Alert,
  CircularProgress,
  SelectChangeEvent,
  Checkbox,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  ContentCopy as CopyIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { adminApi } from '@/services/admin';

// Types from admin API
interface AccessTokenCreateData {
  scopes: string[];
  expires_days?: number;
  never_expires?: boolean;
}

interface AccessTokenResponse {
  id: number;
  username: string;
  scopes: string[];
  expires_at?: string;
  revoked: boolean;
  created_at: string;
}

/**
 * Token Management Table Component
 * 
 * This component provides a complete interface for managing access tokens:
 * - View all tokens in a paginated table
 * - Create new access tokens for users
 * - Delete/revoke tokens
 */
const TokenMgmtTable: React.FC = () => {
  // State for tokens data
  const [tokens, setTokens] = useState<AccessTokenResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [openDeleteDialog, setOpenDeleteDialog] = useState<boolean>(false);

  // Pagination state
  const [page, setPage] = useState<number>(0);
  const [rowsPerPage, setRowsPerPage] = useState<number>(10);

  // Form states
  const [deleteTokenId, setDeleteTokenId] = useState<{ id: number; username: string }>({
    id: 0,
    username: '',
  });
  const [showRevokedTokens, setShowRevokedTokens] = useState<boolean>(false);

  // Fetch tokens on component mount
  useEffect(() => {
    fetchTokens();
  }, []);

  // Fetch tokens from API
  const fetchTokens = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await adminApi.listAccessTokens();
      setTokens(response);
    } catch (err) {
      setError('Failed to load tokens. Please try again later.');
      console.error('Error fetching tokens:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete token confirmation
  const handleDeleteToken = async () => {
    try {
      setLoading(true);
      await adminApi.deleteAccessToken(deleteTokenId.username, deleteTokenId.id);
      await fetchTokens(); // Refresh the token list
      setOpenDeleteDialog(false);
      setDeleteTokenId({ id: 0, username: '' });
    } catch (err) {
      setError('Failed to delete token.');
      console.error('Error deleting token:', err);
    } finally {
      setLoading(false);
    }
  };

  // Pagination handlers
  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Open dialog handlers
  const openConfirmDeleteDialog = (id: number, username: string) => {
    setDeleteTokenId({ id, username });
    setOpenDeleteDialog(true);
  };

  // Formatted date helper
  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 2 }}>
        <Typography variant="h6" component="div">
          Access Token Management
        </Typography>
        <Box>
          <FormControlLabel
            control={
              <Switch
                checked={showRevokedTokens}
                onChange={(_, checked) => setShowRevokedTokens(checked)}
                color="primary"
                size="small"
              />
            }
            label="Show Revoked"
            sx={{ mr: 2 }}
          />
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchTokens}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {error && (
        <Box sx={{ px: 2 }}>
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        </Box>
      )}

      <TableContainer sx={{ maxHeight: 440 }}>
        <Table stickyHeader aria-label="token management table">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Username</TableCell>
              <TableCell>Scopes</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Expires</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && tokens.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <CircularProgress size={24} sx={{ my: 2 }} />
                </TableCell>
              </TableRow>
            ) : tokens.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No tokens found
                </TableCell>
              </TableRow>
            ) : (
              tokens
                .filter((token) => (showRevokedTokens ? true : !token.revoked))
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((token) => (
                  <TableRow key={token.id} hover>
                    <TableCell>{token.id}</TableCell>
                    <TableCell>{token.username}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {token.scopes.map((scope) => (
                          <Chip
                            key={scope}
                            label={scope}
                            size="small"
                            color={scope === 'admin' ? 'primary' : 'default'}
                          />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={token.revoked ? 'Revoked' : 'Active'}
                        color={token.revoked ? 'error' : 'success'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{formatDate(token.created_at)}</TableCell>
                    <TableCell>{formatDate(token.expires_at)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Delete Token">
                        <IconButton
                          onClick={() => openConfirmDeleteDialog(token.id, token.username)}
                          size="small"
                          color="error"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 100]}
        component="div"
        count={tokens.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />

      {/* Delete Token Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Delete Access Token</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the access token for user "{deleteTokenId.username}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDeleteToken} variant="contained" color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default TokenMgmtTable;