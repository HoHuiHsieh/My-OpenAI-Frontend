// Admin Panel Functionality

let adminUsageChart = null;
let usageTrendChart = null;
let adminAuthState = null; // Will be populated from window.auth

// Initialize admin functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    checkAdminAccess();
    setupAdminEventListeners();
});

// Validate token function for admin.js (uses auth.js validateToken through window.auth)
async function validateToken(token) {
    if (window.auth && typeof window.auth.validateToken === 'function') {
        return window.auth.validateToken(token);
    } else {
        console.error('validateToken function not available in window.auth');
        return Promise.reject('Auth function not available');
    }
}

// Check if current user has admin access
function checkAdminAccess() {
    console.log('Checking admin access, window.auth available:', !!window.auth);

    // If auth isn't available yet, wait for auth.js to initialize
    if (!window.auth) {
        console.log('Auth not available yet, retrying in 100ms');
        setTimeout(checkAdminAccess, 100);
        return;
    }

    // Validate token if available
    const token = localStorage.getItem('accessToken');
    if (token) {
        console.log('Token found in localStorage, revalidating token for admin page');

        // Force re-validation to ensure admin status is checked
        adminAuthState = window.auth.getAuthState ? window.auth.getAuthState() : {
            isAuthenticated: false,
            accessToken: token,
            username: null,
            isAdmin: false,
            userInfo: null
        };

        // Revalidate token to ensure we have admin status
        validateToken(token).then(() => {
            console.log('Token revalidated for admin page, updating UI');
            updateAdminUI();
        }).catch(error => {
            console.error('Error validating token for admin page:', error);
            showAdminRequired();
        });
    } else {
        console.log('No token found, showing admin required message');
        // No token, show admin required message
        showAdminRequired();
    }
}

// Update UI based on admin access
function updateAdminUI() {
    const adminRequired = document.getElementById('admin-required');
    const adminContent = document.getElementById('admin-content');

    // Check if user is authenticated and has admin privileges
    const isAuthenticated = window.auth.isAuthenticated();
    const isAdmin = window.auth.isAdmin();
    console.log('Admin check:', { isAuthenticated, isAdmin });

    if (isAuthenticated && isAdmin) {
        console.log('User has admin access, showing admin panel');
        if (adminRequired) adminRequired.style.display = 'none';
        if (adminContent) adminContent.style.display = 'grid';

        // Load initial admin data
        loadDashboardData();
    } else {
        // User doesn't have admin access
        console.log('User does not have admin access, showing admin required message');
        if (adminRequired) adminRequired.style.display = 'flex';
        if (adminContent) adminContent.style.display = 'none';
    }
}

// Show admin required message
function showAdminRequired() {
    const adminRequired = document.getElementById('admin-required');
    const adminContent = document.getElementById('admin-content');

    if (adminRequired) adminRequired.style.display = 'flex';
    if (adminContent) adminContent.style.display = 'none';
}

// Setup admin event listeners
function setupAdminEventListeners() {
    // Return to portal button
    document.getElementById('portal-btn')?.addEventListener('click', () => {
        console.log('Returning to portal');
        window.location.href = '/share/index.html';
    });

    // Return button on admin required message
    document.getElementById('return-btn')?.addEventListener('click', () => {
        console.log('Returning to portal');
        window.location.href = '/share/index.html';
    });

    // Admin navigation
    const navItems = document.querySelectorAll('.admin-nav li');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active class from all nav items
            navItems.forEach(navItem => {
                navItem.classList.remove('active');
            });

            // Add active class to clicked item
            item.classList.add('active');

            // Show corresponding section
            const section = item.getAttribute('data-section');
            showSection(section);

            // Load section data if needed
            loadSectionData(section);
        });
    });

    // User form related
    document.getElementById('add-user-btn')?.addEventListener('click', () => {
        showUserModal('add');
    });

    document.getElementById('user-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        saveUser();
    });

    document.getElementById('cancel-user-btn')?.addEventListener('click', () => {
        hideUserModal();
    });

    // Token form related
    document.getElementById('generate-token-btn')?.addEventListener('click', () => {
        showTokenModal();
    });

    document.getElementById('token-form')?.addEventListener('submit', (e) => {
        e.preventDefault();
        generateToken();
    });

    document.getElementById('cancel-token-btn')?.addEventListener('click', () => {
        hideTokenModal();
    });

    document.getElementById('copy-token-btn')?.addEventListener('click', () => {
        copyGeneratedToken();
    });

    // Usage statistics filters
    document.getElementById('period-select')?.addEventListener('change', () => {
        loadUsageData();
    });

    document.getElementById('period-count')?.addEventListener('change', () => {
        loadUsageData();
    });

    document.getElementById('username-filter')?.addEventListener('input', debounce(() => {
        loadUsageData();
    }, 300));

    // Search inputs
    document.getElementById('user-search')?.addEventListener('input', debounce(() => {
        filterUserTable();
    }, 300));

    document.getElementById('token-search')?.addEventListener('input', debounce(() => {
        filterTokenTable();
    }, 300));

    // Modal close buttons
    document.querySelectorAll('.modal .close').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            closeBtn.closest('.modal').style.display = 'none';
        });
    });

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

