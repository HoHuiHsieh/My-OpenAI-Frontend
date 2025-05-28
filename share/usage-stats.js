// Usage statistics functionality

let usageChart = null;

// Initialize usage statistics functionality
document.addEventListener('DOMContentLoaded', () => {
    setupUsageStatisticsListeners();
});

// Setup event listeners for usage statistics
function setupUsageStatisticsListeners() {
    // Period selection change
    document.getElementById('period-select')?.addEventListener('change', () => {
        if (window.auth.isAuthenticated()) {
            loadUsageStatistics();
        }
    });
    
    // Period count change
    document.getElementById('period-count')?.addEventListener('change', () => {
        if (window.auth.isAuthenticated()) {
            loadUsageStatistics();
        }
    });
}

// Load usage statistics
async function loadUsageStatistics() {
    if (!window.auth.isAuthenticated()) {
        console.log('User not authenticated, skipping usage statistics');
        return;
    }
    
    try {
        const periodSelect = document.getElementById('period-select');
        const periodCountSelect = document.getElementById('period-count');
        
        if (!periodSelect || !periodCountSelect) {
            console.error('Period selection elements not found in DOM');
            return;
        }
        
        const period = periodSelect.value || 'day';
        const numPeriods = periodCountSelect.value || 30;
        
        console.log(`Loading usage statistics for period: ${period}, count: ${numPeriods}`);
        
        // Use root-relative URL for API endpoints
        const url = `/usage/me/${period}?num_periods=${numPeriods}`;
        const token = window.auth.getToken();
        
        if (!token) {
            console.error('No authentication token available');
            return;
        }
        
        console.log('Fetching usage data from API...');
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('Usage data received:', data);
            
            if (!Array.isArray(data)) {
                console.error('Expected array of usage data but received:', typeof data);
                return;
            }
            
            renderUsageChart(data, period);
            updateUsageSummary(data);
        } else {
            console.error(`Failed to load usage statistics: ${response.status} - ${response.statusText}`);
            try {
                const errorData = await response.text();
                console.error('Error details:', errorData);
            } catch (e) {
                console.error('Could not parse error response');
            }
        }
    } catch (error) {
        console.error('Error loading usage statistics:', error);
    }
}

// Render usage chart
function renderUsageChart(data, period) {
    const usageChartElement = document.getElementById('usage-chart');
    if (!usageChartElement) {
        console.error('Usage chart element not found in DOM');
        return;
    }
    
    const ctx = usageChartElement.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context from canvas');
        return;
    }
    
    // Set explicit dimensions for the chart
    usageChartElement.style.height = '300px';
    usageChartElement.style.width = '100%';
    
    // Handle empty data
    if (!data || data.length === 0) {
        console.warn('No usage data available to render chart');
        // Display a message on the canvas
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText('No usage data available', usageChartElement.width / 2, usageChartElement.height / 2);
        return;
    }
    
    try {
        // Format dates for display based on period
        const labels = data.map(item => formatPeriodDate(item.period_start || '', period));
        
        // Extract data for chart
        const promptTokens = data.map(item => item.prompt_tokens || 0);
        const completionTokens = data.map(item => item.completion_tokens || 0);
        
        console.log('Chart data prepared:', {
            labels,
            promptTokens,
            completionTokens,
            period
        });
        
        // Destroy existing chart if it exists
        if (usageChart) {
            usageChart.destroy();
        }
        
        // Create new chart
        usageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Prompt Tokens',
                    data: promptTokens,
                    backgroundColor: 'rgba(67, 97, 238, 0.7)',
                    borderColor: 'rgba(67, 97, 238, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Completion Tokens',
                    data: completionTokens,
                    backgroundColor: 'rgba(76, 201, 240, 0.7)',
                    borderColor: 'rgba(76, 201, 240, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    top: 10,
                    right: 20,
                    bottom: 10,
                    left: 10
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Token Count'
                    },
                    grid: {
                        display: true,
                        color: 'rgba(0, 0, 0, 0.1)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: getPeriodLabel(period)
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        footer: (tooltipItems) => {
                            const index = tooltipItems[0].dataIndex;
                            const dataPoint = data[index];
                            
                            if (!dataPoint) return '';
                            
                            return `Total: ${dataPoint.total_tokens || 0} tokens`;
                        }
                    }
                }
            }
        }
    });
    } catch (error) {
        console.error('Error creating usage chart:', error);
        // Clear the canvas and show error message
        ctx.clearRect(0, 0, usageChartElement.width, usageChartElement.height);
        ctx.font = '16px Arial';
        ctx.fillStyle = '#dd3333';
        ctx.textAlign = 'center';
        ctx.fillText('Error displaying chart', usageChartElement.width / 2, usageChartElement.height / 2);
    }
}

// Update usage summary
function updateUsageSummary(data) {
    // Find UI elements
    const totalTokensElement = document.getElementById('total-tokens');
    const totalRequestsElement = document.getElementById('total-requests');
    
    if (!totalTokensElement || !totalRequestsElement) {
        console.error('Usage summary elements not found');
        return;
    }
    
    try {
        // Calculate totals with safe checks
        const totalTokens = Array.isArray(data) ? 
            data.reduce((sum, item) => sum + (item.total_tokens || 0), 0) : 0;
        const totalRequests = Array.isArray(data) ? 
            data.reduce((sum, item) => sum + (item.request_count || 0), 0) : 0;
        
        // Update UI with formatted values
        totalTokensElement.textContent = formatNumber(totalTokens);
        totalRequestsElement.textContent = formatNumber(totalRequests);
        
        console.log('Usage summary updated:', { totalTokens, totalRequests });
    } catch (error) {
        console.error('Error updating usage summary:', error);
        // Set default values if there's an error
        totalTokensElement.textContent = '0';
        totalRequestsElement.textContent = '0';
    }
}

// Format date based on period
function formatPeriodDate(dateString, period) {
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            console.warn('Invalid date:', dateString);
            return 'Invalid date';
        }
        
        switch(period) {
            case 'day':
                return date.toLocaleDateString();
            case 'week':
                return `Week ${getWeekNumber(date)}`;
            case 'month':
                return date.toLocaleDateString('default', { month: 'short', year: 'numeric' });
            default:
                return date.toLocaleDateString();
        }
    } catch (error) {
        console.error('Error formatting period date:', error);
        return 'Error';
    }
}

// Get week number
function getWeekNumber(date) {
    try {
        const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
        const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
        return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
    } catch (error) {
        console.error('Error calculating week number:', error);
        return 0;
    }
}

// Get period label
function getPeriodLabel(period) {
    switch(period) {
        case 'day':
            return 'Days';
        case 'week':
            return 'Weeks';
        case 'month':
            return 'Months';
        default:
            return 'Period';
    }
}

// Format number with commas
function formatNumber(number) {
    try {
        return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    } catch (error) {
        console.error('Error formatting number:', error);
        return '0';
    }
}
