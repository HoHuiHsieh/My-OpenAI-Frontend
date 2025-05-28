// Portal functionality

document.addEventListener('DOMContentLoaded', () => {
    setupPortalListeners();
});

// Setup event listeners for portal buttons
function setupPortalListeners() {
    // Add click listener to all portal buttons
    const portalButtons = document.querySelectorAll('.portal-button');
    portalButtons.forEach(button => {
        button.addEventListener('click', () => {
            const service = button.getAttribute('data-service');
            if (service) {
                navigateToService(service);
            }
        });
    });
}

// Navigate to selected service
function navigateToService(service) {
    // Check if user is authenticated
    if (!window.auth.isAuthenticated()) {
        showLoginModal();
        return;
    }
    
    // Handle navigation to different services
    switch(service) {
        // case 'example':
        //     window.location.href = 'example.html';
        //     break;
        default:
            console.error('Unknown service:', service);
    }
}
