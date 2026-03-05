/**
 * AIAA Dashboard - Common Utilities
 * Shared JavaScript functions used across all pages
 */

// Inject spinner keyframes if not already present
(function() {
    if (!document.getElementById('aiaa-spinner-styles')) {
        var style = document.createElement('style');
        style.id = 'aiaa-spinner-styles';
        style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
        document.head.appendChild(style);
    }
})();

// ==============================================================================
// Focus Trap Utility (for accessible modals)
// ==============================================================================

/**
 * Trap focus within a modal element.
 * Call on modal open; returns a cleanup function to call on close.
 * @param {HTMLElement} modalElement - The modal container element
 * @returns {Function} cleanup - Call to remove the event listener
 */
function trapFocus(modalElement) {
    var focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    var focusableElements = modalElement.querySelectorAll(focusableSelectors);
    var firstFocusable = focusableElements[0];
    var lastFocusable = focusableElements[focusableElements.length - 1];

    function handleKeydown(e) {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        }
        if (e.key === 'Escape') {
            modalElement.dispatchEvent(new CustomEvent('modal-escape'));
        }
    }

    modalElement.addEventListener('keydown', handleKeydown);

    // Focus first focusable element
    if (firstFocusable) firstFocusable.focus();

    return function cleanup() {
        modalElement.removeEventListener('keydown', handleKeydown);
    };
}


// ==============================================================================
// Toast Notifications
// ==============================================================================

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in ms (default: 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    // Remove existing toasts
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    // Icon based on type
    let icon = '';
    switch (type) {
        case 'success':
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
            break;
        case 'error':
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
            break;
        case 'warning':
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
            break;
        case 'info':
            icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
            break;
    }
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-message">${message}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('toast-show'), 10);
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * Show a toast notification with a retry button
 * @param {string} message - Message to display
 * @param {Function} retryFn - Function to call on retry
 * @param {number} duration - Duration in ms (default: 10000)
 */
function showToastWithRetry(message, retryFn, duration = 10000) {
    // Remove existing toasts
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = 'toast-notification toast-error';

    toast.innerHTML = `
        <div class="toast-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
        </div>
        <div class="toast-content">
            <div class="toast-message">${message}</div>
            <button class="toast-retry-btn" onclick="this.textContent='Retrying...';this.disabled=true;">
                Retry
            </button>
        </div>
        <button class="toast-close" onclick="this.closest('.toast-notification').remove()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
    `;

    // Wire up retry button
    const retryBtn = toast.querySelector('.toast-retry-btn');
    retryBtn.addEventListener('click', function() {
        toast.remove();
        if (typeof retryFn === 'function') retryFn();
    });

    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('toast-show'), 10);

    // Auto remove after longer duration (user may need time to retry)
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.remove('toast-show');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}


// ==============================================================================
// Confirmation Modal
// ==============================================================================

/**
 * Show a confirmation dialog (accessible: focus trap, return focus, Escape key)
 * @param {string} message - Message to display
 * @returns {Promise<boolean>} - Resolves to true if confirmed, false if canceled
 */