// Show specific admin section
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.admin-section').forEach(section => {
        section.classList.remove('active');
    });

    // Show requested section
    const section = document.getElementById(`${sectionId}-section`);
    if (section) {
        section.classList.add('active');
    }
}

// Load section data based on section ID
function loadSectionData(sectionId) {
    switch (sectionId) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'users':
            loadUsersData();
            break;
        case 'tokens':
            loadTokensData();
            break;
        case 'usage':
            loadUsageData();
            break;
    }
}

// Dashboard data functions
async function loadDashboardData() {
    if (!window.auth.isAuthenticated() || !window.auth.isAdmin()) return;

    try {
        // Load summary statistics
        await loadSummaryStatistics();

        // Load usage trend chart
        await loadUsageTrendChart();

        // Load recent activity
        await loadRecentActivity();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

async function loadSummaryStatistics() {
    try {
        // Example API call - replace with actual endpoint
        const response = await fetch('/usage/admin/summary', {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const data = await response.json();

            // Update UI elements
            document.getElementById('total-users').textContent = data.total_users || '--';
            document.getElementById('active-users').textContent = data.active_users_today || '--';
            document.getElementById('api-requests').textContent = formatNumber(data.api_requests_today) || '--';
            document.getElementById('total-tokens').textContent = formatNumber(data.total_tokens_today) || '--';
        } else {
            console.error('Failed to load summary statistics');
        }
    } catch (error) {
        console.error('Error loading summary statistics:', error);
    }
}

async function loadUsageTrendChart() {
    try {
        // Get data from the statistics API
        const response = await fetch('/usage/admin/all/day?num_periods=30', {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const allUsersData = await response.json();
            // Extract all usage data points from all users
            let combinedData = [];

            // Check if we have users data
            if (allUsersData.users && Array.isArray(allUsersData.users)) {
                // For each user, extract their statistics
                allUsersData.users.forEach(user => {
                    if (user.statistics && Array.isArray(user.statistics)) {
                        combinedData = combinedData.concat(user.statistics);
                    }
                });
            }

            renderUsageTrendChart(combinedData);
        } else {
            console.error('Failed to load usage trend data');
        }
    } catch (error) {
        console.error('Error loading usage trend chart:', error);
    }
}

// Render usage trend chart with real data
function renderUsageTrendChart(data) {
    const usageTrendChartElement = document.getElementById('usage-trend-chart');
    if (!usageTrendChartElement) {
        console.error('Usage trend chart element not found in DOM');
        return;
    }

    // Set explicit dimensions for the chart
    usageTrendChartElement.style.height = '300px';
    usageTrendChartElement.style.width = '100%';

    const ctx = usageTrendChartElement.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context from canvas');
        return;
    }

    // Handle empty data
    if (!Array.isArray(data) || data.length === 0) {
        console.warn('No usage trend data available to render chart');
        // Display a message on the canvas
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText('No usage trend data available', usageTrendChartElement.width / 2, usageTrendChartElement.height / 2);
        return;
    }

    try {
        // Group data by period_start to merge data from multiple users
        const dataByPeriod = {};
        data.forEach(item => {
            const periodDate = item.period_start;
            if (!dataByPeriod[periodDate]) {
                dataByPeriod[periodDate] = {
                    period_start: periodDate,
                    request_count: 0,
                    total_tokens: 0
                };
            }
            dataByPeriod[periodDate].request_count += item.request_count || 0;
            dataByPeriod[periodDate].total_tokens += item.total_tokens || 0;
        });

        // Convert back to array and sort by date
        const aggregatedData = Object.values(dataByPeriod);
        aggregatedData.sort((a, b) => new Date(a.period_start) - new Date(b.period_start));

        // Format data for the chart
        const labels = aggregatedData.map(item => new Date(item.period_start).toLocaleDateString('zh-TW', { timeZone: 'Asia/Taipei' }));
        const requestData = aggregatedData.map(item => item.request_count || 0);
        const tokenData = aggregatedData.map(item => item.total_tokens || 0);

        // Destroy existing chart if it exists
        if (usageTrendChart) {
            usageTrendChart.destroy();
        }

        // Create new chart
        usageTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'API Requests',
                        data: requestData,
                        borderColor: 'rgba(63, 55, 201, 1)',
                        backgroundColor: 'rgba(63, 55, 201, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        yAxisID: 'requests'
                    },
                    {
                        label: 'Tokens Used',
                        data: tokenData,
                        borderColor: 'rgba(76, 201, 240, 1)',
                        backgroundColor: 'rgba(76, 201, 240, 0.1)',
                        borderWidth: 2,
                        tension: 0.3,
                        fill: true,
                        yAxisID: 'tokens'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    requests: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'API Requests'
                        },
                        grid: {
                            display: false
                        }
                    },
                    tokens: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Tokens Used'
                        },
                        grid: {
                            display: true
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating usage trend chart:', error);
        // Clear the canvas and show error message or fall back to demo data
    }
}

async function loadRecentActivity() {
    try {
        // Example API call - replace with actual endpoint
        const response = await fetch('/usage/admin/recent', {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const activities = await response.json();

            // Clear loading message
            const tbody = document.getElementById('recent-activity-body');
            tbody.innerHTML = '';

            // Add activities to table
            activities.forEach(activity => {
                const row = document.createElement('tr');

                row.innerHTML = `
                    <td>${formatDateTime(activity.timestamp)}</td>
                    <td>${activity.username}</td>
                    <td>${activity.action}</td>
                    <td>${activity.details}</td>
                `;

                tbody.appendChild(row);
            });
        } else {
            console.error('Failed to load recent activity');
        }
    } catch (error) {
        console.error('Error loading recent activity:', error);
    }
}

// User management functions
async function loadUsersData() {
    if (!window.auth.isAuthenticated() || !window.auth.isAdmin()) return;

    try {
        // Example API call - replace with actual endpoint
        const response = await fetch('/admin/users', {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const users = await response.json();

            // Clear loading message
            const tbody = document.getElementById('users-table-body');
            tbody.innerHTML = '';

            // Add users to table
            users.forEach(user => {
                const row = document.createElement('tr');

                const statusClass = user.disabled ? 'status-disabled' : 'status-active';
                const statusText = user.disabled ? 'Disabled' : 'Active';
                const scopes = (user.scopes || []).join(', ') || '-';

                row.innerHTML = `
                    <td title="${user.username}">${user.username}</td>
                    <td title="${user.email || '-'}">${user.email || '-'}</td>
                    <td title="${user.full_name || '-'}">${user.full_name || '-'}</td>
                    <td><span class="${statusClass}">${statusText}</span></td>
                    <td title="${scopes}">${scopes}</td>
                    <td class="table-actions">
                        <button class="action-btn edit-user" data-username="${user.username}">Edit</button>
                        <button class="action-btn delete action-delete-user" data-username="${user.username}">Delete</button>
                    </td>
                `;

                tbody.appendChild(row);
            });

            // Add event listeners to action buttons
            attachUserActionListeners();
        } else {
            console.error('Failed to load users data');
        }
    } catch (error) {
        console.error('Error loading users data:', error);
    }
}

// Token management functions
async function loadTokensData() {
    if (!window.auth.isAuthenticated() || !window.auth.isAdmin()) return;

    try {
        // Fetch tokens data from API
        const response = await fetch('/admin/tokens', {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const tokens = await response.json();

            // Clear loading message
            const tbody = document.getElementById('tokens-table-body');
            tbody.innerHTML = '';

            // Add tokens to table
            tokens.forEach(token => {
                const row = document.createElement('tr');

                // Format dates
                const lastRefresh = token.last_refresh ? formatDateTime(token.last_refresh) : 'Never';
                const nextRefresh = token.next_refresh_required ? formatDateTime(token.next_refresh_required) : 'N/A';

                row.innerHTML = `
                    <td title="${token.username}">${token.username}</td>
                    <td title="${lastRefresh}">${lastRefresh}</td>
                    <td title="${nextRefresh}">${nextRefresh}</td>
                    <td>${token.token_type || 'Bearer'}</td>
                    <td class="table-actions">
                        <button class="action-btn refresh-token" data-username="${token.username}">Refresh</button>
                        <button class="action-btn delete action-revoke-token" data-username="${token.username}" data-token-id="${token.id}">Revoke</button>
                    </td>
                `;

                tbody.appendChild(row);
            });

            // Add event listeners to action buttons
            attachTokenActionListeners();

            // Populate token username select for the token generation modal
            populateTokenUsernameSelect(tokens);
        } else {
            console.error('Failed to load tokens data');

            // Show error message in table
            const tbody = document.getElementById('tokens-table-body');
            tbody.innerHTML = '<tr><td colspan="5">Failed to load token data</td></tr>';
        }
    } catch (error) {
        console.error('Error loading tokens data:', error);

        // Show error message in table
        const tbody = document.getElementById('tokens-table-body');
        tbody.innerHTML = '<tr><td colspan="5">Error loading token data</td></tr>';
    }
}

// Populate token username select dropdown
function populateTokenUsernameSelect(tokens = []) {
    const select = document.getElementById('token-username');
    if (!select) return;

    // Clear existing options
    // select.innerHTML = '';

    // Get unique usernames from tokens
    const usernames = [...new Set(tokens.map(token => token.username))];

    // Add options for each username
    usernames.forEach(username => {
        const option = document.createElement('option');
        option.value = username;
        option.textContent = username;
        select.appendChild(option);
    });
}

// Helper Functions
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    // Parse as UTC and convert to Asia/Taipei timezone
    const utcDate = new Date(dateString);
    // Adjust for UTC+8 
    const taipeiDate = new Date(utcDate.getTime() + (8 * 60 * 60 * 1000));
    return taipeiDate.toLocaleString('zh-TW');
}

// User Form Related Functions
// Show user modal for add or edit operations
function showUserModal(mode, username = null) {
    const modal = document.getElementById('user-modal');
    const modalTitle = document.getElementById('user-modal-title');
    const form = document.getElementById('user-form');

    // Clear any previous errors
    document.getElementById('user-form-error').textContent = '';

    // Reset form
    form.reset();

    if (mode === 'edit' && username) {
        // Set title for edit mode
        modalTitle.textContent = 'Edit User';

        // Fetch user data and populate form
        fetchUserData(username);
    } else {
        // Set title for add mode
        modalTitle.textContent = 'Add New User';

        // Clear any previous user ID
        document.getElementById('form-user-id').value = '';
    }

    // Show modal
    modal.style.display = 'flex';
}

// Hide the user modal
function hideUserModal() {
    const modal = document.getElementById('user-modal');
    modal.style.display = 'none';
}

// Fetch user data for editing
async function fetchUserData(username) {
    try {
        const response = await fetch(`/admin/users/${username}`, {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const user = await response.json();

            // Populate form fields
            document.getElementById('form-username').value = user.username;
            document.getElementById('form-email').value = user.email || '';
            document.getElementById('form-full-name').value = user.full_name || '';
            document.getElementById('form-disabled').checked = user.disabled || false;
            document.getElementById('form-scopes').value = (user.scopes || []).join(',');

            // Store user ID in hidden field (useful for some API implementations)
            document.getElementById('form-user-id').value = user.id || user.username;

            // Disable username field in edit mode to prevent changing it
            document.getElementById('form-username').readOnly = true;
        } else {
            const errorDiv = document.getElementById('user-form-error');
            errorDiv.textContent = 'Failed to fetch user data';
        }
    } catch (error) {
        console.error('Error fetching user data:', error);
        const errorDiv = document.getElementById('user-form-error');
        errorDiv.textContent = 'An error occurred while fetching user data';
    }
}

// Save user data (create or update)
async function saveUser() {
    try {
        const form = document.getElementById('user-form');
        const errorDiv = document.getElementById('user-form-error');

        // Clear previous errors
        errorDiv.textContent = '';

        // Get form data
        const formData = new FormData(form);
        const userId = document.getElementById('form-user-id').value;

        // Convert form data to JSON object
        const userData = {
            username: formData.get('username'),
            email: formData.get('email') || null,
            full_name: formData.get('full_name') || null,
            disabled: formData.get('disabled') === 'on',
            scopes: formData.get('scopes') ? formData.get('scopes').split(',').map(s => s.trim()).filter(Boolean) : []
        };

        // Add password only if provided (to avoid changing it when not intended)
        const password = formData.get('password');
        if (password) {
            userData.password = password;
        }

        // Determine if this is an update or create operation
        const isUpdate = !!userId;
        const url = isUpdate ? `/admin/users/${userId}` : '/admin/users';
        const method = isUpdate ? 'PUT' : 'POST';

        // Make API request
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.auth.getToken()}`
            },
            body: JSON.stringify(userData)
        });

        if (response.ok) {
            // Success - close modal and reload users
            hideUserModal();
            loadUsersData();
        } else {
            // Failed - show error
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            errorDiv.textContent = errorData.detail || 'Failed to save user';
        }
    } catch (error) {
        console.error('Error saving user:', error);
        const errorDiv = document.getElementById('user-form-error');
        errorDiv.textContent = 'An error occurred while saving user data';
    }
}

// Delete user confirmation and execution
async function deleteUser(username) {
    if (!username) return;

    // Confirm before deleting
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/admin/users/${username}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            // Success - reload users
            loadUsersData();
        } else {
            // Failed - show error
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            alert(`Failed to delete user: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('An error occurred while deleting the user');
    }
}

// Usage statistics functions
async function loadUsageData() {
    if (!window.auth.isAuthenticated() || !window.auth.isAdmin()) return;

    try {
        // Get filter values
        const period = document.getElementById('period-select').value || 'month';
        const numPeriods = document.getElementById('period-count').value || '30';
        const usernameFilter = document.getElementById('username-filter').value || '';

        // Build API endpoint with filters
        let endpoint = `/usage/admin/all/${period}?num_periods=${numPeriods}`;
        if (usernameFilter) {
            endpoint += `&username=${encodeURIComponent(usernameFilter)}`;
        }

        // Fetch usage statistics
        const response = await fetch(endpoint, {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const usageData = await response.json();

            // Render usage chart
            renderUsageChart(usageData);

            // Update usage table
            updateUsageTable(usageData);
        } else {
            console.error('Failed to load usage statistics');

            // Show error message in chart
            const chartElement = document.getElementById('admin-usage-chart');
            if (chartElement) {
                const ctx = chartElement.getContext('2d');
                ctx.font = '16px Arial';
                ctx.fillStyle = '#666';
                ctx.textAlign = 'center';
                ctx.fillText('Failed to load usage data', chartElement.width / 2, chartElement.height / 2);
            }

            // Show error message in table
            const tbody = document.getElementById('usage-table-body');
            tbody.innerHTML = '<tr><td colspan="6">Failed to load usage data</td></tr>';
        }
    } catch (error) {
        console.error('Error loading usage statistics:', error);

        // Show error message in chart and table
        const chartElement = document.getElementById('admin-usage-chart');
        if (chartElement) {
            const ctx = chartElement.getContext('2d');
            ctx.font = '16px Arial';
            ctx.fillStyle = '#666';
            ctx.textAlign = 'center';
            ctx.fillText('Error loading usage data', chartElement.width / 2, chartElement.height / 2);
        }

        const tbody = document.getElementById('usage-table-body');
        tbody.innerHTML = '<tr><td colspan="6">Error loading usage data</td></tr>';
    }
}

// Render usage chart with data
function renderUsageChart(data) {
    const chartElement = document.getElementById('admin-usage-chart');
    if (!chartElement) {
        console.error('Usage chart element not found in DOM');
        return;
    }

    // Set explicit dimensions for the chart
    chartElement.style.height = '300px';
    chartElement.style.width = '100%';

    const ctx = chartElement.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context from canvas');
        return;
    }

    // Destroy existing chart if it exists
    if (adminUsageChart) {
        adminUsageChart.destroy();
    }

    // Extract users and calculate total usage by user
    const users = data.users || [];

    if (users.length === 0) {
        // No data to display
        ctx.font = '16px Arial';
        ctx.fillStyle = '#666';
        ctx.textAlign = 'center';
        ctx.fillText('No usage data available', chartElement.width / 2, chartElement.height / 2);
        return;
    }

    // Calculate total usage by user
    const userTotals = {};
    users.forEach(user => {
        userTotals[user.user_id] = (user.statistics || []).reduce(
            (sum, stat) => sum + (stat.total_tokens || 0), 0
        );
    });

    // Sort users by total usage
    const sortedUsers = Object.keys(userTotals).sort((a, b) => userTotals[b] - userTotals[a]);

    // Take top 10 users for the chart
    const topUsers = sortedUsers.slice(0, 10);

    // Prepare chart data
    const labels = topUsers;
    const tokenData = topUsers.map(userId => userTotals[userId]);

    // Color palette for the chart
    const colorPalette = [
        'rgba(63, 55, 201, 0.8)',
        'rgba(76, 201, 240, 0.8)',
        'rgba(94, 190, 140, 0.8)',
        'rgba(247, 185, 72, 0.8)',
        'rgba(236, 100, 75, 0.8)',
        'rgba(176, 84, 185, 0.8)',
        'rgba(86, 128, 233, 0.8)',
        'rgba(52, 170, 188, 0.8)',
        'rgba(141, 191, 117, 0.8)',
        'rgba(240, 152, 46, 0.8)'
    ];

    // Create chart
    adminUsageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Total Tokens',
                data: tokenData,
                backgroundColor: colorPalette,
                borderColor: colorPalette.map(color => color.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Total Tokens'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'User ID'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        title: function (tooltipItems) {
                            // Try to get a readable user identifier
                            const userId = tooltipItems[0].label;
                            return `User: ${userId}`;
                        },
                        label: function (context) {
                            return `Total Tokens: ${formatNumber(context.raw)}`;
                        }
                    }
                }
            }
        }
    });
}

