/**
 * AIAA Dashboard - Client Management JavaScript
 * Handles client CRUD operations, table rendering, and search
 */

// ==============================================================================
// Client List
// ==============================================================================

/**
 * Load all clients from the API and render the table
 */
async function loadClients() {
    const tableBody = document.getElementById('clients-table-body');
    const loadingEl = document.getElementById('clients-loading');
    const emptyEl = document.getElementById('clients-empty');

    if (loadingEl) loadingEl.classList.remove('hidden');
    if (emptyEl) emptyEl.classList.add('hidden');

    try {
        const data = await fetchAPI('/api/v2/clients');
        const clients = data.clients || [];

        if (loadingEl) loadingEl.classList.add('hidden');

        if (clients.length === 0) {
            if (tableBody) tableBody.innerHTML = '';
            if (emptyEl) emptyEl.classList.remove('hidden');
            return;
        }

        if (tableBody) {
            tableBody.innerHTML = clients.map(client => `
                <tr data-client-name="${escapeHtml(client.name)}" class="client-row">
                    <td>
                        <div class="client-name-cell">
                            <strong>${escapeHtml(client.name)}</strong>
                            ${client.website ? `<br><small class="text-muted">${escapeHtml(client.website)}</small>` : ''}
                        </div>
                    </td>
                    <td>${escapeHtml(client.industry || '-')}</td>
                    <td>${client.updated_at ? formatDate(client.updated_at) : '-'}</td>
                    <td class="client-actions">
                        <button class="btn btn-small btn-secondary" onclick="showClientForm('edit', '${escapeHtml(client.slug || client.name)}')">Edit</button>
                        <button class="btn btn-small btn-secondary" onclick="showClientForm('edit', '${escapeHtml(client.slug || client.name)}')">View</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        if (loadingEl) loadingEl.classList.add('hidden');
        showToast('Failed to load clients.', 'error');
    }
}

// ==============================================================================
// Client Form
// ==============================================================================

/**
 * Show the client add/edit form
 * @param {string} mode - 'add' or 'edit'
 * @param {string} [name] - Client name (required for edit mode)
 */
async function showClientForm(mode, name) {
    const formOverlay = document.getElementById('client-form-overlay');
    const formTitle = document.getElementById('client-form-title');
    const form = document.getElementById('client-form');
    const submitBtn = document.getElementById('client-form-submit');

    if (!formOverlay || !form) return;

    // Reset form
    form.reset();
    document.getElementById('client-form-mode').value = mode;
    document.getElementById('client-form-original-name').value = '';

    if (mode === 'edit' && name) {
        if (formTitle) formTitle.textContent = 'Edit Client';
        if (submitBtn) submitBtn.textContent = 'Update Client';
        document.getElementById('client-form-original-name').value = name;

        // Load existing client data
        try {
            const data = await fetchAPI(`/api/v2/clients/${encodeURIComponent(name)}`);
            const client = data.client || data;

            setFormData(form, {
                name: client.name || '',
                website: client.website || '',
                industry: client.industry || '',
                description: client.description || '',
                target_audience: client.target_audience || '',
                goals: client.goals || '',
                competitors: client.competitors || '',
                brand_voice: client.brand_voice || '',
                words_to_avoid: client.words_to_avoid || (client.rules && client.rules.words_to_avoid) || '',
                content_length: client.content_length || (client.preferences && client.preferences.content_length) || ''
            });
        } catch (error) {
            showToast('Failed to load client data.', 'error');
            return;
        }
    } else {
        if (formTitle) formTitle.textContent = 'Add New Client';
        if (submitBtn) submitBtn.textContent = 'Create Client';
    }

    formOverlay.classList.remove('hidden');
}

/**
 * Hide the client form overlay
 */
function hideClientForm() {
    const formOverlay = document.getElementById('client-form-overlay');
    if (formOverlay) {
        formOverlay.classList.add('hidden');
    }
}

/**
 * Collect form data and save the client (create or update)
 */
async function saveClient() {
    const form = document.getElementById('client-form');
    const submitBtn = document.getElementById('client-form-submit');
    if (!form) return;

    // Validate required fields
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const mode = document.getElementById('client-form-mode').value;
    const originalName = document.getElementById('client-form-original-name').value;
    const formData = getFormData(form);

    // Remove internal fields
    delete formData.mode;
    delete formData.original_name;

    if (submitBtn) {
        setButtonLoading(submitBtn, true, 'Saving...');
    }

    try {
        if (mode === 'edit' && originalName) {
            await fetchAPI(`/api/v2/clients/${encodeURIComponent(originalName)}`, {
                method: 'PUT',
                body: JSON.stringify(formData)
            });
            showToast('Client updated successfully.', 'success');
        } else {
            await fetchAPI('/api/v2/clients', {
                method: 'POST',
                body: JSON.stringify(formData)
            });
            showToast('Client created successfully.', 'success');
        }

        hideClientForm();
        loadClients();
    } catch (error) {
        showToast(`Failed to save client: ${error.message}`, 'error');
    } finally {
        if (submitBtn) {
            setButtonLoading(submitBtn, false);
        }
    }
}

// ==============================================================================
// Client View
// ==============================================================================

/**
 * Navigate to view a client's details
 * @param {string} name - Client name
 */
function viewClient(name) {
    window.location.href = `/clients/${encodeURIComponent(name)}`;
}

// ==============================================================================
// Client Search
// ==============================================================================

/**
 * Filter client table rows by search query
 * @param {string} query - Search text to filter by
 */
function searchClients(query) {
    const rows = document.querySelectorAll('.client-row');
    const lowerQuery = (query || '').toLowerCase().trim();

    rows.forEach(row => {
        if (!lowerQuery) {
            row.classList.remove('hidden');
            return;
        }

        const name = (row.dataset.clientName || '').toLowerCase();
        const cells = row.querySelectorAll('td');
        let matchFound = name.includes(lowerQuery);

        if (!matchFound) {
            cells.forEach(cell => {
                if (cell.textContent.toLowerCase().includes(lowerQuery)) {
                    matchFound = true;
                }
            });
        }

        row.classList.toggle('hidden', !matchFound);
    });
}

// ==============================================================================
// Init on page load
// ==============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the clients page
    const clientsContainer = document.getElementById('clients-container');
    if (!clientsContainer) return;

    // Load clients
    loadClients();

    // Bind search input
    const searchInput = document.getElementById('client-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function(event) {
            searchClients(event.target.value);
        }, 200));
    }

    // Bind form submit
    const form = document.getElementById('client-form');
    if (form) {
        form.addEventListener('submit', function(event) {
            event.preventDefault();
            saveClient();
        });
    }

    // Close form on overlay click
    const formOverlay = document.getElementById('client-form-overlay');
    if (formOverlay) {
        formOverlay.addEventListener('click', function(event) {
            if (event.target === formOverlay) {
                hideClientForm();
            }
        });
    }
});

// ==============================================================================
// Export for global use
// ==============================================================================

window.loadClients = loadClients;
window.showClientForm = showClientForm;
window.hideClientForm = hideClientForm;
window.saveClient = saveClient;
window.viewClient = viewClient;
window.searchClients = searchClients;
