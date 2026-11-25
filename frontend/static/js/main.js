/**
 * MediQueue – Common JavaScript Utilities
 * Handles mobile navbar toggle, toast notifications, and global helpers.
 */

// Global Toast Notification System
function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-info-circle';
    if (type === 'success') iconClass = 'fa-check-circle';
    else if (type === 'error') iconClass = 'fa-exclamation-circle';
    else if (type === 'warning') iconClass = 'fa-exclamation-triangle';

    toast.innerHTML = `
        <i class="fas ${iconClass}" style="font-size: 1.25rem;"></i>
        <div style="flex: 1; font-size: 0.9rem; font-weight: 500;">${message}</div>
        <button type="button" style="background: none; border: none; cursor: pointer; color: #94A3B8; padding: 2px;" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Mobile Menu Navigation Toggle
document.addEventListener('DOMContentLoaded', () => {
    const mobileToggle = document.getElementById('mobileNavToggle');
    const mobileMenu = document.getElementById('mobileNavMenu');

    if (mobileToggle && mobileMenu) {
        mobileToggle.addEventListener('click', () => {
            mobileMenu.classList.toggle('open');
            const icon = mobileToggle.querySelector('i');
            if (icon) {
                if (mobileMenu.classList.contains('open')) {
                    icon.className = 'fas fa-times';
                } else {
                    icon.className = 'fas fa-bars';
                }
            }
        });
    }

    // Home Page Live Queue Snapshot Poller
    const homeServing = document.getElementById('homeServingToken');
    const homeWaiting = document.getElementById('homeWaitingCount');
    const homeTotal = document.getElementById('homeTotalToday');

    if (homeServing || homeWaiting || homeTotal) {
        function updateHomeStats() {
            fetch('/api/public-queue')
                .then(res => res.json())
                .then(data => {
                    if (data.success && data.data) {
                        if (homeServing) homeServing.textContent = data.data.current_serving || 'None';
                        if (homeWaiting) homeWaiting.textContent = data.data.waiting_count;
                        if (homeTotal) homeTotal.textContent = data.data.total_today;
                    }
                })
                .catch(() => {});
        }
        updateHomeStats();
        setInterval(updateHomeStats, 6000);
    }
});