// Update usage table with data
function updateUsageTable(data) {
    const tbody = document.getElementById('usage-table-body');
    if (!tbody) return;

    // Clear existing table content
    tbody.innerHTML = '';

    // Extract users
    const users = data.users || [];

    if (users.length === 0) {
        // No data to display
        tbody.innerHTML = '<tr><td colspan="6">No usage data available</td></tr>';
        return;
    }

    // Calculate total usage by user
    users.forEach(user => {
        const row = document.createElement('tr');

        // Calculate totals
        let totalTokens = 0;
        let totalPromptTokens = 0;
        let totalCompletionTokens = 0;
        let totalRequests = 0;

        (user.statistics || []).forEach(stat => {
            totalTokens += stat.total_tokens || 0;
            totalPromptTokens += stat.prompt_tokens || 0;
            totalCompletionTokens += stat.completion_tokens || 0;
            totalRequests += stat.request_count || 0;
        });

        // Prepare formatted values with title attributes for tooltips
        const formattedTotalTokens = formatNumber(totalTokens);
        const formattedPromptTokens = formatNumber(totalPromptTokens);
        const formattedCompletionTokens = formatNumber(totalCompletionTokens);
        const formattedRequests = formatNumber(totalRequests);

        // Create row
        row.innerHTML = `
            <td title="${user.user_id}">${user.user_id}</td>
            <td title="${formattedTotalTokens}">${formattedTotalTokens}</td>
            <td title="${formattedPromptTokens}">${formattedPromptTokens}</td>
            <td title="${formattedCompletionTokens}">${formattedCompletionTokens}</td>
            <td title="${formattedRequests}">${formattedRequests}</td>
            <td class="table-actions">
                <button class="action-btn view-user-details" data-user-id="${user.user_id}">Details</button>
            </td>
        `;

        tbody.appendChild(row);
    });

    // Add event listeners to view details buttons
    document.querySelectorAll('.view-user-details').forEach(button => {
        button.addEventListener('click', () => {
            const userId = button.getAttribute('data-user-id');
            viewUserDetails(userId);
        });
    });
}

