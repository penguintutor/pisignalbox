document.addEventListener('DOMContentLoaded', () => {
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const sidebar = document.getElementById('sidebar-menu');
    const overlay = document.getElementById('menu-overlay');

    function toggleMenu() {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('open');
    }

    // Open menu on button click
    if (hamburgerBtn) {
        hamburgerBtn.addEventListener('click', toggleMenu);
    }

    // Close menu when clicking outside of it (on the dark overlay)
    if (overlay) {
        overlay.addEventListener('click', toggleMenu);
    }
});

// Function to display the toast pop-up
function showToast(message, type = 'success', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Choose icon based on type
    let icon = '✓';
    if (type === 'error') icon = '✕';
    if (type === 'info') icon = 'ℹ';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
        <button type="button" class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
        toast.classList.add('toast-hiding');
        toast.addEventListener('transitionend', () => toast.remove());
    }, duration);
}

// Automatically check URL arguments on page load
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);

    // Maps friendly short codes (e.g., ?status=added)
    const statusMessages = {
        'added': { text: 'User added successfully.', type: 'success' },
        'updated': { text: 'User details updated.', type: 'success' },
        'deleted': { text: 'User permanently deleted.', type: 'success' },
        'error': { text: 'An error occurred. Please try again.', type: 'error' }
    };

    const status = params.get('status');
    const customMsg = params.get('msg');
    const msgType = params.get('type') || 'success';

    let messageToShow = null;
    let typeToShow = msgType;

    if (customMsg) {
        messageToShow = customMsg;
    } else if (status && statusMessages[status]) {
        messageToShow = statusMessages[status].text;
        typeToShow = statusMessages[status].type;
    }

    if (messageToShow) {
        showToast(messageToShow, typeToShow);

        // Clean up the URL in the address bar without reloading
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    }
});

function handleEditClick(button) {
    const { username, fullname, email, role } = button.dataset;
    openEditUserModal(username, fullname, email, role);
}