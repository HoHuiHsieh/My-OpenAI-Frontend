/**
 * A component that displays and manages a table of user accounts.
 * @module UserMgmtTable
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
  OutlinedInput,
  Tooltip,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  VpnKey as VpnKeyIcon,
  Refresh as RefreshIcon,
  Dashboard,
} from '@mui/icons-material';
import { userApi, AccessToken, User, UserCreate, UserResponse, UserUpdate } from '@/services/user';
import UsageStats from './UsageStats';
import { useAuthContext } from '@/context/AuthContext';

/**
 * User Management Table Component
 * 
 * This component provides a complete interface for managing users in the system:
 * - View all users in a paginated table
 * - Add new users
 * - Edit existing user information
 * - Change user passwords
 * - Delete users
 * - Toggle user activation status
 */
const UserMgmtTable: React.FC<{}> = () => {
  // Context for authentication
  const { accessToken } = useAuthContext(); // Get access token from AuthContext
  // State for users data
  const [users, setUsers] = useState<UserResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState<boolean>(false);

  // Pagination state
  const [page, setPage] = useState<number>(0);
  const [rowsPerPage, setRowsPerPage] = useState<number>(10);

  // Dialog states
  const [openAddDialog, setOpenAddDialog] = useState<boolean>(false);
  const [openEditDialog, setOpenEditDialog] = useState<boolean>(false);
  const [openPasswordDialog, setOpenPasswordDialog] = useState<boolean>(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState<boolean>(false);

  // Form states
  const [newUser, setNewUser] = useState<UserCreate>({
    username: '',
    password: '',
    email: '',
    fullname: '',
    active: true,
    scopes: [], // Added scopes property
  });

  const [editUser, setEditUser] = useState<UserUpdate & { username: string }>({
    username: '',
    email: '',
    fullname: '',
    active: true,
    scopes: [] // Added scopes property
  });

  const [passwordChange, setPasswordChange] = useState({
    username: '',
    password: '',
    confirmPassword: '',
  });

  const [deleteUsername, setDeleteUsername] = useState<string>('');

  const [dashboardUsername, setDashboardUsername] = useState<string>('all');

  const openDashboard = (username: string) => {
    setDashboardUsername(username);
  }

  // Fetch users from API
  const fetchUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const users = await userApi.listUsers(0, 100, accessToken); // Add explicit pagination parameters
      setUsers(users);
    } catch (err) {
      setError('Failed to load users. Please try again later.');
      console.error('Error fetching users:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load users on component mount
  useEffect(() => {
    fetchUsers();
  }, []);

  // Handle add user form submission
  const handleAddUser = async () => {
    try {
      setLoading(true);
      await userApi.createUser(newUser, accessToken);
      await fetchUsers(); // Refresh the user list
      setOpenAddDialog(false);
      // Reset form
      setNewUser({
        username: '',
        password: '',
        email: '',
        fullname: '',
        active: true,
        scopes: [], // Added scopes property
      });
    } catch (err) {
      setError('Failed to create user.');
      console.error('Error creating user:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle edit user form submission
  const handleEditUser = async () => {
    const { username, ...updateData } = editUser;
    try {
      setLoading(true);
      await userApi.updateUser(username, updateData, accessToken);
      await fetchUsers(); // Refresh the user list
      setOpenEditDialog(false);
    } catch (err) {
      setError('Failed to update user.');
      console.error('Error updating user:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle password change form submission
  const handleChangePassword = async () => {
    if (passwordChange.password !== passwordChange.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    try {
      setLoading(true);
      await userApi.updateUser(passwordChange.username, { password: passwordChange.password }, accessToken);
      setOpenPasswordDialog(false);
      setPasswordChange({
        username: '',
        password: '',
        confirmPassword: '',
      });
    } catch (err) {
      setError('Failed to change password.');
      console.error('Error changing password:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle delete user confirmation
  const handleDeleteUser = async () => {
    try {
      setLoading(true);
      await userApi.deleteUser(deleteUsername, accessToken);
      await fetchUsers(); // Refresh the user list
      setOpenDeleteDialog(false);
      setDeleteUsername('');
    } catch (err) {
      setError('Failed to delete user.');
      console.error('Error deleting user:', err);
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

  // Form change handlers
  const handleNewUserChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setNewUser(prev => ({ ...prev, [name]: value }));
  };

  const handleEditUserChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setEditUser(prev => ({ ...prev, [name]: value }));
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPasswordChange(prev => ({ ...prev, [name]: value }));
  };

  // Open dialog handlers
  const openEditUserDialog = (user: UserResponse) => {
    setEditUser({
      username: user.username,
      email: user.email || '',
      fullname: user.fullname || '',
      active: user.active,
      scopes: user.scopes || [], // Ensure scopes is an array
    });
    setOpenEditDialog(true);
  };

  const openChangePasswordDialog = (username: string) => {
    setPasswordChange({
      username,
      password: '',
      confirmPassword: '',
    });
    setOpenPasswordDialog(true);
  };

  const openConfirmDeleteDialog = (username: string) => {
    setDeleteUsername(username);
    setOpenDeleteDialog(true);
  };

  // Fetched available scopes
  const [availableScopes, setAvailableScopes] = useState<string[]>([]);

  useEffect(() => {
    const fetchAvailableScopes = async () => {
      try {
        const scopes = await userApi.getScopes(accessToken); // Adjust the endpoint if necessary
        setAvailableScopes(scopes);
      } catch (error) {
        console.error('Failed to fetch available scopes:', error);
      }
    };

    fetchAvailableScopes();
  }, []);

  // Formatted date helper
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 2 }}>
        <Typography variant="h6" component="div">
          User Management
        </Typography>
        <Box>
          <FormControlLabel
            control={
              <Switch
                checked={showInactive}
                onChange={(_, checked) => setShowInactive(checked)}
                color="primary"
              />
            }
            label="Show Inactive Users"
            sx={{ mr: 2 }}
          />
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={fetchUsers}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setOpenAddDialog(true)}
          >
            Add User
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
        <Table stickyHeader aria-label="user management table">
          <TableHead>
            <TableRow>
              <TableCell>Username</TableCell>
              <TableCell>Full Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Updated</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <CircularProgress size={24} sx={{ my: 2 }} />
                </TableCell>
              </TableRow>
            ) : users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  No users found
                </TableCell>
              </TableRow>
            ) : (
              users
                .filter((user) => showInactive || user.active)
                .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                .map((user) => (
                  <TableRow key={user.username} hover>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>{user.fullname || '-'}</TableCell>
                    <TableCell>{user.email || '-'}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.active ? 'Active' : 'Inactive'}
                        color={user.active ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{formatDate(user.created_at)}</TableCell>
                    <TableCell>{user?.updated_at && formatDate(user.updated_at)}</TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <Tooltip title="Edit User">
                          <IconButton onClick={() => openEditUserDialog(user)} size="small">
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Change Password">
                          <IconButton onClick={() => openChangePasswordDialog(user.username)} size="small">
                            <VpnKeyIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete User">
                          <IconButton
                            onClick={() => openConfirmDeleteDialog(user.username)}
                            size="small"
                            color="error"
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Dashboard">
                          <IconButton
                            onClick={() => openDashboard(user.username)}
                            size="small"
                          >
                            <Dashboard fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
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
        count={users.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />

      {/* Usage Stats Component */}
      <Box
        sx={{
          mt: 4,
          mb: 0,
          border: 1,
          borderColor: 'divider',
          borderRadius: 2,
          backgroundColor: 'background.paper',
          boxShadow: 10,
        }}
      >
        <UsageStats useAdminPanel={true} username={dashboardUsername} />
      </Box>

      {/* Add User Dialog */}
      <Dialog open={openAddDialog} onClose={() => setOpenAddDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New User</DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 1 }}>
            <TextField
              margin="dense"
              id="username"
              name="username"
              label="Username"
              type="text"
              fullWidth
              variant="outlined"
              value={newUser.username}
              onChange={handleNewUserChange}
              required
            />
            <TextField
              margin="dense"
              id="password"
              name="password"
              label="Password"
              type="password"
              fullWidth
              variant="outlined"
              value={newUser.password}
              onChange={handleNewUserChange}
              required
            />
            <FormControl fullWidth margin="dense">
              <InputLabel id="scopes-label">Scopes</InputLabel>
              <Select
                labelId="scopes-label"
                id="scopes"
                multiple
                value={newUser.scopes}
                onChange={(e) => setNewUser({ ...newUser, scopes: e.target.value as string[] })}
                input={<OutlinedInput label="Chip" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} />
                    ))}
                  </Box>
                )}
              >
                {availableScopes.map((scope) => (
                  <MenuItem key={scope} value={scope}>
                    {scope}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              margin="dense"
              id="email"
              name="email"
              label="Email"
              type="email"
              fullWidth
              variant="outlined"
              value={newUser.email}
              onChange={handleNewUserChange}
            />
            <TextField
              margin="dense"
              id="fullname"
              name="fullname"
              label="Full Name"
              type="text"
              fullWidth
              variant="outlined"
              value={newUser.fullname}
              onChange={handleNewUserChange}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={newUser.active}
                  onChange={(e) => setNewUser({ ...newUser, active: e.target.checked })}
                  name="active"
                />
              }
              label="Active"
              sx={{ mt: 1 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAddDialog(false)}>Cancel</Button>
          <Button onClick={handleAddUser} variant="contained" color="primary">
            Add User
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={openEditDialog} onClose={() => setOpenEditDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit User: {editUser.username}</DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 1 }}>
            <TextField
              margin="dense"
              id="edit-email"
              name="email"
              label="Email"
              type="email"
              fullWidth
              variant="outlined"
              value={editUser.email}
              onChange={handleEditUserChange}
            />
            <TextField
              margin="dense"
              id="edit-fullname"
              name="fullname"
              label="Full Name"
              type="text"
              fullWidth
              variant="outlined"
              value={editUser.fullname}
              onChange={handleEditUserChange}
            />
            <FormControl fullWidth margin="dense">
              <InputLabel id="edit-scopes-label">Scopes</InputLabel>
              <Select
                labelId="edit-scopes-label"
                id="edit-scopes"
                multiple
                value={editUser.scopes}
                onChange={(e) => setEditUser({ ...editUser, scopes: e.target.value as string[] })}
                input={<OutlinedInput label="Chip" />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} />
                    ))}
                  </Box>
                )}
              >
                {availableScopes.map((scope) => (
                  <MenuItem key={scope} value={scope}>
                    {scope}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Switch
                  checked={editUser.active}
                  onChange={(e) => setEditUser({ ...editUser, active: e.target.checked })}
                  name="active"
                />
              }
              label="Active"
              sx={{ mt: 1 }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenEditDialog(false)}>Cancel</Button>
          <Button onClick={handleEditUser} variant="contained" color="primary">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Change Password Dialog */}
      <Dialog open={openPasswordDialog} onClose={() => setOpenPasswordDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change Password for {passwordChange.username}</DialogTitle>
        <DialogContent>
          <Box component="form" sx={{ mt: 1 }}>
            <TextField
              margin="dense"
              id="password"
              name="password"
              label="New Password"
              type="password"
              fullWidth
              variant="outlined"
              value={passwordChange.password}
              onChange={handlePasswordChange}
              required
            />
            <TextField
              margin="dense"
              id="confirmPassword"
              name="confirmPassword"
              label="Confirm New Password"
              type="password"
              fullWidth
              variant="outlined"
              value={passwordChange.confirmPassword}
              onChange={handlePasswordChange}
              required
              error={passwordChange.password !== passwordChange.confirmPassword && passwordChange.confirmPassword !== ''}
              helperText={
                passwordChange.password !== passwordChange.confirmPassword && passwordChange.confirmPassword !== ''
                  ? 'Passwords do not match'
                  : ''
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenPasswordDialog(false)}>Cancel</Button>
          <Button
            onClick={handleChangePassword}
            variant="contained"
            color="primary"
            disabled={
              !passwordChange.password ||
              !passwordChange.confirmPassword ||
              passwordChange.password !== passwordChange.confirmPassword
            }
          >
            Change Password
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete User Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={() => setOpenDeleteDialog(false)}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the user &quot;{deleteUsername}&quot;? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDeleteDialog(false)}>Cancel</Button>
          <Button onClick={handleDeleteUser} variant="contained" color="error">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default UserMgmtTable;