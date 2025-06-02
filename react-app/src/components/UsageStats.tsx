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
// Import chart config to ensure Chart.js is properly set up
import '../components/chart-config';


/**
 * Props for the UsageStats component.
 * @property className - Optional CSS class name for styling the component.
 */
interface UsageStatsProps {
    className?: string;
}


/**
 * This component displays API usage statistics for the authenticated user.
 * @param param0 
 * @returns 
 */
const UsageStats: React.FC<UsageStatsProps> = ({ className }) => {
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

    useEffect(() => {
        if (isAuthenticated && user) {
            fetchUsageData();
        }
    }, [isAuthenticated, user, period, numPeriods]);

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
                // Map numPeriods to the correct param for the API
                let params: any = {};
                if (period === 'day') params.days = numPeriods;
                else if (period === 'week') params.weeks = numPeriods;
                else if (period === 'month') params.months = numPeriods;

                const response = await usageApi.getUserUsageByPeriod(period, params);
                
                let dataArr: any[] = [];
                if (period === 'day') {
                    dataArr = response.daily_usage || [];
                } else if (period === 'week') {
                    dataArr = response.weekly_usage || [];
                } else if (period === 'month') {
                    dataArr = response.monthly_usage || [];
                }

                if (!dataArr || dataArr.length === 0) {
                    setUsageData({
                        labels: [],
                        datasets: [
                            { ...usageData.datasets[0], data: [] },
                            { ...usageData.datasets[1], data: [] },
                        ],
                    });
                    return;
                }

                // Sort by date/period
                let sortedData = [...dataArr];
                if (period === 'day') {
                    sortedData.sort((a, b) =>
                        new Date(a.date).getTime() - new Date(b.date).getTime()
                    );
                } else if (period === 'week') {
                    sortedData.sort((a, b) =>
                        new Date(a.week_start).getTime() - new Date(b.week_start).getTime()
                    );
                } else if (period === 'month') {
                    sortedData.sort((a, b) =>
                        a.year !== b.year ? a.year - b.year : a.month - b.month
                    );
                }

                setUsageData({
                    labels: sortedData.map(item => {
                        if (period === 'day') {
                            const date = new Date(item.date);
                            return date.toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                            });
                        } else if (period === 'week') {
                            const start = new Date(item.week_start);
                            const end = new Date(item.week_end);
                            return `${start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
                        } else if (period === 'month') {
                            return `${item.year}-${String(item.month).padStart(2, '0')}`;
                        }
                        return '';
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

    if (!isAuthenticated || !user) {
        return null;
    }

    return (
        <Paper elevation={2} sx={{ p: 3, className }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Your API Usage</Typography>
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
