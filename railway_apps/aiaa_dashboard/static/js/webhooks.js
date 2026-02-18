/**
 * AIAA Dashboard - Webhooks JavaScript
 * Handles webhook management, testing, and monitoring
 */

// ==============================================================================
// Webhook Stats
// ==============================================================================

/**
 * Load webhook statistics from API
 */
async function loadWebhookStats() {
    try {
        const data = await fetchAPI('/api/webhook-workflows');
        const webhooks = data.webhook_workflows || [];
        
        // Update stats
        const totalWebhooks = webhooks.length;
        const activeWebhooks = webhooks.filter(w => w.enabled).length;
        
        document.getElementById('total-webhooks').textContent = totalWebhooks;
        document.getElementById('active-webhooks').textContent = activeWebhooks;
        
        // TODO: Get actual call stats from API
        document.getElementById('total-calls').textContent = '-';
        document.getElementById('success-rate').textContent = '-';
        
    } catch (error) {
        console.error('Failed to load webhook stats:', error);
    }
}


// ==============================================================================
// Webhook Actions
// ==============================================================================

/**
 * Copy webhook URL to clipboard
 * @param {string} url - Webhook URL to copy
 */
function copyWebhookUrl(url) {
    copyToClipboard(url);
}

/**
 * Test a webhook by sending a test payload
 * @param {string} slug - Webhook slug
 * @param {string} name - Webhook name
 */
async function testWebhook(slug, name) {
    try {
        showToast(`Testing ${name}...`, 'info');
        
        const response = await fetchAPI('/api/webhook-workflows/test', {
            method: 'POST',
            body: JSON.stringify({ slug })
        });
        
        if (response.test_status === 'success') {
            showToast(`✓ ${name} test successful (${response.status_code})`, 'success');
        } else {
            showToast(`✗ ${name} test failed`, 'error');
        }
        
    } catch (error) {
        showToast(`Test failed: ${error.message}`, 'error');
    }
}

/**
 * Toggle webhook enabled state
 * @param {string} slug - Webhook slug
 * @param {boolean} currentState - Current enabled state
 */
async function toggleWebhook(slug, currentState) {
    try {
        const action = currentState ? 'Disabling' : 'Enabling';
        showToast(`${action} webhook...`, 'info');
        
        const response = await fetchAPI('/api/webhook-workflows/toggle', {
            method: 'POST',
            body: JSON.stringify({ slug })
        });
        
        const newState = response.enabled ? 'enabled' : 'disabled';
        showToast(`Webhook ${newState}`, 'success');
        
        // Reload page to reflect changes
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast(`Failed to toggle: ${error.message}`, 'error');
    }
}

/**
 * Delete a webhook
 * @param {string} slug - Webhook slug
 * @param {string} name - Webhook name
 */
