// Authentication functionality

// State management for authentication
const authState = {
    isAuthenticated: false,
    accessToken: null,
    username: null,
    isAdmin: false,
    userInfo: null
};

// Check if user is already authenticated on page load
document.addEventListener('DOMContentLoaded', () => {
    // Try to get token from localStorage
    const token = localStorage.getItem('accessToken');
    if (token) {
        authState.accessToken = token;
        validateToken(token);
    } else {
        showLoginRequired();
    }
    
    // Setup event listeners
    setupAuthListeners();
});

// Setup authentication-related event listeners
function setupAuthListeners() {
    // Add event listeners with null checks
    const addSafeClickListener = (id, callback) => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('click', callback);
        } else {
            console.log(`Element with ID "${id}" not found, skipping event listener`);
        }
    };
    
    // Determine current page
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    console.log('Setting up auth listeners for page:', currentPage);
    
    // Common logout button (present on all pages)
    addSafeClickListener('logout-btn', () => {
        logout();
    });
    
    // Index page specific elements
    if (currentPage === 'index.html' || currentPage === '') {
        // Login button
        addSafeClickListener('login-btn', () => {
            showLoginModal();
        });
        
        // Login prompt button
        addSafeClickListener('login-prompt-btn', () => {
            showLoginModal();
        });
        
        // Change password button
        addSafeClickListener('change-password-btn', () => {
            showChangePasswordModal();
        });
        
        // Admin panel button
        addSafeClickListener('admin-panel-btn', () => {
            window.location.href = 'admin.html';
        });
    }
    
    // Only set up modal-related listeners on pages that have the login modal
    const loginForm = document.getElementById('login-form');
    const loginModal = document.getElementById('login-modal');
    
    if (loginModal) {
        // Login form submission
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                login(username, password);
            });
        } else {
            console.log('Element with ID "login-form" not found, skipping event listener');
        }
        
        // Modal close button
        const closeButton = loginModal.querySelector('.close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                hideLoginModal();
            });
        } else {
            console.log('Close button element not found, skipping event listener');
        }
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === loginModal) {
                hideLoginModal();
            }
        });
    }
    
    // Additional global auth-related event listeners can be added here
    
    // Change password modal handling
    const changePasswordForm = document.getElementById('change-password-form');
    const changePasswordModal = document.getElementById('change-password-modal');
    
    if (changePasswordModal) {
        // Change password form submission
        if (changePasswordForm) {
            changePasswordForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const currentPassword = document.getElementById('current-password').value;
                const newPassword = document.getElementById('new-password').value;
                const confirmPassword = document.getElementById('confirm-password').value;
                
                // Validate passwords match
                if (newPassword !== confirmPassword) {
                    document.getElementById('password-change-error').textContent = 'New passwords do not match';
                    return;
                }
                
                changePassword(currentPassword, newPassword);
            });
        }
        
        // Modal close button
        const closeButton = changePasswordModal.querySelector('.close');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                hideChangePasswordModal();
            });
        }
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === changePasswordModal) {
                hideChangePasswordModal();
            }
        });
    }
}

// Show login modal
function showLoginModal() {
    const loginModal = document.getElementById('login-modal');
    if (loginModal) {
        loginModal.style.display = 'block';
    } else {
        console.error('Login modal element not found');
    }
}

// Hide login modal
function hideLoginModal() {
    const loginModal = document.getElementById('login-modal');
    const loginError = document.getElementById('login-error');
    const loginForm = document.getElementById('login-form');
    
    if (loginModal) loginModal.style.display = 'none';
    if (loginError) loginError.textContent = '';
    if (loginForm) loginForm.reset();
}

// Login functionality
async function login(username, password) {
    try {
        // Create form data for the token endpoint
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        
        // Use root-relative URL for API endpoints
        const response = await fetch('/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            // Save token to localStorage
            localStorage.setItem('accessToken', data.access_token);
            
            // Update auth state
            authState.accessToken = data.access_token;
            authState.isAuthenticated = true;
            
            // Get user info
            await getUserInfo();
            
            // Hide modal and update UI
            hideLoginModal();
            updateAuthUI();
        } else {
            const errorData = await response.json();
            document.getElementById('login-error').textContent = errorData.detail || 'Login failed. Please check your credentials.';
        }
    } catch (error) {
        console.error('Login error:', error);
        document.getElementById('login-error').textContent = 'An error occurred during login. Please try again.';
    }
}

// Logout functionality
function logout() {
    console.log('Logging out user:', authState.username);
    
    // Clear auth state
    authState.isAuthenticated = false;
    authState.accessToken = null;
    authState.username = null;
    authState.isAdmin = false; // Reset admin status
    authState.userInfo = null;
    
    // Remove token from localStorage
    localStorage.removeItem('accessToken');
    
    // Update UI
    updateAuthUI();
    showLoginRequired();
    
    console.log('Logout complete, auth state reset');
}

// Get user information
async function getUserInfo() {
    try {
        if (!authState.accessToken) return;
        
        // Use root-relative URL for API endpoints
        const response = await fetch('/users/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authState.accessToken}`
            }
        });
        
        if (response.ok) {
            const userInfo = await response.json();
            authState.username = userInfo.username;
            authState.userInfo = userInfo;
            
            // Check if user has admin scope
            authState.isAdmin = false; // Reset admin status
            if (userInfo.scopes && userInfo.scopes.includes('admin')) {
                authState.isAdmin = true;
                console.log('User has admin privileges:', userInfo.username);
            } else {
                console.log('User does NOT have admin privileges:', userInfo.username, 'Scopes:', userInfo.scopes || []);
            }
            
            return userInfo;
        } else {
            console.error('Failed to get user info');
            // If token is invalid, logout
            if (response.status === 401) {
                logout();
            }
        }
    } catch (error) {
        console.error('Error getting user info:', error);
    }
}

