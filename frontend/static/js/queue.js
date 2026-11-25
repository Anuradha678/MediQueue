/**
 * MediQueue – Patient Queue Tracking Script
 * Polls queue status every 3 seconds and updates queue state in real time.
 */

document.addEventListener('DOMContentLoaded', () => {
    const lookupForm = document.getElementById('queueLookupForm');
    const tokenInput = document.getElementById('tokenSearchInput');
    const displayCard = document.getElementById('queueDisplayCard');
    const emptyNotice = document.getElementById('queueEmptyNotice');
    const errorNotice = document.getElementById('queueErrorNotice');
    const trackBtn = document.getElementById('trackSubmitBtn');

    // Display fields
    const dispToken = document.getElementById('dispPatientToken');
    const dispName = document.getElementById('dispPatientName');
    const dispStatusBadge = document.getElementById('dispStatusBadge');
    const dispServing = document.getElementById('dispCurrentServing');
    const dispAhead = document.getElementById('dispPatientsAhead');
    const dispDate = document.getElementById('dispQueueDate');
    const dispWaitTime = document.getElementById('dispEstimatedWait');
    const alertBox = document.getElementById('servingAlertBanner');

    let pollInterval = null;
    let currentToken = '';
    let previousStatus = '';

    // Play subtle audio alert using Web Audio API when patient is called
    function playTurnChime() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = 'sine';
            osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
            osc.frequency.setValueAtTime(880.00, ctx.currentTime + 0.15); // A5
            
            gain.gain.setValueAtTime(0.2, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start();
            osc.stop(ctx.currentTime + 0.6);
        } catch (e) {
            // Audio context may require prior user interaction
        }
    }

    async function fetchQueueData(token, isAutoRefresh = false) {
        if (!token) return;

        try {
            const response = await fetch(`/api/queue/${encodeURIComponent(token)}`);
            const result = await response.json();

            if (response.ok && result.success) {
                const data = result.data;

                // Hide empty & error notices, show display card
                if (emptyNotice) emptyNotice.style.display = 'none';
                if (errorNotice) errorNotice.style.display = 'none';
                displayCard.style.display = 'block';

                // Populate fields
                dispToken.textContent = data.token_number;
                dispName.textContent = data.patient_name;
                dispServing.textContent = data.current_serving;
                dispDate.textContent = data.queue_date;

                // Status Badge
                dispStatusBadge.className = `badge-status badge-${data.status.toLowerCase()}`;
                let statusIcon = 'fa-clock';
                if (data.status === 'Serving') statusIcon = 'fa-stethoscope';
                else if (data.status === 'Completed') statusIcon = 'fa-check-circle';
                else if (data.status === 'Missed') statusIcon = 'fa-times-circle';

                dispStatusBadge.innerHTML = `<i class="fas ${statusIcon}"></i> ${data.status}`;

                // Patients Ahead
                dispAhead.textContent = data.patients_ahead;

                if (dispWaitTime) {
                    dispWaitTime.textContent = data.patients_ahead > 0 
                        ? `~${data.estimated_wait_minutes} mins` 
                        : 'Immediate';
                }

                // Check if patient's turn has arrived
                if (data.status === 'Serving') {
                    if (alertBox) alertBox.style.display = 'block';
                    if (previousStatus !== 'Serving') {
                        playTurnChime();
                        showToast(`It is your turn! Token ${data.token_number} is now being served.`, 'success');
                    }
                } else {
                    if (alertBox) alertBox.style.display = 'none';
                }

                previousStatus = data.status;

                // Stop polling if completed or missed
                if (data.status === 'Completed' || data.status === 'Missed') {
                    if (pollInterval) {
                        clearInterval(pollInterval);
                        pollInterval = null;
                    }
                }
            } else {
                if (!isAutoRefresh) {
                    if (displayCard) displayCard.style.display = 'none';
                    if (emptyNotice) emptyNotice.style.display = 'none';
                    if (errorNotice) {
                        errorNotice.style.display = 'block';
                        const errMsg = document.getElementById('queueErrorMessage');
                        if (errMsg) errMsg.textContent = result.error || 'Token not found.';
                    }
                    showToast(result.error || 'Token not found.', 'error');
                }
            }
        } catch (err) {
            if (!isAutoRefresh) {
                showToast('Unable to reach server. Please check your connection.', 'error');
            }
        }
    }

    function startTracking(token) {
        currentToken = token.trim().toUpperCase();
        if (!currentToken) return;

        // Reset previous interval
        if (pollInterval) clearInterval(pollInterval);

        // Fetch immediately
        fetchQueueData(currentToken, false);

        // Poll every 3 seconds
        pollInterval = setInterval(() => {
            fetchQueueData(currentToken, true);
        }, 3000);
    }

    if (lookupForm) {
        lookupForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const token = tokenInput.value.trim().toUpperCase();
            if (!token) {
                showToast('Please enter your token number.', 'warning');
                return;
            }
            startTracking(token);
        });
    }

    // Check URL parameters for ?token=MQ-001
    const urlParams = new URLSearchParams(window.location.search);
    const initialToken = urlParams.get('token');
    if (initialToken) {
        tokenInput.value = initialToken.trim().toUpperCase();
        startTracking(initialToken);
    }
});
