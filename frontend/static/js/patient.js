/**
 * MediQueue – Patient Registration Script
 * Validates patient form inputs, requests token generation from backend,
 * and presents the confirmation token slip.
 */

document.addEventListener('DOMContentLoaded', () => {
    const regForm = document.getElementById('patientRegistrationForm');
    const formCard = document.getElementById('registrationFormCard');
    const tokenCard = document.getElementById('tokenConfirmationCard');
    const submitBtn = document.getElementById('submitRegBtn');
    const nameInput = document.getElementById('patientName');
    const phoneInput = document.getElementById('patientPhone');
    const nameError = document.getElementById('nameError');
    const phoneError = document.getElementById('phoneError');
    const resetBtn = document.getElementById('registerAnotherBtn');

    if (!regForm) return;

    // Validation patterns
    const nameRegex = /^[^\W\d_][\w\s.'’-]{1,99}$/u;
    const phoneRegex = /^\+?[0-9\s\-()]{7,20}$/;

    function validateName() {
        const val = nameInput.value.trim();
        if (!val) {
            nameInput.classList.add('is-invalid');
            nameError.textContent = 'Full name is required.';
            return false;
        }
        if (!nameRegex.test(val)) {
            nameInput.classList.add('is-invalid');
            nameError.textContent = 'Name should contain only letters and spaces (min 2 characters).';
            return false;
        }
        nameInput.classList.remove('is-invalid');
        nameError.textContent = '';
        return true;
    }

    function validatePhone() {
        const val = phoneInput.value.trim();
        if (!val) {
            phoneInput.classList.add('is-invalid');
            phoneError.textContent = 'Phone number is required.';
            return false;
        }
        if (!phoneRegex.test(val) || (val.match(/[0-9]/g) || []).length < 7) {
            phoneInput.classList.add('is-invalid');
            phoneError.textContent = 'Please enter a valid phone number (at least 7 digits).';
            return false;
        }
        phoneInput.classList.remove('is-invalid');
        phoneError.textContent = '';
        return true;
    }

    nameInput.addEventListener('input', validateName);
    phoneInput.addEventListener('input', validatePhone);

    regForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const isNameValid = validateName();
        const isPhoneValid = validatePhone();

        if (!isNameValid || !isPhoneValid) {
            showToast('Please fix the errors in the form before submitting.', 'error');
            return;
        }

        // Lock button during submission
        submitBtn.disabled = true;
        const originalBtnContent = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Token...';

        try {
            const response = await fetch('/api/register-patient', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    patient_name: nameInput.value.trim(),
                    phone: phoneInput.value.trim()
                })
            });

            const result = await response.json().catch(() => ({ success: false, error: 'The server returned an unreadable response. Check the Flask terminal for details.' }));

            if (response.ok && result.success) {
                const patientData = result.data;
                
                // Populate Confirmation Card
                document.getElementById('confTokenNumber').textContent = patientData.token_number;
                document.getElementById('confPatientName').textContent = patientData.patient_name;
                document.getElementById('confQueueDate').textContent = patientData.queue_date;
                document.getElementById('confStatus').textContent = patientData.status;
                document.getElementById('confPatientsAhead').textContent = patientData.patients_ahead;

                // Setup Track My Queue button
                const trackBtn = document.getElementById('confTrackBtn');
                if (trackBtn) {
                    trackBtn.href = `/track-queue?token=${encodeURIComponent(patientData.token_number)}`;
                }

                // Transition UI views
                formCard.style.display = 'none';
                tokenCard.style.display = 'block';

                showToast(`Token ${patientData.token_number} generated successfully!`, 'success');
            } else {
                showToast(result.error || 'Registration failed. Please try again.', 'error');
            }
        } catch (error) {
            console.error('Patient registration request failed:', error);
            showToast('Could not contact the server. Make sure Flask is running, then try again.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnContent;
        }
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            regForm.reset();
            nameInput.classList.remove('is-invalid');
            phoneInput.classList.remove('is-invalid');
            nameError.textContent = '';
            phoneError.textContent = '';
            tokenCard.style.display = 'none';
            formCard.style.display = 'block';
        });
    }
});