// Validate token
async function validateToken(token) {
    try {
        // Use root-relative URL for API endpoints
        const response = await fetch('/token-info', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Update auth state
            authState.isAuthenticated = true;
            authState.username = data.username;
            
            // Check if scopes are included in token info response
            if (data.scopes && Array.isArray(data.scopes)) {
                authState.isAdmin = data.scopes.includes('admin');
                console.log('Admin status from token info:', authState.isAdmin);
            } else {
                // Reset admin status - we'll get it from getUserInfo with consistent logic
                authState.isAdmin = false;
            }
            
            // Get full user info
            const userInfo = await getUserInfo();
            
            // Update UI
            updateAuthUI();
            
            return userInfo;
        } else {
            console.error('Invalid token');
            logout();
        }
    } catch (error) {
        console.error('Token validation error:', error);
        logout();
    }
}

// Update UI based on authentication state
function updateAuthUI() {
    console.log('Updating UI for authentication state:', authState.isAuthenticated);
    
    // Get UI elements with null checks
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const adminBtn = document.getElementById('admin-panel-btn');
    const usernameDisplay = document.getElementById('username-display');
    const loginRequired = document.getElementById('login-required');
    const authenticatedContent = document.getElementById('authenticated-content');
    
    // Apply styles to elements that exist
    if (authState.isAuthenticated) {
        // User is authenticated
        if (loginBtn) loginBtn.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'inline-block';
        const changePasswordBtn = document.getElementById('change-password-btn');
        if (changePasswordBtn) changePasswordBtn.style.display = 'inline-block';
        if (usernameDisplay) usernameDisplay.textContent = authState.username;
        
        // Show admin button for admin users
        if (adminBtn) adminBtn.style.display = authState.isAdmin ? 'inline-block' : 'none';
        
        // Show authenticated content and hide login required
        if (loginRequired) loginRequired.style.display = 'none';
        if (authenticatedContent) authenticatedContent.style.display = 'block';
        
        // Load user-specific data
        if (typeof loadUsageStatistics === 'function') {
            loadUsageStatistics();
        }
    } else {
        // User is not authenticated
        if (loginBtn) loginBtn.style.display = 'inline-block';
        if (logoutBtn) logoutBtn.style.display = 'none';
        const changePasswordBtn = document.getElementById('change-password-btn');
        if (changePasswordBtn) changePasswordBtn.style.display = 'none';
        if (adminBtn) adminBtn.style.display = 'none';
        if (usernameDisplay) usernameDisplay.textContent = '';
        
        // Hide authenticated content and show login required
        if (loginRequired) loginRequired.style.display = 'flex';
        if (authenticatedContent) authenticatedContent.style.display = 'none';
    }
    
    console.log('UI update complete');
}

// Show login required message
function showLoginRequired() {
    const loginRequired = document.getElementById('login-required');
    const authenticatedContent = document.getElementById('authenticated-content');
    
    if (loginRequired) loginRequired.style.display = 'flex';
    if (authenticatedContent) authenticatedContent.style.display = 'none';
}

// Export auth functions for other scripts
window.auth = {
    getToken: () => authState.accessToken,
    isAuthenticated: () => authState.isAuthenticated,
    isAdmin: () => {
        console.log('isAdmin() called, returning:', authState.isAdmin);
        return authState.isAdmin;
    },
    getUsername: () => authState.username,
    getUserInfo: () => authState.userInfo,
    validateToken: validateToken,
    getAuthState: () => authState
};

// Show change password modal
function showChangePasswordModal() {
    const modal = document.getElementById('change-password-modal');
    if (modal) {
        modal.style.display = 'block';
    } else {
        console.error('Change password modal element not found');
    }
}

// Hide change password modal
function hideChangePasswordModal() {
    const modal = document.getElementById('change-password-modal');
    const errorEl = document.getElementById('password-change-error');
    const successEl = document.getElementById('password-change-success');
    const form = document.getElementById('change-password-form');
    
    if (modal) modal.style.display = 'none';
    if (errorEl) errorEl.textContent = '';
    if (successEl) {
        successEl.textContent = '';
        successEl.style.display = 'none';
    }
    if (form) form.reset();
}

// Change password functionality
async function changePassword(currentPassword, newPassword) {
    try {
        if (!authState.accessToken) {
            document.getElementById('password-change-error').textContent = 'You must be logged in to change your password';
            return;
        }
        
        // Use the /change-password endpoint as specified
        const response = await fetch('/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authState.accessToken}`
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        if (response.ok) {
            const successEl = document.getElementById('password-change-success');
            if (successEl) {
                successEl.textContent = 'Password changed successfully!';
                successEl.style.display = 'block';
            }
            
            // After 3 seconds, close the modal
            setTimeout(() => {
                hideChangePasswordModal();
            }, 3000);
        } else {
            const errorData = await response.json();
            document.getElementById('password-change-error').textContent = 
                errorData.detail || 'Failed to change password. Please check your current password.';
        }
    } catch (error) {
        console.error('Change password error:', error);
        document.getElementById('password-change-error').textContent = 
            'An error occurred while changing your password. Please try again.';
    }
}
