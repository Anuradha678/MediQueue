/**
 * MediQueue – Doctor Login Script
 * Handles authentication form submission, password visibility toggle,
 * and redirection to the doctor dashboard upon validation.
 */

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('doctorLoginForm');
    const usernameInput = document.getElementById('loginUsername');
    const passwordInput = document.getElementById('loginPassword');
    const togglePassBtn = document.getElementById('togglePasswordBtn');
    const loginSubmitBtn = document.getElementById('loginSubmitBtn');
    const errorAlert = document.getElementById('loginErrorAlert');

    if (!loginForm) return;

    // Password visibility toggle
    if (togglePassBtn) {
        togglePassBtn.addEventListener('click', () => {
            const isPassword = passwordInput.getAttribute('type') === 'password';
            passwordInput.setAttribute('type', isPassword ? 'text' : 'password');
            const icon = togglePassBtn.querySelector('i');
            if (icon) {
                icon.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
            }
        });
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        if (!username || !password) {
            showError('Please enter both your username and password.');
            return;
        }

        // Disable button & show spinner
        loginSubmitBtn.disabled = true;
        const originalText = loginSubmitBtn.innerHTML;
        loginSubmitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
        hideError();

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showToast('Login successful! Redirecting to dashboard...', 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 600);
            } else {
                showError(result.error || 'Invalid credentials. Please try again.');
                showToast(result.error || 'Login failed.', 'error');
            }
        } catch (err) {
            showError('Server connection error. Please verify the backend is running.');
            showToast('Unable to connect to server.', 'error');
        } finally {
            loginSubmitBtn.disabled = false;
            loginSubmitBtn.innerHTML = originalText;
        }
    });

    function showError(msg) {
        if (errorAlert) {
            errorAlert.textContent = msg;
            errorAlert.style.display = 'block';
        }
    }

    function hideError() {
        if (errorAlert) {
            errorAlert.style.display = 'none';
        }
    }
});
