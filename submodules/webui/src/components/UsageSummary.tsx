/**
 * A component that displays system usage summary statistics
 * @module UsageSummary
 * @version 1.0.0
 * @author Hsieh,HoHui 
 */
import React, { useState, useEffect } from 'react';
import {
    Box,
    Paper,
    Grid,
    Typography,
    useTheme,
    CircularProgress,
    Alert
} from '@mui/material';
import { usageApi } from '@/services/usage';
import { useAuthContext } from '@/context/AuthContext';

/**
 * Interface for usage summary data
 */
interface UsageSummaryData {
    total_users: number;
    active_users_today: number;
    requests_today: number;
    tokens_today: number;
}

/**
 * Props for the UsageSummary component.
 * @property className - Optional CSS class name for styling the component.
 * @property refreshInterval - Optional interval in milliseconds to refresh the data.
 */
interface UsageSummaryProps {
    className?: string;
    refreshInterval?: number;
}

/**
 * This component displays usage summary statistics.
 * It fetches data from the admin summary API and displays it in a grid of cards.
 * @param {UsageSummaryProps} props - Component props
 * @returns {JSX.Element} Rendered component
 */
const UsageSummary = ({ className, refreshInterval = 60000 }: UsageSummaryProps): JSX.Element => {
    const theme = useTheme();
    const {accessToken} = useAuthContext(); // Get access token from AuthContext
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [summaryData, setSummaryData] = useState<UsageSummaryData | null>(null);

    const fetchSummaryData = async () => {
        try {
            setLoading(true);
            const data = await usageApi.getUsageSummary(accessToken); // Fetch usage summary data using the access token
            console.log('Fetched usage summary data:', data);
            
            setSummaryData(data);
            setError(null);
        } catch (err) {
            console.error('Failed to load usage summary data:', err);
            setError('Failed to load usage summary data. Please try again later.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSummaryData();

        // Set up interval to refresh data if refreshInterval is provided
        if (refreshInterval && refreshInterval > 0) {
            const intervalId = setInterval(fetchSummaryData, refreshInterval);
            return () => clearInterval(intervalId);
        }
    }, [refreshInterval]);

    if (loading && !summaryData) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error && !summaryData) {
        return (
            <Alert severity="error" sx={{ mb: 2 }}>
                {error}
            </Alert>
        );
    }

    return (
        <Box className={className}>
            <Typography variant="h6" gutterBottom>
                System Status
            </Typography>
            <Grid container spacing={2}>
                {summaryData && (
                    <>
                        <Grid size={{ xs: 12, sm: 6, md: 3 }} >
                            <Paper
                                elevation={0}
                                sx={{
                                    p: 2,
                                    bgcolor: theme.palette.primary.light,
                                    color: theme.palette.primary.contrastText,
                                    textAlign: 'center',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center'
                                }}
                            >
                                <Typography variant="h4">{summaryData.total_users}</Typography>
                                <Typography variant="body2">Total Users</Typography>
                            </Paper>
                        </Grid>

                        <Grid size={{ xs: 12, sm: 6, md: 3 }} >
                            <Paper
                                elevation={0}
                                sx={{
                                    p: 2,
                                    bgcolor: theme.palette.success.light,
                                    color: theme.palette.success.contrastText,
                                    textAlign: 'center',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center'
                                }}
                            >
                                <Typography variant="h4">{summaryData.active_users_today}</Typography>
                                <Typography variant="body2">Active Users Today</Typography>
                            </Paper>
                        </Grid>

                        <Grid size={{ xs: 12, sm: 6, md: 3 }} >
                            <Paper
                                elevation={0}
                                sx={{
                                    p: 2,
                                    bgcolor: theme.palette.info.light,
                                    color: theme.palette.info.contrastText,
                                    textAlign: 'center',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center'
                                }}
                            >
                                <Typography variant="h4">{summaryData.requests_today}</Typography>
                                <Typography variant="body2">API Requests Today</Typography>
                            </Paper>
                        </Grid>

                        <Grid size={{ xs: 12, sm: 6, md: 3 }} >
                            <Paper
                                elevation={0}
                                sx={{
                                    p: 2,
                                    bgcolor: theme.palette.warning.light,
                                    color: theme.palette.warning.contrastText,
                                    textAlign: 'center',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    justifyContent: 'center'
                                }}
                            >
                                <Typography variant="h4">{summaryData.tokens_today}</Typography>
                                <Typography variant="body2">Total Tokens Today</Typography>
                            </Paper>
                        </Grid>
                    </>
                )}
            </Grid>
        </Box>
    );
};

export default UsageSummary;