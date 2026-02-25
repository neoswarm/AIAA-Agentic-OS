/**
 * AIAA Dashboard - Settings JavaScript
 * Handles API key management, preferences, and profile settings
 */

// ==============================================================================
// Tab Navigation
// ==============================================================================

/**
 * Switch between settings tabs (API Keys, Preferences, Profile)
 * @param {string} tabName - Tab identifier to activate
 */
function switchSettingsTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.settings-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab panels
    document.querySelectorAll('.settings-tab-panel').forEach(panel => {
        panel.classList.toggle('hidden', panel.id !== `tab-${tabName}`);
    });

    // Update URL without reload
    updateQueryParams({ tab: tabName });
}

// ==============================================================================
// API Key Management
// ==============================================================================

/**
 * Save an API key by name
 * Validates the key with the backend before saving
 * @param {string} keyName - Key identifier (e.g., 'OPENROUTER_API_KEY')
 * @param {string} keyValue - The API key value
 */
async function saveApiKey(keyName, keyValue) {
    if (!keyValue || keyValue.trim() === '') {
        showToast('Please enter a valid API key.', 'warning');
        return;
    }

    const saveBtn = document.querySelector(`[data-save-key="${keyName}"]`);
    if (saveBtn) {
        setButtonLoading(saveBtn, true, 'Saving...');
    }

    try {
        await fetchAPI('/api/v2/settings/api-keys', {
            method: 'POST',
            body: JSON.stringify({
                key_name: keyName,
                key_value: keyValue.trim()
            })
        });

        showToast(`${formatKeyName(keyName)} saved successfully.`, 'success');
        updateKeyStatusIndicator(keyName, 'valid');

        // Hide the input form, show the masked value
        const inputGroup = document.getElementById(`key-input-${keyName}`);
        if (inputGroup) {
            inputGroup.classList.add('hidden');
        }
        const display = document.getElementById(`key-display-${keyName}`);
        if (display) {
            display.classList.remove('hidden');
            const maskedEl = display.querySelector('.key-masked');
            if (maskedEl) {
                maskedEl.textContent = maskApiKey(keyValue.trim());
            }
        }
    } catch (error) {
        showToast(`Failed to save key: ${error.message}`, 'error');
        updateKeyStatusIndicator(keyName, 'error');
    } finally {
        if (saveBtn) {
            setButtonLoading(saveBtn, false);
        }
    }
}

/**
 * Test an API key by triggering backend validation
 * @param {string} keyName - Key identifier to test
 */
async function testApiKey(keyName) {
    const testBtn = document.querySelector(`[data-test-key="${keyName}"]`);
    if (testBtn) {
        setButtonLoading(testBtn, true, 'Testing...');
    }

    try {
        const data = await fetchAPI('/api/v2/settings/api-keys', {
            method: 'POST',
            body: JSON.stringify({
                key_name: keyName,
                action: 'test'
            })
        });

        if (data.valid) {
            showToast(`${formatKeyName(keyName)} is valid!`, 'success');
            updateKeyStatusIndicator(keyName, 'valid');
        } else {
            showToast(`${formatKeyName(keyName)} validation failed: ${data.message || 'Invalid key'}`, 'error');
            updateKeyStatusIndicator(keyName, 'invalid');
        }
    } catch (error) {
        showToast(`Test failed: ${error.message}`, 'error');
        updateKeyStatusIndicator(keyName, 'error');
    } finally {
        if (testBtn) {
            setButtonLoading(testBtn, false);
        }
    }
}

/**
 * Load the status of all API keys (configured, valid, missing)
 */
async function loadApiKeyStatus() {
    try {
        const data = await fetchAPI('/api/v2/settings/api-keys/status');
        const keys = data.keys || {};

        for (const [keyName, status] of Object.entries(keys)) {
            updateKeyStatusIndicator(keyName, status.configured ? 'configured' : 'missing');

            // Update display with masked value if configured
            const display = document.getElementById(`key-display-${keyName}`);
            if (display && status.configured) {
                display.classList.remove('hidden');
                const maskedEl = display.querySelector('.key-masked');
                if (maskedEl) {
                    maskedEl.textContent = status.redacted_value || '***configured***';
                }
                const inputGroup = document.getElementById(`key-input-${keyName}`);
                if (inputGroup) {
                    inputGroup.classList.add('hidden');
                }
            }
        }
    } catch (error) {
        showToast('Failed to load API key status.', 'error');
    }
}

/**
 * Update the visual status indicator for an API key
 * @param {string} keyName - Key identifier
 * @param {string} status - Status: 'valid', 'invalid', 'error', 'missing', 'configured'
 */
function updateKeyStatusIndicator(keyName, status) {
    const indicator = document.getElementById(`key-status-${keyName}`);
    if (!indicator) return;

    indicator.className = 'key-status-indicator';
    indicator.classList.add(`key-status-${status}`);

    switch (status) {
        case 'valid':
        case 'configured':
            indicator.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> Valid';
            break;
        case 'invalid':
            indicator.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Invalid';
            break;
        case 'error':
            indicator.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> Error';
            break;
        case 'missing':
        default:
            indicator.innerHTML = 'Not configured';
            break;
    }
}

