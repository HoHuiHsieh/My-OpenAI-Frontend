import React, { useState, useEffect, useRef, useId } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Tabs,
  Tab,
  useTheme,
  Stack,
} from '@mui/material';
import Head from 'next/head';
import Header from '@/components/Header';
import UsageSummary from '@/components/UsageSummary';
import UserMgmtTable from '@/components/UserMgmtTable';
import { useAuthContext } from '@/context/AuthContext';
import { useRouter } from 'next/router';

// Import chart config to ensure Chart.js is properly set up
import '../components/chart-config';
import UsageStats from '@/components/UsageStats';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const IMAGE_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * TabPanel component to render content for each tab in the admin panel.
 * @param props 
 * @returns 
 */
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
  const { isAuthenticated, user, logout } = useAuthContext();
  const router = useRouter();
  const theme = useTheme();
  const chartId = useId(); // Generate unique IDs for charts

  // References for chart instances
  const usageChartRef = useRef<any>(null);
  const serviceChartRef = useRef<any>(null);

  // Redirect non-admin users to homepage
  useEffect(() => {
    if (isAuthenticated && !user.scopes.includes('admin')) {
      router.push('/');
    } else if (!isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, user, router]);

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

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (!isAuthenticated || !user.scopes.includes('admin')) {
    return null; // Don't render anything while redirecting
  }

  return (
    <>
      <Head>
        <title>Admin Panel - AI Platform</title>
        {/* <link rel="icon" href={`${IMAGE_BASE_URL}/favicon.ico`} /> */}
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
            </Tabs>
          </Box>

          <TabPanel value={tabValue} index={0}>
            <Stack direction="column" spacing={2} sx={{ mb: 4 }}>
              <UsageSummary refreshInterval={300000} />
              <UsageStats useAdminPanel={true} />
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <UserMgmtTable />
          </TabPanel>

        </Paper>
      </Container>
    </>
  );
}