async function deleteWebhook(slug, name) {
    const confirmed = await confirmAction(
        `Delete webhook "${name}"? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    try {
        showToast('Deleting webhook...', 'info');
        
        await fetchAPI('/api/webhook-workflows/unregister', {
            method: 'POST',
            body: JSON.stringify({ slug })
        });
        
        showToast('Webhook deleted', 'success');
        
        // Reload page to reflect changes
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        showToast(`Failed to delete: ${error.message}`, 'error');
    }
}

/**
 * Edit a webhook
 * @param {string} slug - Webhook slug
 */
async function editWebhook(slug) {
    try {
        // Load webhook data
        const data = await fetchAPI('/api/webhook-workflows');
        const webhook = data.webhook_workflows.find(w => w.slug === slug);
        
        if (!webhook) {
            showToast('Webhook not found', 'error');
            return;
        }
        
        // Show edit modal
        showEditWebhookModal(webhook);
        
    } catch (error) {
        showToast(`Failed to load webhook: ${error.message}`, 'error');
    }
}


// ==============================================================================
// Modal Management
// ==============================================================================

/**
 * Show add webhook modal
 */
function showAddWebhookModal() {
    const modal = createWebhookModal({
        title: 'Add Webhook',
        submitText: 'Create Webhook',
        onSubmit: createWebhook
    });
    
    document.body.appendChild(modal);
}

/**
 * Show edit webhook modal
 * @param {Object} webhook - Webhook data
 */
function showEditWebhookModal(webhook) {
    const modal = createWebhookModal({
        title: 'Edit Webhook',
        submitText: 'Update Webhook',
        webhook,
        onSubmit: (data) => updateWebhook(webhook.slug, data)
    });
    
    document.body.appendChild(modal);
}

/**
 * Create webhook modal element
 * @param {Object} options - Modal options
 * @returns {HTMLElement} - Modal element
 */
function createWebhookModal(options) {
    const { title, submitText, webhook = {}, onSubmit } = options;
    
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">${title}</span>
                <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            <form id="webhook-form" class="modal-body">
                <div class="form-group">
                    <label class="form-label">Webhook Name *</label>
                    <input type="text" name="name" class="form-input" required 
                           placeholder="Stripe Webhook" value="${webhook.name || ''}">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Slug *</label>
                    <input type="text" name="slug" class="form-input" required 
                           placeholder="stripe" value="${webhook.slug || ''}"
                           pattern="[a-z0-9-]+" title="Lowercase letters, numbers, and hyphens only"
                           ${webhook.slug ? 'readonly' : ''}>
                    <small class="form-hint">Lowercase letters, numbers, and hyphens only</small>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Description</label>
                    <textarea name="description" class="form-input" rows="3"
                              placeholder="Handles Stripe payment webhooks...">${webhook.description || ''}</textarea>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Source</label>
                    <input type="text" name="source" class="form-input" 
                           placeholder="Stripe" value="${webhook.source || ''}">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Forward URL (optional)</label>
                    <input type="url" name="forward_url" class="form-input" 
                           placeholder="https://my-processor.up.railway.app/process" 
                           value="${webhook.forward_url || ''}">
                    <small class="form-hint">Incoming webhooks will be forwarded to this URL</small>
                </div>
                
                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" name="slack_notify" ${webhook.slack_notify ? 'checked' : ''}>
                        <span>Send Slack notifications</span>
                    </label>
                </div>
                
                <div class="form-group">
                    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" name="enabled" ${webhook.enabled !== false ? 'checked' : ''}>
                        <span>Enabled</span>
                    </label>
                </div>
            </form>
            <div class="modal-footer">
                <button type="button" class="btn-secondary btn" onclick="this.closest('.modal-overlay').remove()">
                    Cancel
                </button>
                <button type="submit" form="webhook-form" class="btn">
                    ${submitText}
                </button>
            </div>
        </div>
    `;
    
    // Handle form submission
    const form = overlay.querySelector('#webhook-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = getFormData(form);
        const submitBtn = overlay.querySelector('button[type="submit"]');
        
        setButtonLoading(submitBtn, true, 'Saving...');
        
        try {
            await onSubmit(formData);
            overlay.remove();
        } catch (error) {
            showToast(error.message, 'error');
            setButtonLoading(submitBtn, false);
        }
    });
    
    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
    
    return overlay;
}


// ==============================================================================
// API Operations
// ==============================================================================

/**
 * Create a new webhook
 * @param {Object} data - Webhook data
 */
async function createWebhook(data) {
    try {
        showToast('Creating webhook...', 'info');
        
        const response = await fetchAPI('/api/webhook-workflows/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('Webhook created successfully', 'success');
        
        // Reload page to show new webhook
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        throw new Error(`Failed to create webhook: ${error.message}`);
    }
}

/**
 * Update an existing webhook
 * @param {string} slug - Webhook slug
 * @param {Object} data - Updated webhook data
 */
async function updateWebhook(slug, data) {
    try {
        showToast('Updating webhook...', 'info');
        
        // Add slug to data
        data.slug = slug;
        
        const response = await fetchAPI('/api/webhook-workflows/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
        
        showToast('Webhook updated successfully', 'success');
        
        // Reload page to show updated webhook
        setTimeout(() => location.reload(), 1000);
        
    } catch (error) {
        throw new Error(`Failed to update webhook: ${error.message}`);
    }
}


// ==============================================================================
// Export for global use
// ==============================================================================

window.loadWebhookStats = loadWebhookStats;
window.copyWebhookUrl = copyWebhookUrl;
window.testWebhook = testWebhook;
window.toggleWebhook = toggleWebhook;
window.deleteWebhook = deleteWebhook;
window.editWebhook = editWebhook;
window.showAddWebhookModal = showAddWebhookModal;
