/**
 * AIAA Dashboard - Onboarding Wizard JavaScript
 * Handles multi-step onboarding: role selection, API key setup, first task
 */

// ==============================================================================
// Wizard State
// ==============================================================================

/** @type {number} Current wizard step (1-based) */
let currentStep = 1;

/** @type {number} Total number of wizard steps */
const totalSteps = 4;

/** @type {string|null} Selected user role */
let selectedRole = null;

/** @type {boolean} Whether the API key has been validated */
let keyValidated = false;

// ==============================================================================
// Step Navigation
// ==============================================================================

/**
 * Navigate to a specific wizard step
 * Shows the target step div, hides others, updates progress dots
 * @param {number} step - Step number to navigate to (1-based)
 */
function goToStep(step) {
    if (step < 1 || step > totalSteps) return;

    // Hide all steps
    document.querySelectorAll('.onboarding-step').forEach(el => {
        el.classList.add('hidden');
    });

    // Show target step
    const targetStep = document.querySelector(`.onboarding-step[data-step="${step}"]`);
    if (targetStep) {
        targetStep.classList.remove('hidden');
    }

    currentStep = step;
    updateProgressDots();
    updateNavigationButtons();
}

/**
 * Move to the next wizard step
 */
function nextStep() {
    // Validate current step before proceeding
    if (!validateCurrentStep()) return;
    goToStep(currentStep + 1);
}

/**
 * Move to the previous wizard step
 */
function prevStep() {
    goToStep(currentStep - 1);
}

/**
 * Validate the current step before allowing navigation forward
 * @returns {boolean} - Whether the current step is valid
 */
function validateCurrentStep() {
    switch (currentStep) {
        case 1:
            if (!selectedRole) {
                showToast('Please select your role to continue.', 'warning');
                return false;
            }
            return true;

        case 2:
            if (!keyValidated) {
                showToast('Please validate your API key before continuing.', 'warning');
                return false;
            }
            return true;

        case 3:
            // First task selection — no validation needed, handled by task click
            return true;

        default:
            return true;
    }
}

// ==============================================================================
// Progress Dots
// ==============================================================================

/**
 * Update the visual progress dots to reflect the current step
 */
function updateProgressDots() {
    document.querySelectorAll('.progress-dot').forEach((dot, index) => {
        const stepNum = index + 1;
        dot.classList.remove('active', 'completed');

        if (stepNum < currentStep) {
            dot.classList.add('completed');
        } else if (stepNum === currentStep) {
            dot.classList.add('active');
        }
    });

    // Update progress text if present
    const progressText = document.getElementById('onboarding-progress-text');
    if (progressText) {
        progressText.textContent = `Step ${currentStep} of ${totalSteps}`;
    }
}

/**
 * Update the visibility and state of navigation buttons
 */
function updateNavigationButtons() {
    const prevBtn = document.getElementById('onboarding-prev-btn');
    const nextBtn = document.getElementById('onboarding-next-btn');

    if (prevBtn) {
        prevBtn.classList.toggle('hidden', currentStep === 1);
    }

    if (nextBtn) {
        // Hide next on the last step and on the task-selection step
        nextBtn.classList.toggle('hidden', currentStep === totalSteps || currentStep === 3);
    }
}

// ==============================================================================
// Step 1: Role Selection
// ==============================================================================

/**
 * Handle role card selection
 * Highlights the selected card and stores the role
 * @param {string} role - Selected role identifier
 */
function selectRole(role) {
    selectedRole = role;

    // Update card highlighting
    document.querySelectorAll('.role-card').forEach(card => {
        card.classList.toggle('selected', card.dataset.role === role);
    });

    // Auto-advance after a brief delay
    setTimeout(() => nextStep(), 300);
}

// ==============================================================================
// Step 2: API Key Validation
// ==============================================================================

/** @type {Function} Debounced API key validation */
const debouncedValidateKey = debounce(function(value) {
    if (value && value.trim().length > 10) {
        validateApiKey(value.trim());
    } else {
        resetKeyValidation();
    }
}, 500);

/**
 * Validate the entered API key against the backend
 * @param {string} keyValue - API key to validate
 */
