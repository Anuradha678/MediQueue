/**
 * MediQueue – Doctor Dashboard Script
 * Manages live queue retrieval, patient actions (Next, Complete, Missed, Re-queue),
 * live search filtering, status tab filtering, and logout.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Stats elements
    const statTotal = document.getElementById('statTotalPatients');
    const statWaiting = document.getElementById('statWaitingPatients');
    const statCompleted = document.getElementById('statCompletedPatients');
    const statMissed = document.getElementById('statMissedPatients');

    // Current patient elements
    const currentTokenEl = document.getElementById('currentServingToken');
    const currentNameEl = document.getElementById('currentPatientName');
    const currentPhoneEl = document.getElementById('currentPatientPhone');
    const currentActionsBox = document.getElementById('currentActionsBox');

    // Controls
    const btnNextPatient = document.getElementById('btnNextPatient');
    const btnCompleteCurrent = document.getElementById('btnCompleteCurrent');
    const btnMissedCurrent = document.getElementById('btnMissedCurrent');
    const btnManualRefresh = document.getElementById('btnManualRefresh');
    const btnLogout = document.getElementById('btnLogout');
    const searchInput = document.getElementById('queueSearchInput');
    const filterPills = document.querySelectorAll('.filter-pill');

    // Table elements
    const queueTableBody = document.getElementById('queueTableBody');
    const emptyState = document.getElementById('tableEmptyState');
    const lastUpdatedEl = document.getElementById('lastUpdatedTime');

    let allPatients = [];
    let activeFilter = 'all';
    let currentServingPatient = null;
    let autoRefreshTimer = null;
    let isRequestInProgress = false;

    // Load full dashboard data
    async function loadDashboard(showFeedback = false) {
        if (isRequestInProgress) return;
        isRequestInProgress = true;

        if (btnManualRefresh && showFeedback) {
            btnManualRefresh.querySelector('i').classList.add('spin-icon');
        }

        try {
            const response = await fetch('/api/dashboard');
            
            if (response.status === 401) {
                // Unauthorized session expired
                window.location.href = '/login';
                return;
            }

            const result = await response.json();

            if (response.ok && result.success) {
                const data = result.data;

                // Update Stats
                statTotal.textContent = data.stats.total;
                statWaiting.textContent = data.stats.waiting;
                statCompleted.textContent = data.stats.completed;
                statMissed.textContent = data.stats.missed;

                // Update Current Patient Section
                currentServingPatient = data.current_serving;
                updateCurrentPatientView(currentServingPatient);

                // Update Patients Table
                allPatients = data.patients || [];
                renderTable();

                // Update Timestamp
                const now = new Date();
                lastUpdatedEl.textContent = `Updated at ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;

                if (showFeedback) {
                    showToast('Dashboard data refreshed.', 'success');
                }
            } else {
                if (showFeedback) showToast(result.error || 'Failed to refresh.', 'error');
            }
        } catch (err) {
            if (showFeedback) showToast('Network connection error.', 'error');
        } finally {
            isRequestInProgress = false;
            if (btnManualRefresh) {
                btnManualRefresh.querySelector('i').classList.remove('spin-icon');
            }
        }
    }

    function updateCurrentPatientView(patient) {
        if (patient) {
            currentTokenEl.textContent = patient.token_number;
            currentNameEl.textContent = patient.patient_name;
            currentPhoneEl.textContent = patient.phone ? `Phone: ${patient.phone}` : '';
            
            if (btnCompleteCurrent) btnCompleteCurrent.style.display = 'inline-flex';
            if (btnMissedCurrent) btnMissedCurrent.style.display = 'inline-flex';
        } else {
            currentTokenEl.textContent = 'None';
            currentNameEl.textContent = 'No patient currently being served';
            currentPhoneEl.textContent = 'Click "Next Patient" to call the earliest waiting patient.';
            
            if (btnCompleteCurrent) btnCompleteCurrent.style.display = 'none';
            if (btnMissedCurrent) btnMissedCurrent.style.display = 'none';
        }
    }

    function renderTable() {
        const query = searchInput ? searchInput.value.trim().toLowerCase() : '';

        const filtered = allPatients.filter(patient => {
            // Filter by search query
            const matchesQuery = !query || 
                patient.token_number.toLowerCase().includes(query) ||
                patient.patient_name.toLowerCase().includes(query) ||
                (patient.phone && patient.phone.toLowerCase().includes(query));

            // Filter by status tab
            const matchesStatus = (activeFilter === 'all') || 
                (patient.status.toLowerCase() === activeFilter.toLowerCase());

            return matchesQuery && matchesStatus;
        });

        if (filtered.length === 0) {
            queueTableBody.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';

        queueTableBody.innerHTML = filtered.map(p => {
            const statusLower = p.status.toLowerCase();
            let statusIcon = 'fa-clock';
            if (p.status === 'Serving') statusIcon = 'fa-stethoscope';
            else if (p.status === 'Completed') statusIcon = 'fa-check-circle';
            else if (p.status === 'Missed') statusIcon = 'fa-times-circle';

            // Action buttons depending on state
            let actionsHtml = '';
            if (p.status === 'Serving') {
                actionsHtml = `
                    <button class="btn btn-sm btn-success" onclick="completePatient(${p.id}, '${p.token_number}')" title="Complete Consultation">
                        <i class="fas fa-check"></i> Complete
                    </button>
                    <button class="btn btn-sm btn-outline" style="color: #DC2626; border-color: #FECACA;" onclick="markMissed(${p.id}, '${p.token_number}')" title="Mark as Missed">
                        <i class="fas fa-user-slash"></i> Missed
                    </button>
                `;
            } else if (p.status === 'Waiting') {
                actionsHtml = `
                    <button class="btn btn-sm btn-outline" style="color: #DC2626; border-color: #FECACA;" onclick="markMissed(${p.id}, '${p.token_number}')" title="Mark as Missed">
                        <i class="fas fa-user-slash"></i> Missed
                    </button>
                `;
            } else if (p.status === 'Missed') {
                actionsHtml = `
                    <button class="btn btn-sm btn-outline-primary" onclick="requeuePatient(${p.id}, '${p.token_number}')" title="Re-queue as Waiting">
                        <i class="fas fa-redo"></i> Re-queue
                    </button>
                `;
            } else {
                // Completed
                actionsHtml = `<span style="color: #94A3B8; font-size: 0.85rem;"><i class="fas fa-check-double"></i> Finished</span>`;
            }

            // Format timestamp
            let regTime = p.created_at;
            if (regTime && regTime.length > 10) {
                try {
                    const d = new Date(regTime);
                    if (!isNaN(d.getTime())) {
                        regTime = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    }
                } catch (e) {}
            }

            return `
                <tr>
                    <td><span class="table-token-badge">${p.token_number}</span></td>
                    <td style="font-weight: 600; color: var(--secondary);">${p.patient_name}</td>
                    <td style="color: var(--text-muted);">${p.phone || 'N/A'}</td>
                    <td style="color: var(--text-muted); font-size: 0.875rem;">${regTime}</td>
                    <td>
                        <span class="badge-status badge-${statusLower}">
                            <i class="fas ${statusIcon}"></i> ${p.status}
                        </span>
                    </td>
                    <td>
                        <div class="table-actions">
                            ${actionsHtml}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Call Next Patient
    if (btnNextPatient) {
        btnNextPatient.addEventListener('click', async () => {
            btnNextPatient.disabled = true;
            const originalContent = btnNextPatient.innerHTML;
            btnNextPatient.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Calling Next...';

            try {
                const response = await fetch('/api/next-patient', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await response.json();

                if (response.ok && result.success) {
                    showToast(result.message, result.current_serving ? 'success' : 'info');
                    loadDashboard();
                } else {
                    showToast(result.error || 'Failed to advance queue.', 'error');
                }
            } catch (err) {
                showToast('Network error while advancing queue.', 'error');
            } finally {
                btnNextPatient.disabled = false;
                btnNextPatient.innerHTML = originalContent;
            }
        });
    }

    // Complete Current Serving Patient
    if (btnCompleteCurrent) {
        btnCompleteCurrent.addEventListener('click', () => {
            if (currentServingPatient) {
                completePatient(currentServingPatient.id, currentServingPatient.token_number);
            }
        });
    }

    // Mark Current Patient as Missed
    if (btnMissedCurrent) {
        btnMissedCurrent.addEventListener('click', () => {
            if (currentServingPatient) {
                markMissed(currentServingPatient.id, currentServingPatient.token_number);
            }
        });
    }

    // Global action functions exposed for inline onclick handlers
    window.completePatient = async function(patientId, tokenNumber) {
        if (!confirm(`Mark token ${tokenNumber} consultation as Completed?`)) return;

        try {
            const response = await fetch('/api/complete-patient', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patient_id: patientId, token_number: tokenNumber })
            });
            const result = await response.json();
            if (response.ok && result.success) {
                showToast(result.message, 'success');
                loadDashboard();
            } else {
                showToast(result.error || 'Failed to complete patient.', 'error');
            }
        } catch (err) {
            showToast('Network error completing patient.', 'error');
        }
    };

    window.markMissed = async function(patientId, tokenNumber) {
        if (!confirm(`Mark token ${tokenNumber} as Missed?`)) return;

        try {
            const response = await fetch('/api/mark-missed', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patient_id: patientId, token_number: tokenNumber })
            });
            const result = await response.json();
            if (response.ok && result.success) {
                showToast(result.message, 'warning');
                loadDashboard();
            } else {
                showToast(result.error || 'Failed to mark patient as missed.', 'error');
            }
        } catch (err) {
            showToast('Network error marking patient missed.', 'error');
        }
    };

    window.requeuePatient = async function(patientId, tokenNumber) {
        try {
            const response = await fetch('/api/requeue-patient', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ patient_id: patientId, token_number: tokenNumber })
            });
            const result = await response.json();
            if (response.ok && result.success) {
                showToast(result.message, 'success');
                loadDashboard();
            } else {
                showToast(result.error || 'Failed to re-queue patient.', 'error');
            }
        } catch (err) {
            showToast('Network error re-queueing patient.', 'error');
        }
    };

    // Filter Tabs
    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            activeFilter = pill.getAttribute('data-filter') || 'all';
            renderTable();
        });
    });

    // Search Input
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            renderTable();
        });
    }

    // Manual Refresh
    if (btnManualRefresh) {
        btnManualRefresh.addEventListener('click', () => {
            loadDashboard(true);
        });
    }

    // Doctor Logout
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to log out of MediQueue?')) return;

            try {
                const response = await fetch('/api/logout', { method: 'POST' });
                if (response.ok) {
                    showToast('Logged out successfully.', 'success');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 400);
                }
            } catch (err) {
                window.location.href = '/login';
            }
        });
    }

    // Initial Load & Auto Refresh every 4 seconds
    loadDashboard(false);
    autoRefreshTimer = setInterval(() => {
        loadDashboard(false);
    }, 4000);
});
