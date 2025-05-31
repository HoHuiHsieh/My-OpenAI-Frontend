import React, { useState, useEffect, useRef, useId } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Grid,
  Tabs,
  Tab,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  useTheme,
  Alert,
  CircularProgress,
} from '@mui/material';
import Head from 'next/head';
import Header from '@/components/Header';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/router';
import { Line, Bar } from 'react-chartjs-2';
import { usageApi } from '@/services/usage';
import { adminApi } from '@/services/admin';
// Import chart config to ensure Chart.js is properly set up
import '../components/chart-config';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `admin-tab-${index}`,
    'aria-controls': `admin-tabpanel-${index}`,
  };
}

// Function to transform usage data for charts
/**
 * Transforms raw usage data into a format suitable for rendering charts.
 * @param data - Array of usage data objects containing period_start, request_count, and total_tokens.
 * @returns Chart.js-compatible data object with labels and datasets.
 */
const transformUsageData = (data: any[]) => {
  // Return default structure if data is empty
  if (!data || data.length === 0) return {
    labels: [],
    datasets: [{ label: 'API Calls', data: [], borderColor: 'rgb(53, 162, 235)', backgroundColor: 'rgba(53, 162, 235, 0.5)' }]
  };

  // Sort data by period_start
  const sortedData = [...data].sort((a, b) => 
    new Date(a.period_start).getTime() - new Date(b.period_start).getTime()
  );

  // Map sorted data to chart labels and datasets
  return {
    labels: sortedData.map(item => {
      const date = new Date(item.period_start);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'API Calls',
        data: sortedData.map(item => item.request_count),
        borderColor: 'rgb(53, 162, 235)',
        backgroundColor: 'rgba(53, 162, 235, 0.5)',
      },
      {
        label: 'Total Tokens',
        data: sortedData.map(item => item.total_tokens),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
      },
    ],
  };
};

/**
 * Aggregates and transforms API usage data by service type for rendering charts.
 * @param data - Array of usage data objects containing api_types.
 * @returns Chart.js-compatible data object with labels and datasets.
 */
const transformServiceData = (data: any[]) => {
  // Return default structure if data is empty
  if (!data || data.length === 0) return {
    labels: [],
    datasets: [{ label: 'Usage by Service', data: [], backgroundColor: [] }]
  };
  
  // Aggregate data by API type
  const apiTypes: Record<string, number> = {};
  data.forEach(item => {
    if (item.api_types) {
      Object.entries(item.api_types).forEach(([type, count]) => {
        apiTypes[type] = (apiTypes[type] || 0) + Number(count);
      });
    }
  });

  // Define colors for chart bars
  const colors = [
    'rgba(255, 99, 132, 0.5)',
    'rgba(54, 162, 235, 0.5)',
    'rgba(255, 206, 86, 0.5)',
    'rgba(75, 192, 192, 0.5)',
    'rgba(153, 102, 255, 0.5)',
    'rgba(255, 159, 64, 0.5)',
  ];

  // Map aggregated data to chart labels and datasets
  const labels = Object.keys(apiTypes);
  return {
    labels,
    datasets: [
      {
        label: 'Usage by Service',
        data: labels.map(label => apiTypes[label]),
        backgroundColor: labels.map((_, index) => colors[index % colors.length]),
      },
    ],
  };
};