async function validateApiKey(keyValue) {
    const statusEl = document.getElementById('key-validation-status');
    const validateBtn = document.getElementById('validate-key-btn');

    if (statusEl) {
        statusEl.className = 'key-validation-status validating';
        statusEl.innerHTML = '<div class="spinner-small"></div> Validating...';
    }
    if (validateBtn) {
        setButtonLoading(validateBtn, true, 'Validating...');
    }

    try {
        const data = await fetchAPI('/api/v2/settings/api-keys', {
            method: 'POST',
            body: JSON.stringify({
                key_name: 'openrouter',
                key_value: keyValue
            })
        });

        if (data.status === 'ok' || data.valid) {
            keyValidated = true;
            if (statusEl) {
                statusEl.className = 'key-validation-status valid';
                statusEl.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Key is valid! You\'re connected.';
            }
        } else {
            keyValidated = false;
            if (statusEl) {
                statusEl.className = 'key-validation-status invalid';
                statusEl.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Invalid key. Please check and try again.';
            }
        }
    } catch (error) {
        keyValidated = false;
        if (statusEl) {
            statusEl.className = 'key-validation-status error';
            statusEl.innerHTML = 'Validation failed. Please try again.';
        }
        showToast('Could not validate key. Check your connection.', 'error');
    } finally {
        if (validateBtn) {
            setButtonLoading(validateBtn, false);
        }
    }
}

/**
 * Reset the key validation status display
 */
function resetKeyValidation() {
    keyValidated = false;
    const statusEl = document.getElementById('key-validation-status');
    if (statusEl) {
        statusEl.className = 'key-validation-status';
        statusEl.innerHTML = '';
    }
}

/**
 * Handle the validate button click
 */
function handleValidateClick() {
    const input = document.getElementById('onboarding-api-key-input');
    if (input && input.value.trim()) {
        validateApiKey(input.value.trim());
    } else {
        showToast('Please paste your API key first.', 'warning');
    }
}

// ==============================================================================
// Step 3: First Task Selection
// ==============================================================================

/**
 * Handle first task card selection
 * Stores role preference, then redirects to skill execution page
 * @param {string} skillName - The skill to execute as first task
 */
async function selectFirstTask(skillName) {
    // Save role preference if we have one
    if (selectedRole) {
        try {
            await fetchAPI('/api/v2/settings/preferences', {
                method: 'POST',
                body: JSON.stringify({ role: selectedRole })
            });
        } catch (error) {
            // Non-critical, don't block
        }
    }

    // Mark onboarding as completed
    try {
        await fetchAPI('/api/v2/settings/preferences', {
            method: 'POST',
            body: JSON.stringify({ onboarding_completed: true })
        });
    } catch (error) {
        // Non-critical
    }

    // Redirect to skill execution
    window.location.href = `/skills/${encodeURIComponent(skillName)}/run`;
}

/**
 * Skip the first task and go to the dashboard
 */
function skipFirstTask() {
    // Mark onboarding completed
    fetchAPI('/api/v2/settings/preferences', {
        method: 'POST',
        body: JSON.stringify({ onboarding_completed: true })
    }).catch(() => {});

    window.location.href = '/home';
}

// ==============================================================================
// Step 4: Success / Completion
// ==============================================================================

/**
 * Navigate to a destination from the success step
 * @param {string} destination - URL to navigate to
 */
function navigateFromSuccess(destination) {
    window.location.href = destination;
}

// ==============================================================================
// Init on page load
// ==============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the onboarding page
    const onboardingContainer = document.getElementById('onboarding-container');
    if (!onboardingContainer) return;

    // Initialize at step 1
    goToStep(1);

    // Bind role cards
    document.querySelectorAll('.role-card').forEach(card => {
        card.addEventListener('click', function() {
            selectRole(this.dataset.role);
        });
    });

    // Bind API key input
    const keyInput = document.getElementById('onboarding-api-key-input');
    if (keyInput) {
        keyInput.addEventListener('input', function() {
            debouncedValidateKey(this.value);
        });

        // Also handle paste event for immediate validation
        keyInput.addEventListener('paste', function() {
            setTimeout(() => {
                if (this.value.trim().length > 10) {
                    validateApiKey(this.value.trim());
                }
            }, 100);
        });
    }

    // Bind validate button
    const validateBtn = document.getElementById('validate-key-btn');
    if (validateBtn) {
        validateBtn.addEventListener('click', handleValidateClick);
    }

    // Bind first task cards
    document.querySelectorAll('.first-task-card').forEach(card => {
        card.addEventListener('click', function() {
            selectFirstTask(this.dataset.skill);
        });
    });
});

// ==============================================================================
// Export for global use
// ==============================================================================

window.goToStep = goToStep;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.selectRole = selectRole;
window.validateApiKey = validateApiKey;
window.handleValidateClick = handleValidateClick;
window.selectFirstTask = selectFirstTask;
window.skipFirstTask = skipFirstTask;
window.navigateFromSuccess = navigateFromSuccess;