function confirmAction(message) {
    return new Promise((resolve) => {
        // Remove existing modal
        const existingModal = document.querySelector('.confirm-modal-overlay');
        if (existingModal) {
            existingModal.remove();
        }

        // Store the element that triggered the modal
        var triggerElement = document.activeElement;

        // Create modal
        const modal = document.createElement('div');
        modal.className = 'confirm-modal-overlay';
        modal.innerHTML = `
            <div class="modal confirm-modal" role="dialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message">
                <div class="modal-header">
                    <span class="modal-title" id="confirm-title">Confirm Action</span>
                </div>
                <div class="modal-body">
                    <p id="confirm-message">${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn-secondary btn" id="confirm-cancel">Cancel</button>
                    <button class="btn" id="confirm-ok">Confirm</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Focus trap
        var focusCleanup = trapFocus(modal.querySelector('.confirm-modal'));

        function close(result) {
            focusCleanup();
            modal.remove();
            // Return focus to trigger element
            if (triggerElement && triggerElement.focus) triggerElement.focus();
            resolve(result);
        }

        modal.querySelector('#confirm-cancel').addEventListener('click', function() { close(false); });
        modal.querySelector('#confirm-ok').addEventListener('click', function() { close(true); });
        modal.addEventListener('click', function(e) {
            if (e.target === modal) close(false);
        });
        modal.querySelector('.confirm-modal').addEventListener('modal-escape', function() { close(false); });
    });
}

/**
 * Close confirmation modal (legacy - kept for backward compatibility)
 * @param {boolean} result - Confirmation result
 */
function closeConfirmModal(result) {
    const modal = document.querySelector('.confirm-modal-overlay');
    if (modal) {
        modal.remove();
    }
    if (window._confirmResolve) {
        window._confirmResolve(result);
        delete window._confirmResolve;
    }
}


// ==============================================================================
// Fetch API Wrapper
// ==============================================================================

/**
 * Fetch API wrapper with error handling, timeout detection, and auto-toast
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options plus custom options:
 *   - timeout {number} - Request timeout in ms (default: 15000)
 *   - showError {boolean} - Auto-show toast on error (default: true)
 *   - retryable {boolean} - Show retry button for network errors (default: true)
 * @returns {Promise<any>} - Response data
 */
async function fetchAPI(url, options = {}) {
    // Extract custom options
    const {
        timeout = 15000,
        showError = true,
        retryable = true,
        ...fetchOptions
    } = options;

    // Set up timeout via AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...fetchOptions.headers
            },
            signal: controller.signal,
            ...fetchOptions
        });

        clearTimeout(timeoutId);
        const data = await response.json();

        if (!response.ok) {
            // Parse structured error format from API v2: {status, message, errors}
            const errorMessage = data.message || data.error || `Request failed (${response.status})`;
            const error = new Error(errorMessage);
            error.status = response.status;
            error.data = data;
            error.fieldErrors = data.errors || null;

            if (showError) {
                showToast(errorMessage, 'error', 5000);
            }
            throw error;
        }

        return data;
    } catch (error) {
        clearTimeout(timeoutId);

        // Network timeout (AbortError from AbortController)
        if (error.name === 'AbortError') {
            const msg = 'Request timed out. Check your connection and try again.';
            if (showError) {
                showToastWithRetry(msg, function() {
                    return fetchAPI(url, options);
                });
            }
            const timeoutError = new Error(msg);
            timeoutError.isTimeout = true;
            throw timeoutError;
        }

        // Network error (fetch failed entirely -- no internet, DNS, CORS)
        if (error instanceof TypeError && error.message.includes('fetch')) {
            const msg = 'Network error. Check your connection and try again.';
            if (showError && retryable) {
                showToastWithRetry(msg, function() {
                    return fetchAPI(url, options);
                });
            } else if (showError) {
                showToast(msg, 'error', 5000);
            }
            const netError = new Error(msg);
            netError.isNetworkError = true;
            throw netError;
        }

        // Already handled API errors (from !response.ok above) -- don't double-toast
        if (error.status) {
            throw error;
        }

        // Unexpected errors
        if (showError) {
            showToast(error.message || 'Something went wrong', 'error');
        }
        throw error;
    }
}


// ==============================================================================
// Date & Time Formatting
// ==============================================================================

/**
 * Format ISO date string to readable format
 * @param {string} isoString - ISO 8601 date string
 * @returns {string} - Formatted date
 */
function formatDate(isoString) {
    if (!isoString) return '-';
    
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    // Less than 1 minute
    if (diff < 60000) {
        return 'Just now';
    }
    
    // Less than 1 hour
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }
    
    // Less than 24 hours
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }
    
    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
    }
    
    // Format as date
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
}

/**
 * Format date to full readable string
 * @param {string} isoString - ISO 8601 date string
 * @returns {string} - Formatted date
 */
function formatDateFull(isoString) {
    if (!isoString) return '-';
    
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}


// ==============================================================================
// Clipboard Utilities
// ==============================================================================

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<void>}
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard', 'success', 2000);
    } catch (error) {
        console.error('Copy failed:', error);
        
        // Fallback method
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            showToast('Copied to clipboard', 'success', 2000);
        } catch (err) {
            showToast('Failed to copy', 'error');
        }
        
        document.body.removeChild(textarea);
    }
}


// ==============================================================================
// Form Utilities
// ==============================================================================

/**
 * Get form data as object
 * @param {HTMLFormElement} form - Form element
 * @returns {Object} - Form data as object
 */
function getFormData(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (const [key, value] of formData.entries()) {
        // Handle checkboxes
        if (form.elements[key].type === 'checkbox') {
            data[key] = form.elements[key].checked;
        } else {
            data[key] = value;
        }
    }
    
    return data;
}

/**
 * Set form data from object
 * @param {HTMLFormElement} form - Form element
 * @param {Object} data - Data object
 */
function setFormData(form, data) {
    for (const [key, value] of Object.entries(data)) {
        const element = form.elements[key];
        if (!element) continue;
        
        if (element.type === 'checkbox') {
            element.checked = Boolean(value);
        } else {
            element.value = value;
        }
    }
}


// ==============================================================================
// URL Utilities
// ==============================================================================

/**
 * Get URL query parameters as object
 * @returns {Object} - Query parameters
 */
function getQueryParams() {
    const params = {};
    const searchParams = new URLSearchParams(window.location.search);
    
    for (const [key, value] of searchParams.entries()) {
        params[key] = value;
    }
    
    return params;
}

/**
 * Update URL query parameters without reload
 * @param {Object} params - Parameters to update
 */
function updateQueryParams(params) {
    const url = new URL(window.location);
    
    for (const [key, value] of Object.entries(params)) {
        if (value === null || value === undefined) {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, value);
        }
    }
    
    window.history.pushState({}, '', url);
}


// ==============================================================================
// Loading States
// ==============================================================================

/**
 * Show loading state on button with proper spinner SVG
 * @param {HTMLElement} button - Button element
 * @param {boolean} loading - Loading state
 * @param {string} loadingText - Text to show while loading
 */
function setButtonLoading(button, loading, loadingText) {
    if (!button) return;
    if (loading) {
        // Store original state for restoration
        button.dataset.originalHTML = button.innerHTML;
        button.dataset.originalDisabled = button.disabled;
        button.disabled = true;
        var text = loadingText || button.dataset.loadingText || 'Loading...';
        button.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation: spin 0.8s linear infinite; margin-right: 0.5rem; flex-shrink: 0;"><circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="12"/></svg>' + text;
    } else {
        button.disabled = button.dataset.originalDisabled === 'true';
        button.innerHTML = button.dataset.originalHTML || button.textContent;
        delete button.dataset.originalHTML;
        delete button.dataset.originalDisabled;
    }
}

/**
 * Wrap an async operation with automatic button loading state management
 * Prevents double-clicks (checks button.disabled) and handles errors (finally block)
 * @param {HTMLElement} button - Button element
 * @param {Function} asyncFn - Async function to execute
 * @param {string} loadingText - Text to show while loading
 * @returns {Promise<any>} - Result of asyncFn
 */
async function withButtonLoading(button, asyncFn, loadingText) {
    if (!button || button.disabled) return;
    setButtonLoading(button, true, loadingText);
    try {
        return await asyncFn();
    } finally {
        setButtonLoading(button, false);
    }
}


// ==============================================================================
// Debounce Utility
// ==============================================================================

/**
 * Debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in ms
 * @returns {Function} - Debounced function
 */
function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}


// ==============================================================================
// Export for use in other scripts
// ==============================================================================

window.trapFocus = trapFocus;
window.showToast = showToast;
window.showToastWithRetry = showToastWithRetry;
window.confirmAction = confirmAction;
window.fetchAPI = fetchAPI;
window.formatDate = formatDate;
window.formatDateFull = formatDateFull;
window.copyToClipboard = copyToClipboard;
window.getFormData = getFormData;
window.setFormData = setFormData;
window.getQueryParams = getQueryParams;
window.updateQueryParams = updateQueryParams;
window.setButtonLoading = setButtonLoading;
window.withButtonLoading = withButtonLoading;
window.debounce = debounce;
