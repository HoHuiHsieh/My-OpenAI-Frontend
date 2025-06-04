/**
 * This module displays API usage statistics in a chart format.
 * It allows users to select the time period and number of periods to view their usage data.
 * The data is fetched from the API and displayed using a line chart.
 * It also includes error handling and loading states.
 * @module UsageStats
 * @version 1.0.0
 * @author Hsieh,HoHui 
 */

import React, { useEffect, useState, useRef, useId } from 'react';
import { Box, Paper, Typography, CircularProgress, Alert, FormControl, Select, MenuItem, SelectChangeEvent, InputLabel } from '@mui/material';
import { Line } from 'react-chartjs-2';
import { useAuth } from '@/context/AuthContext';
import { usageApi } from '@/services/usage';
import { accessApi } from '@/services/access';
// Import chart config to ensure Chart.js is properly set up
import '../components/chart-config';


/**
 * Props for the UsageStats component.
 * @property className - Optional CSS class name for styling the component.
 */
interface UsageStatsProps {
    useAdminPanel?: boolean;
    username?: string;
    className?: string;
}


/**
 * This component displays API usage statistics for the authenticated user.
 * @param param0 
 * @returns 
 */
const UsageStats: React.FC<UsageStatsProps> = ({ useAdminPanel, username, className }) => {
    const { isAuthenticated, user } = useAuth();
    const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const chartRef = useRef<any>(null);
    const chartId = useId(); // Generate unique ID for chart
    const [usageData, setUsageData] = useState<any>({
        labels: [],
        datasets: [
            {
                label: 'API Calls',
                data: [],
                borderColor: 'rgb(53, 162, 235)',
                backgroundColor: 'rgba(53, 162, 235, 0.5)',
                yAxisID: 'y',
            },
            {
                label: 'Total Tokens',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                yAxisID: 'y1',
            },
        ]
    });
    const [numPeriods, setNumPeriods] = useState(7);
    const [models, setModels] = useState<string[]>([]);
    const [selectedModel, setSelectedModel] = useState<string>('all');

    // Create a cleanup function to destroy the chart when component unmounts
    useEffect(() => {
        return () => {
            if (chartRef.current) {
                // Access the underlying Chart.js instance for v5+
                if (chartRef.current.chart) {
                    chartRef.current.chart.destroy();
                }
                // For older versions
                else if (chartRef.current.destroy) {
                    chartRef.current.destroy();
                }
            }
        };
    }, []);

    // Fetch available models when component mounts
    useEffect(() => {
        const fetchModels = async () => {
            try {
                const response = await accessApi.getModels();
                if (response && Array.isArray(response)) {
                    // Extract unique model names from the response
                    const modelNames = response;
                    setModels(modelNames);
                }
            } catch (error) {
                console.error('Failed to fetch models:', error);
            }
        };

        if (isAuthenticated) {
            fetchModels();
        }
    }, [isAuthenticated]);

    useEffect(() => {
        if (isAuthenticated && user) {
            fetchUsageData();
        }
    }, [isAuthenticated, user, period, numPeriods, selectedModel]);

    // Effect to update chart when data changes
    useEffect(() => {
        if (chartRef.current && chartRef.current.chart) {
            // Update data instead of recreating the chart
            chartRef.current.chart.data = usageData;
            chartRef.current.chart.update('none'); // Update without animation
        }
    }, [usageData]);

    const fetchUsageData = async () => {
        try {
            setLoading(true);
            setError(null);

            try {
                const response = !useAdminPanel
                    ? await usageApi.getUserUsageByPeriod(period, numPeriods, selectedModel)
                    : username
                        ? await usageApi.getSpecificUserUsage(username, period, numPeriods, selectedModel)
                        : await usageApi.getAllUsersUsage(period, numPeriods, selectedModel)

                if (!response || response.length === 0) {
                    setUsageData({
                        labels: [],
                        datasets: [
                            { ...usageData.datasets[0], data: [] },
                            { ...usageData.datasets[1], data: [] },
                        ],
                    });
                    return;
                }

                // Sort by time_period which should be a date string
                let sortedData = [...response].sort((a, b) => {
                    return new Date(a.time_period).getTime() - new Date(b.time_period).getTime();
                });

                // Add padding data to ensure we have numPeriods worth of data points
                if (sortedData.length < numPeriods) {
                    // Create a map of existing dates for quick lookup
                    const existingDates = new Map(
                        sortedData.map(item => [item.time_period, true])
                    );

                    // Generate expected dates based on period
                    const paddedData = [...sortedData];
                    const today = new Date();

                    // Go back numPeriods and generate all expected dates
                    for (let i = 0; i < numPeriods; i++) {
                        let date = new Date();

                        if (period === 'day') {
                            date.setDate(today.getDate() - i);
                            // Reset to start of day
                            date.setHours(0, 0, 0, 0);
                        } else if (period === 'week') {
                            // Go back i weeks
                            date.setDate(today.getDate() - (i * 7));
                            // Adjust to week start (Sunday)
                            const dayOfWeek = date.getDay();
                            date.setDate(date.getDate() - dayOfWeek);
                            date.setHours(0, 0, 0, 0);
                        } else if (period === 'month') {
                            // Go back i months
                            date.setMonth(today.getMonth() - i);
                            // Set to first day of month
                            date.setDate(1);
                            date.setHours(0, 0, 0, 0);
                        }

                        const dateString = date.toISOString().split('T')[0];

                        // If this date isn't in our results, add a zero-value entry
                        if (!existingDates.has(dateString)) {
                            paddedData.push({
                                time_period: dateString,
                                prompt_tokens: 0,
                                completion_tokens: 0,
                                total_tokens: 0,
                                request_count: 0
                            });
                        }
                    }

                    // Re-sort with the padded data
                    sortedData = paddedData.sort((a, b) => {
                        return new Date(a.time_period).getTime() - new Date(b.time_period).getTime();
                    });

                    // Limit to numPeriods most recent entries
                    if (sortedData.length > numPeriods) {
                        sortedData = sortedData.slice(-numPeriods);
                    }
                }

                setUsageData({
                    labels: sortedData.map(item => {
                        const date = new Date(item.time_period);
                        if (period === 'day') {
                            return date.toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                            });
                        } else if (period === 'week') {
                            // Assuming time_period is the start of the week
                            const endDate = new Date(date);
                            endDate.setDate(date.getDate() + 6);
                            return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
                        } else if (period === 'month') {
                            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
                        }
                        return item.time_period;
                    }),
                    datasets: [
                        {
                            label: 'API Calls',
                            data: sortedData.map(item => item.request_count),
                            borderColor: 'rgb(53, 162, 235)',
                            backgroundColor: 'rgba(53, 162, 235, 0.5)',
                            yAxisID: 'y',
                        },
                        {
                            label: 'Total Tokens',
                            data: sortedData.map(item => item.total_tokens),
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.5)',
                            yAxisID: 'y1',
                        },
                    ],
                });
            } catch (err) {
                console.error('Failed to fetch usage data:', err);
                setError('Failed to load usage statistics');
            }
        } finally {
            setLoading(false);
        }
    };

    const handlePeriodChange = (event: SelectChangeEvent<string>) => {
        setPeriod(event.target.value as 'day' | 'week' | 'month');
    };

    const handleNumPeriodsChange = (event: SelectChangeEvent<string>) => {
        setNumPeriods(parseInt(event.target.value as string, 10));
    };

    const handleModelChange = (event: SelectChangeEvent<string>) => {
        setSelectedModel(event.target.value);
    };

    if (!isAuthenticated || !user) {
        return null;
    }

    return (
        <Paper elevation={2} sx={{ p: 3, className }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">
                    {!useAdminPanel ? 'Your API Usage': username ? `${username}'s API Usage` : 'All Users API Usage'}
                </Typography>
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <FormControl size="small">
                        <Select value={period} onChange={handlePeriodChange}>
                            <MenuItem value="day">Daily</MenuItem>
                            <MenuItem value="week">Weekly</MenuItem>
                            <MenuItem value="month">Monthly</MenuItem>
                        </Select>
                    </FormControl>
                    <FormControl size="small">
                        <Select value={numPeriods.toString()} onChange={handleNumPeriodsChange}>
                            <MenuItem value="3">Last 3</MenuItem>
                            <MenuItem value="7">Last 7</MenuItem>
                            <MenuItem value="14">Last 14</MenuItem>
                            <MenuItem value="30">Last 30</MenuItem>
                            <MenuItem value="60">Last 60</MenuItem>
                            <MenuItem value="90">Last 90</MenuItem>
                        </Select>
                    </FormControl>
                    <FormControl size="small">
                        <InputLabel>Model</InputLabel>
                        <Select
                            value={selectedModel}
                            onChange={handleModelChange}
                            label="Model"
                        >
                            <MenuItem value="all">All Models</MenuItem>
                            {models.map((model) => (
                                <MenuItem key={model} value={model}>
                                    {model}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                </Box>
            </Box>

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}>
                    <CircularProgress />
                </Box>
            ) : error ? (
                <Alert severity="error">{error}</Alert>
            ) : (
                <Box sx={{ height: 300 }}>
                    <Line
                        id={`usage-chart-${chartId}`}
                        ref={chartRef}
                        data={usageData}
                        options={{
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false,
                            },
                            plugins: {
                                legend: {
                                    position: 'top',
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function (context) {
                                            let label = context.dataset.label || '';
                                            if (label) {
                                                label += ': ';
                                            }
                                            if (context.parsed.y !== null) {
                                                label += new Intl.NumberFormat().format(context.parsed.y);
                                            }
                                            return label;
                                        }
                                    }
                                }
                            },
                            scales: {
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    title: {
                                        display: true,
                                        text: 'API Calls'
                                    }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    title: {
                                        display: true,
                                        text: 'Tokens'
                                    },
                                    grid: {
                                        drawOnChartArea: false,
                                    },
                                },
                            }
                        }}
                    />
                </Box>
            )}
        </Paper>
    );
};



export default UsageStats;
