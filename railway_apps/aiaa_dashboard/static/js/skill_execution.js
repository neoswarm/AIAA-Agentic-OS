/**
 * AIAA Dashboard - Skill Execution JavaScript
 * Handles skill search, form generation, execution, and progress polling
 */

// ==============================================================================
// Skill Search
// ==============================================================================

/**
 * Search skills by query string
 * Fetches matching skills from the API and renders result cards
 * @param {string} query - Search query (skill name, description, or intent)
 */
async function searchSkills(query) {
    const resultsContainer = document.getElementById('skill-search-results');
    if (!resultsContainer) return;

    query = (query || '').trim().replace(/\s+/g, ' ');
    if (query.length < 2) {
        resultsContainer.innerHTML = '';
        return;
    }

    resultsContainer.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><span>Searching skills...</span></div>';

    try {
        const data = await fetchAPI(`/api/v2/skills/search?q=${encodeURIComponent(query)}`);
        const skills = data.skills || [];

        if (skills.length === 0) {
            resultsContainer.innerHTML = `
                <div class="empty-state">
                    <p>No skills found for "${escapeHtml(query)}"</p>
                    <p class="text-muted">Try different keywords or browse categories below.</p>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = skills.map(skill => renderSkillCard(skill)).join('');
    } catch (error) {
        resultsContainer.innerHTML = '';
        showToast('Failed to search skills. Please try again.', 'error');
    }
}

/**
 * Render a single skill card as HTML
 * @param {Object} skill - Skill object with name, description, category
 * @returns {string} - HTML string for the skill card
 */
function renderSkillCard(skill) {
    const categoryClass = skill.category ? `category-${skill.category.toLowerCase().replace(/[^a-z0-9]/g, '-')}` : '';
    return `
        <div class="skill-card ${categoryClass}" onclick="navigateToSkill('${escapeHtml(skill.name)}')">
            <div class="skill-card-header">
                <h3 class="skill-card-title">${escapeHtml(skill.display_name || skill.name)}</h3>
                ${skill.category ? `<span class="skill-card-category">${escapeHtml(skill.category)}</span>` : ''}
            </div>
            <p class="skill-card-description">${escapeHtml(skill.description || 'No description available')}</p>
            ${skill.inputs && skill.inputs.length > 0 ? `<div class="skill-card-meta">${skill.inputs.length} input${skill.inputs.length !== 1 ? 's' : ''}</div>` : ''}
        </div>
    `;
}

/**
 * Navigate to the skill execution page
 * @param {string} skillName - Name of the skill
 */
function navigateToSkill(skillName) {
    window.location.href = `/skills/${encodeURIComponent(skillName)}/run`;
}

// ==============================================================================
// Dynamic Form Generation
// ==============================================================================

/**
 * Load skill metadata and dynamically build the execution form
 * @param {string} skillName - Name of the skill to load
 */
async function loadSkillForm(skillName) {
    const formContainer = document.getElementById('skill-form-container');
    if (!formContainer) return;

    formContainer.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><span>Loading skill...</span></div>';

    try {
        const data = await fetchAPI(`/api/v2/skills/${encodeURIComponent(skillName)}`);
        const skill = data.skill || data;

        // Build the form HTML
        const inputs = skill.inputs || [];
        const requiredInputs = inputs.filter(i => i.required);
        const optionalInputs = inputs.filter(i => !i.required);

        let formHTML = `<form id="skill-execute-form" onsubmit="event.preventDefault(); executeSkill('${escapeHtml(skillName)}')">`;

        // Required fields
        if (requiredInputs.length > 0) {
            formHTML += '<div class="form-section"><h4 class="form-section-title">Required</h4>';
            requiredInputs.forEach(input => {
                formHTML += buildFormField(input);
            });
            formHTML += '</div>';
        }

        // Optional fields behind toggle
        if (optionalInputs.length > 0) {
            formHTML += `
                <div class="form-section">
                    <button type="button" class="advanced-toggle" onclick="toggleAdvancedOptions(this)">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="toggle-chevron">
                            <polyline points="6 9 12 15 18 9"/>
                        </svg>
                        Advanced Options (${optionalInputs.length})
                    </button>
                    <div class="advanced-options hidden">
            `;
            optionalInputs.forEach(input => {
                formHTML += buildFormField(input);
            });
            formHTML += '</div></div>';
        }

        // Submit buttons
        formHTML += `
            <div class="form-actions">
                <button type="submit" class="btn btn-primary" id="execute-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="5 3 19 12 5 21 5 3"/>
                    </svg>
                    Run Skill
                </button>
                <button type="button" class="btn btn-secondary" onclick="estimateCost('${escapeHtml(skillName)}')">
                    Estimate Cost
                </button>
            </div>
        </form>`;

        formContainer.innerHTML = formHTML;
    } catch (error) {
        formContainer.innerHTML = `
            <div class="error-state">
                <p>Failed to load skill form.</p>
                <button class="btn btn-secondary" onclick="loadSkillForm('${escapeHtml(skillName)}')">Retry</button>
            </div>
        `;
        showToast('Could not load skill details. Please try again.', 'error');
    }
}

/**
 * Build a single form field HTML from an input specification
 * @param {Object} input - Input spec with name, type, required, description, default, options
 * @returns {string} - HTML string for the form field
 */
function buildFormField(input) {
    const fieldId = `field-${input.name}`;
    const requiredAttr = input.required ? 'required' : '';
    const requiredMark = input.required ? '<span class="required-mark">*</span>' : '';
    const defaultValue = input.default || '';
    const placeholder = input.placeholder || input.description || '';

    let fieldHTML = `
        <div class="form-group">
            <label class="form-label" for="${fieldId}">
                ${escapeHtml(input.display_name || formatFieldName(input.name))}${requiredMark}
                ${input.description ? `<span class="form-tooltip" title="${escapeHtml(input.description)}">?</span>` : ''}
            </label>
    `;

    switch (input.type) {
        case 'select':
        case 'enum':
            fieldHTML += `<select id="${fieldId}" name="${input.name}" class="form-input" ${requiredAttr}>`;
            fieldHTML += `<option value="">Select...</option>`;
            (input.options || []).forEach(opt => {
                const optVal = typeof opt === 'object' ? opt.value : opt;
                const optLabel = typeof opt === 'object' ? opt.label : opt;
                const selected = optVal === defaultValue ? 'selected' : '';
                fieldHTML += `<option value="${escapeHtml(optVal)}" ${selected}>${escapeHtml(optLabel)}</option>`;
            });
            fieldHTML += '</select>';
            break;

        case 'textarea':
        case 'text_long':
            fieldHTML += `<textarea id="${fieldId}" name="${input.name}" class="form-input" rows="4"
                placeholder="${escapeHtml(placeholder)}" ${requiredAttr}>${escapeHtml(defaultValue)}</textarea>`;
            break;

        case 'number':
        case 'integer':
            fieldHTML += `<input type="number" id="${fieldId}" name="${input.name}" class="form-input"
                value="${escapeHtml(String(defaultValue))}" placeholder="${escapeHtml(placeholder)}"
                ${input.min !== undefined ? `min="${input.min}"` : ''}
                ${input.max !== undefined ? `max="${input.max}"` : ''}
                ${requiredAttr}>`;
            break;

        case 'boolean':
        case 'checkbox':
            fieldHTML += `
                <label class="form-checkbox-label">
                    <input type="checkbox" id="${fieldId}" name="${input.name}" ${defaultValue ? 'checked' : ''}>
                    <span>${escapeHtml(input.description || '')}</span>
                </label>`;
            break;

        case 'file':
            fieldHTML += `<input type="file" id="${fieldId}" name="${input.name}" class="form-input"
                ${input.accept ? `accept="${escapeHtml(input.accept)}"` : ''} ${requiredAttr}>`;
            break;

        default: // text, string, url, email
            fieldHTML += `<input type="${input.type === 'url' ? 'url' : input.type === 'email' ? 'email' : 'text'}"
                id="${fieldId}" name="${input.name}" class="form-input"
                value="${escapeHtml(String(defaultValue))}" placeholder="${escapeHtml(placeholder)}" ${requiredAttr}>`;
            break;
    }

    fieldHTML += '</div>';
    return fieldHTML;
}

/**
 * Format a field name for display (e.g., "blog_topic" -> "Blog Topic")
 * @param {string} name - Raw field name
 * @returns {string} - Formatted display name
 */
function formatFieldName(name) {
    return name
        .replace(/^--/, '')
        .replace(/[-_]/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Toggle visibility of advanced options section
 * @param {HTMLElement} button - The toggle button element
 */
function toggleAdvancedOptions(button) {
    const optionsDiv = button.nextElementSibling;
    const chevron = button.querySelector('.toggle-chevron');

    if (optionsDiv) {
        optionsDiv.classList.toggle('hidden');
        if (chevron) {
            chevron.style.transform = optionsDiv.classList.contains('hidden') ? '' : 'rotate(180deg)';
        }
    }
}

// ==============================================================================
// Skill Execution
// ==============================================================================

/**
 * Collect form values and execute a skill
 * @param {string} skillName - Name of the skill to execute
 */
async function executeSkill(skillName) {
    const form = document.getElementById('skill-execute-form');
    const executeBtn = document.getElementById('execute-btn');
    if (!form) return;

    // Collect form values
    const params = {};
    const formData = new FormData(form);

    for (const [key, value] of formData.entries()) {
        const element = form.elements[key];
        if (element && element.type === 'checkbox') {
            params[key] = element.checked;
        } else if (element && element.type === 'file') {
            // Skip file inputs for JSON body; handle separately if needed
            if (element.files.length > 0) {
                params[key] = element.files[0].name;
            }
        } else if (value !== '') {
            params[key] = value;
        }
    }

    // Validate required fields
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    setButtonLoading(executeBtn, true, 'Starting...');

    try {
        const data = await fetchAPI(`/api/v2/skills/${encodeURIComponent(skillName)}/execute`, {
            method: 'POST',
            body: JSON.stringify({ params })
        });

        const executionId = data.execution_id;
        if (executionId) {
            window.location.href = `/executions/${encodeURIComponent(executionId)}/progress`;
        } else {
            showToast('Skill started but no execution ID returned.', 'warning');
            setButtonLoading(executeBtn, false);
        }
    } catch (error) {
        setButtonLoading(executeBtn, false);

        // If the error has structured data (from enhanced fetchAPI), use it
        if (error.data && error.data.errors) {
            // Show field-level errors
            const form = document.getElementById('skill-execute-form');
            if (form) {
                for (const [field, msg] of Object.entries(error.data.errors)) {
                    const input = form.querySelector(`[name="${field}"]`);
                    if (input) {
                        const group = input.closest('.form-group');
                        if (group) {
                            group.classList.add('has-error');
                            let errEl = group.querySelector('.field-error');
                            if (!errEl) {
                                errEl = document.createElement('span');
                                errEl.className = 'field-error';
                                group.appendChild(errEl);
                            }
                            errEl.textContent = msg;
                            errEl.style.display = 'block';
                        }
                    }
                }
            }
            showToast(error.data.message || 'Please fix the highlighted fields.', 'error', 5000);
        } else if (error.status === 401 || (error.message && error.message.toLowerCase().includes('api key'))) {
            showToast('API key required. Go to Settings to configure.', 'error', 5000);
        } else {
            showToast(`Skill failed: ${error.message}`, 'error', 5000);
        }
    }
}

/**
 * Estimate the cost of running a skill
 * @param {string} skillName - Name of the skill
 */
async function estimateCost(skillName) {
    try {
        const data = await fetchAPI(`/api/v2/skills/${encodeURIComponent(skillName)}/estimate`);
        const estimate = data.estimate;

        if (estimate) {
            showToast(`Estimated cost: $${estimate.cost || '0.00'} | Time: ~${estimate.time || 'unknown'}`, 'info', 5000);
        } else {
            showToast('Cost estimate not available for this skill.', 'info');
        }
    } catch (error) {
        showToast('Could not get cost estimate.', 'warning');
    }
}

// ==============================================================================
// Execution Progress Polling
// ==============================================================================

/** @type {number|null} Active polling interval ID */
let _pollingInterval = null;

/**
 * Start polling execution status every 2 seconds
 * Updates step indicators, appends output to log area, stops on completion
 * @param {string} executionId - The execution ID to poll
 */
function pollExecutionStatus(executionId) {
    // Clear any existing polling
    if (_pollingInterval) {
        clearInterval(_pollingInterval);
    }

    const stepsContainer = document.getElementById('execution-steps');
    const outputLog = document.getElementById('execution-output');
    const statusLabel = document.getElementById('execution-status');
    const cancelBtn = document.getElementById('cancel-execution-btn');

    let lastOutputLength = 0;

    function updateUI(data) {
        // Update status label
        if (statusLabel) {
            statusLabel.textContent = data.status || 'running';
            statusLabel.className = `execution-status status-${data.status || 'running'}`;
        }

        // Update step indicators
        if (stepsContainer && data.steps) {
            stepsContainer.innerHTML = data.steps.map((step, index) => {
                let icon = '';
                let stepClass = 'step-pending';

                if (step.status === 'completed') {
                    icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
                    stepClass = 'step-completed';
                } else if (step.status === 'running') {
                    icon = '<div class="spinner-small"></div>';
                    stepClass = 'step-running';
                } else if (step.status === 'error') {
                    icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
                    stepClass = 'step-error';
                } else {
                    icon = '<div class="step-circle"></div>';
                }

                return `
                    <div class="execution-step ${stepClass}">
                        <div class="step-icon">${icon}</div>
                        <div class="step-info">
                            <span class="step-name">${escapeHtml(step.name || `Step ${index + 1}`)}</span>
                            ${step.duration ? `<span class="step-duration">${step.duration}</span>` : ''}
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Append new output to log
        if (outputLog && data.output) {
            const newOutput = data.output.substring(lastOutputLength);
            if (newOutput) {
                outputLog.innerHTML += renderSimpleMarkdown(escapeHtml(newOutput));
                outputLog.scrollTop = outputLog.scrollHeight;
                lastOutputLength = data.output.length;
            }
        }

        // Update progress bar if present
        if (data.progress !== undefined) {
            const progressBar = document.getElementById('execution-progress-bar');
            if (progressBar) {
                progressBar.style.width = `${Math.min(100, Math.max(0, data.progress))}%`;
            }
        }

        // Check for completion
        if (data.status === 'success' || data.status === 'error' || data.status === 'cancelled') {
            clearInterval(_pollingInterval);
            _pollingInterval = null;

            if (cancelBtn) {
                cancelBtn.disabled = true;
            }

            if (data.status === 'success') {
                showToast('Skill completed successfully!', 'success');
                // Redirect to output page after a brief delay
                setTimeout(() => {
                    window.location.href = `/executions/${encodeURIComponent(executionId)}/output`;
                }, 1500);
            } else if (data.status === 'error') {
                showToast(data.error_message || 'Skill execution failed.', 'error', 5000);
            } else if (data.status === 'cancelled') {
                showToast('Execution was cancelled.', 'warning');
            }
        }
    }

    // Initial fetch
    fetchAPI(`/api/v2/executions/${encodeURIComponent(executionId)}/status`)
        .then(updateUI)
        .catch(() => showToast('Failed to load execution status.', 'error'));

    // Start polling every 2 seconds
    _pollingInterval = setInterval(() => {
        fetchAPI(`/api/v2/executions/${encodeURIComponent(executionId)}/status`)
            .then(updateUI)
            .catch(() => {
                // Don't stop polling on transient errors
            });
    }, 2000);
}

/**
 * Cancel a running execution
 * @param {string} executionId - The execution ID to cancel
 */
async function cancelExecution(executionId) {
    const confirmed = await confirmAction('Are you sure you want to cancel this execution?');
    if (!confirmed) return;

    const cancelBtn = document.getElementById('cancel-execution-btn');
    if (cancelBtn) {
        setButtonLoading(cancelBtn, true, 'Cancelling...');
    }

    try {
        await fetchAPI(`/api/v2/executions/${encodeURIComponent(executionId)}/cancel`, {
            method: 'POST'
        });
        showToast('Execution cancelled.', 'warning');
    } catch (error) {
        showToast(`Failed to cancel: ${error.message}`, 'error');
        if (cancelBtn) {
            setButtonLoading(cancelBtn, false);
        }
    }
}

// ==============================================================================
// Simple Markdown Renderer
// ==============================================================================

/**
 * Render simple markdown to HTML
 * Supports: **bold**, *italic*, # headers, - lists, ```code blocks
 * @param {string} text - Markdown text (should already be HTML-escaped)
 * @returns {string} - HTML string
 */
function renderSimpleMarkdown(text) {
    if (!text) return '';

    let html = text;

    // Code blocks (``` ... ```)
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');

    // Inline code (`...`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers (# ... )
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

    // Bold (**...**)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic (*...*)
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Unordered lists (- item)
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    // Clean up double <br> inside block elements
    html = html.replace(/<\/ul><br>/g, '</ul>');
    html = html.replace(/<\/pre><br>/g, '</pre>');
    html = html.replace(/<\/h[234]><br>/g, function(match) {
        return match.replace('<br>', '');
    });

    return html;
}

// ==============================================================================
// Output Actions
// ==============================================================================

/**
 * Copy skill output to clipboard
 * @param {string} executionId - Execution ID to fetch output from
 */
async function copyOutput(executionId) {
    try {
        const data = await fetchAPI(`/api/v2/executions/${encodeURIComponent(executionId)}/output`);
        await copyToClipboard(data.output || '');
    } catch (error) {
        showToast('Failed to copy output.', 'error');
    }
}

/**
 * Download skill output as a markdown file
 * @param {string} executionId - Execution ID
 * @param {string} filename - Suggested filename
 */
async function downloadOutput(executionId, filename) {
    try {
        const data = await fetchAPI(`/api/v2/executions/${encodeURIComponent(executionId)}/output`);
        const blob = new Blob([data.output || ''], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'output.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast('Download started.', 'success');
    } catch (error) {
        showToast('Failed to download output.', 'error');
    }
}

// ==============================================================================
// Utility
// ==============================================================================

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Raw text
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// ==============================================================================
// Debounced search handler (attach to search input)
// ==============================================================================

/** Debounced skill search for the search bar */
const debouncedSkillSearch = debounce(function(event) {
    searchSkills(event.target.value);
}, 300);

// ==============================================================================
// Init on page load
// ==============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Bind search input if present
    const searchInput = document.getElementById('skill-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', debouncedSkillSearch);
    }

    // Auto-load skill form if on execution page
    const skillNameEl = document.getElementById('skill-name-data');
    if (skillNameEl && skillNameEl.dataset.skillName) {
        loadSkillForm(skillNameEl.dataset.skillName);
    }

    // Auto-start polling if on progress page
    const executionIdEl = document.getElementById('execution-id-data');
    if (executionIdEl && executionIdEl.dataset.executionId) {
        pollExecutionStatus(executionIdEl.dataset.executionId);
    }
});

// ==============================================================================
// Export for global use
// ==============================================================================

window.searchSkills = searchSkills;
window.loadSkillForm = loadSkillForm;
window.executeSkill = executeSkill;
window.pollExecutionStatus = pollExecutionStatus;
window.cancelExecution = cancelExecution;
window.estimateCost = estimateCost;
window.copyOutput = copyOutput;
window.downloadOutput = downloadOutput;
window.navigateToSkill = navigateToSkill;
window.toggleAdvancedOptions = toggleAdvancedOptions;
window.renderSimpleMarkdown = renderSimpleMarkdown;
window.escapeHtml = escapeHtml;
