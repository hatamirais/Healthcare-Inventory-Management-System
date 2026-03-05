/**
 * Healthcare IMS - Application JavaScript (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    initSidebarCollapse();
    initAlertDismiss();
    initDeleteConfirmation();
    initRowKeyboardFocus();
});

/** Sidebar toggle for mobile */
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggleBtn = document.getElementById('sidebarToggleMobile');
    const closeBtn = document.getElementById('sidebarToggle');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('show');
        if (overlay) overlay.classList.add('show');
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('show');
        if (overlay) overlay.classList.remove('show');
    }

    if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);
}

/** Enable keyboard focus on table rows for quicker navigation */
function initRowKeyboardFocus() {
    document.querySelectorAll('.table tbody tr').forEach((tr) => {
        tr.setAttribute('tabindex', '0');
        tr.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const link = tr.querySelector('a');
                if (link) link.click();
            }
        });
    });
}

/** Sidebar collapse toggle for desktop */
function initSidebarCollapse() {
    const sidebar = document.getElementById('sidebar');
    const pageWrapper = document.getElementById('page-content-wrapper');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');

    if (!sidebar || !collapseBtn) return;

    // Restore saved state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        sidebar.classList.add('collapsed');
        if (pageWrapper) pageWrapper.classList.add('sidebar-collapsed');
    }

    collapseBtn.addEventListener('click', () => {
        const isCollapsed = sidebar.classList.toggle('collapsed');
        if (pageWrapper) pageWrapper.classList.toggle('sidebar-collapsed', isCollapsed);
        localStorage.setItem('sidebarCollapsed', isCollapsed);
        // Ensure any dropdown toggle that should be active keeps the active
        // appearance after collapsing/expanding. When collapsed the server-side
        // active class may be present on child links but not on the parent
        // toggle; this sync will add/remove `.active` on the toggle where
        // appropriate so the icon doesn't look dimmed.
        syncDropdownActiveStates(sidebar);
    });
}

function syncDropdownActiveStates(sidebar) {
    if (!sidebar) return;
    sidebar.querySelectorAll('.sidebar-dropdown-toggle').forEach(toggle => {
        const target = document.querySelector(toggle.getAttribute('data-bs-target'));
        if (!target) return;
        // If any child link is active or submenu is shown, mark the toggle active
        const shouldBeActive = target.querySelector('.sidebar-link.active') !== null || target.classList.contains('show');
        toggle.classList.toggle('active', shouldBeActive);
    });
}

// Run once on load to correct any mismatched active state
document.addEventListener('DOMContentLoaded', () => {
    syncDropdownActiveStates(document.getElementById('sidebar'));
});


/** Auto-dismiss alerts after 5 seconds */
function initAlertDismiss() {
    document.querySelectorAll('.alert-dismissible').forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });
}

/** Confirm before deleting */
function initDeleteConfirmation() {
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            const message = el.getAttribute('data-confirm') || 'Apakah Anda yakin ingin menghapus?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * Utility: Format number to Indonesian locale
 */
function formatNumber(num) {
    return new Intl.NumberFormat('id-ID').format(num);
}

/**
 * Utility: Format currency (IDR)
 */
function formatCurrency(num) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
    }).format(num);
}