export default function AdminPanel() {
  const [tabValue, setTabValue] = useState(0);
  const { isAuthenticated, user, logout, hasScope } = useAuth();
  const router = useRouter();
  const theme = useTheme();
  const chartId = useId(); // Generate unique IDs for charts
  
  // References for chart instances
  const usageChartRef = useRef<any>(null);
  const serviceChartRef = useRef<any>(null);

  // State for API data
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Initialize chart data with empty arrays to avoid null reference errors
  const [usageData, setUsageData] = useState<any>({
    labels: [],
    datasets: [
      {
        label: 'API Calls',
        data: [],
        borderColor: 'rgb(53, 162, 235)',
        backgroundColor: 'rgba(53, 162, 235, 0.5)',
      }
    ]
  });
  const [serviceData, setServiceData] = useState<any>({
    labels: [],
    datasets: [
      {
        label: 'Usage by Service',
        data: [],
        backgroundColor: [],
      }
    ]
  });
  const [userData, setUserData] = useState<any[]>([]);
  const [dashboardSummary, setDashboardSummary] = useState<any>(null);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);

  // Redirect non-admin users to homepage
  useEffect(() => {
    if (isAuthenticated && !hasScope('admin')) {
      router.push('/');
    } else if (!isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, user, router, hasScope]);
  
  // Cleanup chart instances when component unmounts
  // Cleanup effect for chart instances
  useEffect(() => {
    return () => {
      // Define a function to safely destroy chart instances
      const safelyDestroyChart = (ref: React.MutableRefObject<any>) => {
        if (ref.current) {
          // For react-chartjs-2 v5+
          if (ref.current.chart) {
            ref.current.chart.destroy();
          }
          // For older versions
          else if (ref.current.destroy) {
            ref.current.destroy();
          }
        }
      };

      // Clean up both charts
      safelyDestroyChart(usageChartRef);
      safelyDestroyChart(serviceChartRef);

    };
  }, []);
  
  // Load admin data when the component mounts
  useEffect(() => {
    if (isAuthenticated && hasScope('admin')) {
      const loadAdminData = async () => {
        try {
          setLoading(true);
          setError(null);

          // Fetch usage statistics for the last 7 days
          const usageResponse = await usageApi.getAllUsersUsage('day', { num_periods: 7 });
          setUsageData(transformUsageData(usageResponse));
          setServiceData(transformServiceData(usageResponse));

          // Fetch users list
          const usersResponse = await adminApi.listUsers();
          setUserData(usersResponse.map((user: any, index: number) => ({
            id: index + 1,
            username: user.username,
            lastLogin: 'N/A', // Last login info isn't in the API
            role: user.scopes.includes('admin') ? 'Admin' : 'User',
            status: user.disabled ? 'Inactive' : 'Active',
            scopes: user.scopes,
            email: user.email,
            full_name: user.full_name
          })));
          
          // Fetch admin dashboard summary
          const summaryResponse = await usageApi.getAdminSummary();
          setDashboardSummary(summaryResponse.data);
          
          // Fetch recent activity
          const activityResponse = await usageApi.getRecentActivity();
          setRecentActivity(activityResponse.data);
          
        } catch (err) {
          console.error('Failed to load admin data:', err);
          setError('Failed to load admin data. Please try refreshing the page.');
        } finally {
          setLoading(false);
        }
      };
      
      loadAdminData();
    }
  }, [isAuthenticated, hasScope]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (!isAuthenticated || !user?.isAdmin) {
    return null; // Don't render anything while redirecting
  }

  return (
    <>
      <Head>
        <title>Admin Panel - AI Platform</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <Header
        isAuthenticated={isAuthenticated}
        username={user?.username}
        onLogin={() => { }}
        onLogout={logout}
        isAdmin={true}
      />

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Paper sx={{ p: 3, mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
            Admin Dashboard
          </Typography>

          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={handleTabChange} aria-label="admin tabs">
              <Tab label="Dashboard" {...a11yProps(0)} />
              <Tab label="User Management" {...a11yProps(1)} />
              <Tab label="System Status" {...a11yProps(2)} />
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            {loading ? (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
                <CircularProgress />
              </Box>
            ) : error ? (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            ) : (
              <Grid container spacing={4}>
                <Grid size={{ xs: 12, lg: 8 }} >
                  <Paper elevation={2} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      API Usage (Last 7 Days)
                    </Typography>
                    <Box sx={{ height: 300 }}>
                      <Line
                        id={`admin-usage-chart-${chartId}`}
                        ref={usageChartRef}
                        data={usageData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              position: 'top' as const,
                            },
                          },
                        }}
                      />
                    </Box>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 12, lg: 4 }} >
                  <Paper elevation={2} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      Usage by Service
                    </Typography>
                    <Box sx={{ height: 300 }}>
                      <Bar
                        id={`admin-service-chart-${chartId}`}
                        ref={serviceChartRef}
                        data={serviceData}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              display: false,
                            },
                          },
                        }}
                      />
                    </Box>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 12 }}>
                  <Paper elevation={2} sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      System Status
                    </Typography>
                    <Grid container spacing={2}>
                      {dashboardSummary && (
                        <>
                          <Grid size={{ xs: 12, md: 3 }} >
                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                bgcolor: theme.palette.primary.light,
                                color: theme.palette.primary.contrastText,
                                textAlign: 'center'
                              }}
                            >
                              <Typography variant="h4">{dashboardSummary.total_users}</Typography>
                              <Typography variant="body2">Total Users</Typography>
                            </Paper>
                          </Grid>
                          <Grid size={{ xs: 12, md: 3 }}>
                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                bgcolor: theme.palette.success.light,
                                color: theme.palette.success.contrastText,
                                textAlign: 'center'
                              }}
                            >
                              <Typography variant="h4">{dashboardSummary.active_users_today}</Typography>
                              <Typography variant="body2">Active Users Today</Typography>
                            </Paper>
                          </Grid>
                          <Grid size={{ xs: 12, md: 3 }}>
                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                bgcolor: theme.palette.info.light,
                                color: theme.palette.info.contrastText,
                                textAlign: 'center'
                              }}
                            >
                              <Typography variant="h4">{dashboardSummary.api_requests_today}</Typography>
                              <Typography variant="body2">API Requests Today</Typography>
                            </Paper>
                          </Grid>
                          <Grid size={{ xs: 12, md: 3 }}>
                            <Paper
                              elevation={0}
                              sx={{
                                p: 2,
                                bgcolor: theme.palette.warning.light,
                                color: theme.palette.warning.contrastText,
                                textAlign: 'center'
                              }}
                            >
                              <Typography variant="h4">{dashboardSummary.total_tokens_today}</Typography>
                              <Typography variant="body2">Total Tokens Today</Typography>
                            </Paper>
                          </Grid>
                        </>
                      )}
                    </Grid>
                  </Paper>
                </Grid>

                {/* Recent Activity Section */}
                {recentActivity && recentActivity.length > 0 && (
                  <Grid size={{ xs: 12 }}>
                    <Paper elevation={2} sx={{ p: 3 }}>
                      <Typography variant="h6" gutterBottom>
                        Recent Activity
                      </Typography>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Time</TableCell>
                              <TableCell>User</TableCell>
                              <TableCell>Action</TableCell>
                              <TableCell>Details</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {recentActivity.slice(0, 5).map((activity, index) => (
                              <TableRow key={index}>
                                <TableCell>
                                  {new Date(activity.timestamp).toLocaleString()}
                                </TableCell>
                                <TableCell>{activity.username}</TableCell>
                                <TableCell>{activity.action}</TableCell>
                                <TableCell>{activity.details}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </Paper>
                  </Grid>
                )}
              </Grid>
            )}
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            {loading ? (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
                <CircularProgress />
              </Box>
            ) : error ? (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            ) : (
              <Paper elevation={2} sx={{ p: 0 }}>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Username</TableCell>
                        <TableCell>Email</TableCell>
                        <TableCell>Full Name</TableCell>
                        <TableCell>Role</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Scopes</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {userData.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell>{user.username}</TableCell>
                          <TableCell>{user.email || 'N/A'}</TableCell>
                          <TableCell>{user.full_name || 'N/A'}</TableCell>
                          <TableCell>{user.role}</TableCell>
                          <TableCell>
                            <Box
                              component="span"
                              sx={{
                                px: 1,
                                py: 0.5,
                                borderRadius: 1,
                                bgcolor: user.status === 'Active' ? 'success.light' : 'error.light',
                                color: user.status === 'Active' ? 'success.dark' : 'error.dark',
                              }}
                            >
                              {user.status}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, maxWidth: '200px' }}>
                              {user.scopes?.map((scope: string, index: number) => (
                                <Box
                                  key={index}
                                  sx={{
                                    px: 1,
                                    py: 0.5,
                                    borderRadius: 1,
                                    fontSize: '0.75rem',
                                    bgcolor: 'primary.light',
                                    color: 'primary.contrastText',
                                    whiteSpace: 'nowrap',
                                    mb: 0.5,
                                  }}
                                >
                                  {scope}
                                </Box>
                              ))}
                            </Box>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            )}
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            {loading ? (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
                <CircularProgress />
              </Box>
            ) : error ? (
              <Alert severity="error" sx={{ mb: 3 }}>
                {error}
              </Alert>
            ) : (
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={2} sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>Server Stats</Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell><strong>CPU Usage</strong></TableCell>
                            <TableCell>23%</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Memory Usage</strong></TableCell>
                            <TableCell>45% (3.6 GB / 8 GB)</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Disk Space</strong></TableCell>
                            <TableCell>68% (136 GB / 200 GB)</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Network I/O</strong></TableCell>
                            <TableCell>Up: 5.2 Mbps, Down: 8.7 Mbps</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>System Uptime</strong></TableCell>
                            <TableCell>18 days, 7 hours, 23 minutes</TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper elevation={2} sx={{ p: 2 }}>
                    <Typography variant="h6" gutterBottom>Service Status</Typography>
                    <TableContainer>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell><strong>API Gateway</strong></TableCell>
                            <TableCell>
                              <Box component="span" sx={{ color: 'success.main' }}>Online</Box>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Authentication Service</strong></TableCell>
                            <TableCell>
                              <Box component="span" sx={{ color: 'success.main' }}>Online</Box>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Chat Service</strong></TableCell>
                            <TableCell>
                              <Box component="span" sx={{ color: 'success.main' }}>Online</Box>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Embeddings Service</strong></TableCell>
                            <TableCell>
                              <Box component="span" sx={{ color: 'success.main' }}>Online</Box>
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell><strong>Database Service</strong></TableCell>
                            <TableCell>
                              <Box component="span" sx={{ color: 'warning.main' }}>Degraded Performance</Box>
                            </TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </Paper>
                </Grid>
              </Grid>
            )}
          </TabPanel>
        </Paper>
      </Container>
    </>
  );
}
