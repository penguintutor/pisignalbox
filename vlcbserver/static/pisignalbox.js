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