/**
 * Show the API key input form for editing
 * @param {string} keyName - Key identifier
 */
function showKeyInput(keyName) {
    const display = document.getElementById(`key-display-${keyName}`);
    const inputGroup = document.getElementById(`key-input-${keyName}`);

    if (display) display.classList.add('hidden');
    if (inputGroup) {
        inputGroup.classList.remove('hidden');
        const input = inputGroup.querySelector('input');
        if (input) {
            input.value = '';
            input.focus();
        }
    }
}

/**
 * Hide the API key input form
 * @param {string} keyName - Key identifier
 */
function cancelKeyEdit(keyName) {
    const display = document.getElementById(`key-display-${keyName}`);
    const inputGroup = document.getElementById(`key-input-${keyName}`);

    if (inputGroup) inputGroup.classList.add('hidden');
    if (display) display.classList.remove('hidden');
}

/**
 * Handle Enter key press on API key input fields
 * @param {KeyboardEvent} event - The keyboard event
 * @param {string} keyName - Key identifier
 */
function handleKeyInput(event, keyName) {
    if (event.key === 'Enter') {
        event.preventDefault();
        const input = event.target;
        saveApiKey(keyName, input.value);
    }
}

// ==============================================================================
// Preferences
// ==============================================================================

/**
 * Collect preference form values and save them
 */
async function savePreferences() {
    const form = document.getElementById('preferences-form');
    if (!form) return;

    const saveBtn = document.getElementById('save-preferences-btn');
    if (saveBtn) {
        setButtonLoading(saveBtn, true, 'Saving...');
    }

    const prefs = getFormData(form);

    try {
        await fetchAPI('/api/v2/settings/preferences', {
            method: 'POST',
            body: JSON.stringify(prefs)
        });
        showToast('Preferences saved.', 'success');
    } catch (error) {
        showToast(`Failed to save preferences: ${error.message}`, 'error');
    } finally {
        if (saveBtn) {
            setButtonLoading(saveBtn, false);
        }
    }
}

/**
 * Load saved preferences and populate the form
 */
async function loadPreferences() {
    const form = document.getElementById('preferences-form');
    if (!form) return;

    try {
        const data = await fetchAPI('/api/v2/settings/preferences');
        if (data.preferences) {
            setFormData(form, data.preferences);
        }
    } catch (error) {
        // Preferences may not exist yet, that's fine
    }
}

// ==============================================================================
// Profile
// ==============================================================================

/**
 * Save profile information
 */
async function saveProfile() {
    const form = document.getElementById('profile-form');
    if (!form) return;

    const saveBtn = document.getElementById('save-profile-btn');
    if (saveBtn) {
        setButtonLoading(saveBtn, true, 'Saving...');
    }

    const profileData = getFormData(form);

    try {
        await fetchAPI('/api/v2/settings/profile', {
            method: 'POST',
            body: JSON.stringify(profileData)
        });
        showToast('Profile saved.', 'success');
    } catch (error) {
        showToast(`Failed to save profile: ${error.message}`, 'error');
    } finally {
        if (saveBtn) {
            setButtonLoading(saveBtn, false);
        }
    }
}

// ==============================================================================
// Utility
// ==============================================================================

/**
 * Mask an API key for display (show first 6 and last 4 chars)
 * @param {string} key - The full API key
 * @returns {string} - Masked key string
 */
function maskApiKey(key) {
    if (!key || key.length < 12) return '***';
    return key.substring(0, 6) + '***...' + key.substring(key.length - 4);
}

/**
 * Format a key name for display (e.g., "OPENROUTER_API_KEY" -> "OpenRouter API Key")
 * @param {string} name - Raw key name
 * @returns {string} - Formatted name
 */
function formatKeyName(name) {
    return name
        .replace(/_/g, ' ')
        .replace(/\bAPI\b/g, 'API')
        .replace(/\bURL\b/g, 'URL')
        .toLowerCase()
        .replace(/\b\w/g, c => c.toUpperCase())
        .replace(/\bApi\b/g, 'API')
        .replace(/\bUrl\b/g, 'URL');
}

// ==============================================================================
// Init on page load
// ==============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the settings page
    const settingsContainer = document.getElementById('settings-container');
    if (!settingsContainer) return;

    // Initialize tab from URL or default to 'api-keys'
    const params = getQueryParams();
    const activeTab = params.tab || 'api-keys';
    switchSettingsTab(activeTab);

    // Bind tab buttons
    document.querySelectorAll('.settings-tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            switchSettingsTab(this.dataset.tab);
        });
    });

    // Load API key status
    loadApiKeyStatus();

    // Load preferences
    loadPreferences();
});

// ==============================================================================
// Export for global use
// ==============================================================================

window.switchSettingsTab = switchSettingsTab;
window.saveApiKey = saveApiKey;
window.testApiKey = testApiKey;
window.loadApiKeyStatus = loadApiKeyStatus;
window.showKeyInput = showKeyInput;
window.cancelKeyEdit = cancelKeyEdit;
window.handleKeyInput = handleKeyInput;
window.savePreferences = savePreferences;
window.saveProfile = saveProfile;