// View detailed usage for a specific user
function viewUserDetails(userId) {
    if (!userId) return;

    // For this implementation, we'll simply redirect to the filtered view
    document.getElementById('username-filter').value = userId;
    loadUsageData();
}

// User table action listeners
function attachUserActionListeners() {
    // Get all edit user buttons
    const editButtons = document.querySelectorAll('.edit-user');
    editButtons.forEach(button => {
        button.addEventListener('click', function () {
            const username = this.getAttribute('data-username');
            showUserModal('edit', username);
        });
    });

    // Get all delete user buttons
    const deleteButtons = document.querySelectorAll('.action-delete-user');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function () {
            const username = this.getAttribute('data-username');
            deleteUser(username);
        });
    });
}

// Token management functions
async function loadTokensData() {
    if (!window.auth.isAuthenticated() || !window.auth.isAdmin()) return;

    try {
        // Fetch tokens data from API
        const response = await fetch('/admin/tokens', {
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            const tokens = await response.json();

            // Clear loading message
            const tbody = document.getElementById('tokens-table-body');
            tbody.innerHTML = '';

            // Add tokens to table
            tokens.forEach(token => {
                const row = document.createElement('tr');

                // Format dates
                const lastRefresh = token.last_refresh ? formatDateTime(token.last_refresh) : 'Never';
                const nextRefresh = token.next_refresh_required ? formatDateTime(token.next_refresh_required) : 'N/A';

                row.innerHTML = `
                    <td title="${token.username}">${token.username}</td>
                    <td title="${lastRefresh}">${lastRefresh}</td>
                    <td title="${nextRefresh}">${nextRefresh}</td>
                    <td>${token.token_type || 'Bearer'}</td>
                    <td class="table-actions">
                        <button class="action-btn refresh-token" data-username="${token.username}">Refresh</button>
                        <button class="action-btn delete action-revoke-token" data-username="${token.username}" data-token-id="${token.id}">Revoke</button>
                    </td>
                `;

                tbody.appendChild(row);
            });

            // Add event listeners to action buttons
            attachTokenActionListeners();

            // Populate token username select for the token generation modal
            populateTokenUsernameSelect(tokens);
        } else {
            console.error('Failed to load tokens data');

            // Show error message in table
            const tbody = document.getElementById('tokens-table-body');
            tbody.innerHTML = '<tr><td colspan="5">Failed to load token data</td></tr>';
        }
    } catch (error) {
        console.error('Error loading tokens data:', error);

        // Show error message in table
        const tbody = document.getElementById('tokens-table-body');
        tbody.innerHTML = '<tr><td colspan="5">Error loading token data</td></tr>';
    }
}

// Refresh token for a user
async function refreshToken(username) {
    if (!username) return;

    try {
        // Pre-fill the scopes field with blank (will be updated with token data)
        const scopesInput = document.getElementById('token-scopes');
        if (scopesInput) scopesInput.value = '';

        // Make the API request to refresh the token
        const response = await fetch(`/admin/token/${username}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            // Show the refreshed token in the token-result modal
            const tokenData = await response.json();
            const token = tokenData.access_token || tokenData.token;
            const expires = tokenData.expires_at
                ? formatDateTime(tokenData.expires_at)
                : (tokenData.expires_in ? `in ${tokenData.expires_in} seconds` : 'Never');

            // Fetch user data to get scopes
            try {
                const userResponse = await fetch(`/admin/users/${username}`, {
                    headers: {
                        'Authorization': `Bearer ${window.auth.getToken()}`
                    }
                });

                if (userResponse.ok) {
                    const userData = await userResponse.json();
                    // Update scopes field with user scopes
                    if (scopesInput && userData.scopes) {
                        scopesInput.value = (userData.scopes || []).join(',');
                    }
                }
            } catch (error) {
                console.error('Error fetching user scopes:', error);
            }

            // Fill modal fields
            document.getElementById('token-username').value = username;
            document.getElementById('generated-token').value = token;
            document.getElementById('token-type').textContent = tokenData.token_type || 'Bearer';
            document.getElementById('token-expires').textContent = expires;
            document.getElementById('token-result').style.display = 'block';
            document.getElementById('token-modal').style.display = 'flex';

            // Reload tokens table in background
            loadTokensData();
        } else {
            // Failed - show error
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            alert(`Failed to refresh token: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error refreshing token:', error);
        alert('An error occurred while refreshing the token');
    }
}

// Revoke token
async function revokeToken(username, tokenId) {
    if (!username) return;

    // Confirm before revoking
    if (!confirm(`Are you sure you want to revoke the token for "${username}"? This action cannot be undone.`)) {
        return;
    }

    try {
        // For token revocation, we'll use the username since our API doesn't support token_id yet
        const response = await fetch(`/admin/token/${username}/revoke`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });

        if (response.ok) {
            // Success - reload tokens
            loadTokensData();
        } else {
            // Failed - show error
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            alert(`Failed to revoke token: ${errorData.detail || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error revoking token:', error);
        alert('An error occurred while revoking the token');
    }
}

// Show token modal for generation
function showTokenModal() {
    const modal = document.getElementById('token-modal');
    const form = document.getElementById('token-form');
    const resultDiv = document.getElementById('token-result');

    // Reset form and hide result
    form.reset();
    resultDiv.style.display = 'none';
    document.getElementById('token-form-error').textContent = '';

    // If we don't have tokens data yet, load it to populate the username select
    if (document.getElementById('token-username').options.length === 0) {
        loadTokensData();
    }

    // Show modal
    modal.style.display = 'flex';
}

// Hide the token modal
function hideTokenModal() {
    const modal = document.getElementById('token-modal');
    modal.style.display = 'none';
}

// Generate token from form
async function generateToken() {
    try {
        const form = document.getElementById('token-form');
        const errorDiv = document.getElementById('token-form-error');
        const resultDiv = document.getElementById('token-result');

        // Clear previous errors
        errorDiv.textContent = '';

        // Get form data
        const formData = new FormData(form);

        // Get username from form
        const username = formData.get('username');

        // Create request data
        const requestData = {
            username: username
        };

        // Add scopes if provided
        const scopes = formData.get('scopes');
        if (scopes) {
            requestData.scopes = scopes.split(',').map(s => s.trim()).filter(Boolean);
        }

        // Make API request to the token generation endpoint
        const response = await fetch(`/admin/token/${username}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.auth.getToken()}`
            },
            body: JSON.stringify(requestData)
        });

        if (response.ok) {
            // Success - show token
            const tokenData = await response.json();

            // Display token
            document.getElementById('generated-token').value = tokenData.access_token || tokenData.token;
            document.getElementById('token-type').textContent = tokenData.token_type || 'Bearer';
            document.getElementById('token-expires').textContent = tokenData.expires_at
                ? formatDateTime(tokenData.expires_at)
                : (tokenData.expires_in ? `in ${tokenData.expires_in} seconds` : 'Never');

            // Show result div
            resultDiv.style.display = 'block';

            // Reload tokens table in background
            loadTokensData();
        } else {
            // Failed - show error
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            errorDiv.textContent = errorData.detail || 'Failed to generate token';
        }
    } catch (error) {
        console.error('Error generating token:', error);
        const errorDiv = document.getElementById('token-form-error');
        errorDiv.textContent = 'An error occurred while generating the token';
    }
}

// Copy generated token to clipboard
function copyGeneratedToken() {
    const tokenElement = document.getElementById('generated-token');
    tokenElement.select();
    document.execCommand('copy');

    // Visual feedback
    const button = document.getElementById('copy-token-btn');
    const originalText = button.textContent;
    button.textContent = 'Copied!';

    setTimeout(() => {
        button.textContent = originalText;
    }, 2000);
}

// Filter token table based on search input
function filterTokenTable() {
    const searchInput = document.getElementById('token-search').value.toLowerCase();
    const rows = document.querySelectorAll('#tokens-table-body tr');

    rows.forEach(row => {
        const username = row.querySelector('td:first-child')?.textContent.toLowerCase() || '';

        // Show row if username contains the search text
        const isMatch = username.includes(searchInput);
        row.style.display = isMatch ? '' : 'none';
    });
}

// Attach event listeners to token action buttons
function attachTokenActionListeners() {
    // Refresh token buttons
    document.querySelectorAll('.refresh-token').forEach(button => {
        button.addEventListener('click', () => {
            const username = button.getAttribute('data-username');
            refreshToken(username);
        });
    });

    // Revoke token buttons
    document.querySelectorAll('.action-revoke-token').forEach(button => {
        button.addEventListener('click', () => {
            const username = button.getAttribute('data-username');
            const tokenId = button.getAttribute('data-token-id');
            revokeToken(username, tokenId);
        });
    });
}

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function () {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}
