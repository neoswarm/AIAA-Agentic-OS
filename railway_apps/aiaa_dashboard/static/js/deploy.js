/**
 * Deploy Wizard - Handles 3-step deployment wizard
 */

class DeployWizard {
    constructor() {
        this.currentStep = 1;
        this.config = {
            workflowName: '',
            deployType: 'cron',
            cronExpression: '0 */3 * * *',
            webhookSlug: '',
            forwardUrl: '',
            slackNotify: false,
            webPort: 8080,
            healthPath: '/health'
        };
        this.cronBuilder = null;
        this.missingEnvVars = [];
    }

    open(workflowName, workflowCategory) {
        this.config.workflowName = workflowName;
        this.config.workflowCategory = workflowCategory;
        this.currentStep = 1;
        
        // Pre-select deploy type based on category if possible
        if (workflowCategory && workflowCategory.toLowerCase().includes('webhook')) {
            this.config.deployType = 'webhook';
        }
        
        // Reset UI
        document.getElementById('deploy-wizard-overlay').classList.remove('hidden');
        document.getElementById('workflow-name-input').value = workflowName;
        
        // Generate default webhook slug
        if (this.config.deployType === 'webhook') {
            this.config.webhookSlug = workflowName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
            document.getElementById('webhook-slug-input').value = this.config.webhookSlug;
        }
        
        this.updateStepIndicators();
        this.showStep(1);
        this.checkEnvVars();
    }

    close() {
        document.getElementById('deploy-wizard-overlay').classList.add('hidden');
        this.currentStep = 1;
        this.config = {
            workflowName: '',
            deployType: 'cron',
            cronExpression: '0 */3 * * *',
            webhookSlug: '',
            forwardUrl: '',
            slackNotify: false,
            webPort: 8080,
            healthPath: '/health'
        };
    }

    nextStep() {
        if (this.currentStep === 1) {
            // Get selected deploy type
            const selectedType = document.querySelector('input[name="deploy_type"]:checked').value;
            this.config.deployType = selectedType;
        } else if (this.currentStep === 2) {
            // Collect configuration
            this.config.workflowName = document.getElementById('workflow-name-input').value;
            
            if (this.config.deployType === 'cron') {
                this.config.cronExpression = this.cronBuilder ? this.cronBuilder.getCronExpression() : '0 */3 * * *';
            } else if (this.config.deployType === 'webhook') {
                this.config.webhookSlug = document.getElementById('webhook-slug-input').value;
                this.config.forwardUrl = document.getElementById('forward-url-input').value;
                this.config.slackNotify = document.getElementById('slack-notify-checkbox').checked;
            } else if (this.config.deployType === 'web') {
                this.config.webPort = document.getElementById('web-port-input').value;
                this.config.healthPath = document.getElementById('health-path-input').value;
            }
            
            // Show summary
            this.showDeploySummary();
        }
        
        this.currentStep++;
        this.showStep(this.currentStep);
        this.updateStepIndicators();
        this.updateButtons();
    }

    prevStep() {
        this.currentStep--;
        this.showStep(this.currentStep);
        this.updateStepIndicators();
        this.updateButtons();
    }

    showStep(step) {
        // Hide all steps
        document.querySelectorAll('.wizard-step-content').forEach(el => {
            el.classList.add('hidden');
        });
        
        // Show current step
        const stepContent = document.querySelector(`.wizard-step-content[data-step="${step}"]`);
        if (stepContent) {
            stepContent.classList.remove('hidden');
        }
        
        // Initialize cron builder for step 2 if needed
        if (step === 2 && this.config.deployType === 'cron') {
            setTimeout(() => {
                if (!this.cronBuilder) {
                    this.cronBuilder = new CronBuilder('cron-builder-container');
                }
            }, 100);
            this.showConfigSection('cron-config');
        } else if (step === 2 && this.config.deployType === 'webhook') {
            this.showConfigSection('webhook-config');
            this.updateWebhookSlugPreview();
        } else if (step === 2 && this.config.deployType === 'web') {
            this.showConfigSection('web-config');
        }
    }

    showConfigSection(sectionId) {
        document.querySelectorAll('.config-section').forEach(el => {
            el.classList.add('hidden');
        });
        const section = document.getElementById(sectionId);
        if (section) {
            section.classList.remove('hidden');
        }
    }

    updateStepIndicators() {
        document.querySelectorAll('.wizard-step').forEach((step, index) => {
            const indicator = step.querySelector('.step-indicator');
            if (index + 1 < this.currentStep) {
                indicator.classList.add('completed');
                indicator.classList.remove('active');
            } else if (index + 1 === this.currentStep) {
                indicator.classList.add('active');
                indicator.classList.remove('completed');
            } else {
                indicator.classList.remove('active', 'completed');
            }
        });
    }

    updateButtons() {
        const prevBtn = document.getElementById('wizard-prev-btn');
        const nextBtn = document.getElementById('wizard-next-btn');
        const deployBtn = document.getElementById('wizard-deploy-btn');
        
        prevBtn.style.display = this.currentStep === 1 ? 'none' : 'inline-flex';
        nextBtn.style.display = this.currentStep === 3 ? 'none' : 'inline-flex';
        deployBtn.classList.toggle('hidden', this.currentStep !== 3);
    }

    updateWebhookSlugPreview() {
        const slugInput = document.getElementById('webhook-slug-input');
        if (slugInput) {
            slugInput.addEventListener('input', (e) => {
                const preview = document.getElementById('slug-preview');
                if (preview) {
                    preview.textContent = e.target.value || 'my-webhook';
                }
            });
        }
    }

    async checkEnvVars() {
        try {
            const response = await fetch('/api/env/check');
            const data = await response.json();
            
            const requiredVars = [
                'OPENROUTER_API_KEY',
                'PERPLEXITY_API_KEY',
                'SLACK_WEBHOOK_URL',
                'RAILWAY_API_TOKEN'
            ];
            
            this.missingEnvVars = requiredVars.filter(v => !data[v]);
            
            // Populate checklist
            const checklist = document.getElementById('env-vars-checklist');
            if (checklist) {
                checklist.innerHTML = requiredVars.map(varName => {
                    const isSet = data[varName];
                    return `
                        <div class="env-check-item ${isSet ? 'set' : 'missing'}">
                            <div class="env-check-icon">
                                ${isSet ? '✓' : '✗'}
                            </div>
                            <span class="mono">${varName}</span>
                        </div>
                    `;
                }).join('');
            }
        } catch (error) {
            console.error('Error checking env vars:', error);
        }
    }

    showDeploySummary() {
        const summary = document.getElementById('deploy-summary');
        const warnings = document.getElementById('env-warnings');
        const missingList = document.getElementById('missing-env-list');
        
        let summaryHTML = `
            <div class="summary-item">
                <span class="summary-label">Workflow Name:</span>
                <span class="summary-value">${this.config.workflowName}</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">Deploy Type:</span>
                <span class="summary-value">${this.config.deployType.toUpperCase()}</span>
            </div>
        `;
        
        if (this.config.deployType === 'cron') {
            summaryHTML += `
                <div class="summary-item">
                    <span class="summary-label">Schedule:</span>
                    <span class="summary-value">${this.config.cronExpression}</span>
                </div>
            `;
        } else if (this.config.deployType === 'webhook') {
            summaryHTML += `
                <div class="summary-item">
                    <span class="summary-label">Webhook URL:</span>
                    <span class="summary-value">/webhook/${this.config.webhookSlug}</span>
                </div>
            `;
            if (this.config.forwardUrl) {
                summaryHTML += `
                    <div class="summary-item">
                        <span class="summary-label">Forward URL:</span>
                        <span class="summary-value">${this.config.forwardUrl}</span>
                    </div>
                `;
            }
            summaryHTML += `
                <div class="summary-item">
                    <span class="summary-label">Slack Notify:</span>
                    <span class="summary-value">${this.config.slackNotify ? 'Yes' : 'No'}</span>
                </div>
            `;
        } else if (this.config.deployType === 'web') {
            summaryHTML += `
                <div class="summary-item">
                    <span class="summary-label">Port:</span>
                    <span class="summary-value">${this.config.webPort}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Health Check:</span>
                    <span class="summary-value">${this.config.healthPath}</span>
                </div>
            `;
        }
        
        summary.innerHTML = summaryHTML;
        
        // Show warnings if any
        if (this.missingEnvVars.length > 0) {
            warnings.classList.remove('hidden');
            missingList.innerHTML = this.missingEnvVars.map(v => `<li>${v}</li>`).join('');
        } else {
            warnings.classList.add('hidden');
        }
    }

    async deploy() {
        this.showProgress();
        
        try {
            const response = await fetch('/api/workflows/deploy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(this.config)
            });
            
            const result = await response.json();
            
            if (result.status === 'success' || response.ok) {
                await this.simulateProgress();
                this.showSuccess(result);
            } else {
                this.showError(result.message || 'Deployment failed');
            }
        } catch (error) {
            console.error('Deploy error:', error);
            this.showError(error.message);
        }
    }

    showProgress() {
        // Hide summary and show progress
        document.getElementById('deploy-summary').classList.add('hidden');
        document.getElementById('env-warnings').classList.add('hidden');
        document.getElementById('deploy-progress-container').classList.remove('hidden');
        document.getElementById('wizard-deploy-btn').disabled = true;
    }

    async simulateProgress() {
        const steps = document.querySelectorAll('.progress-step');
        
        for (let i = 0; i < steps.length; i++) {
            steps[i].setAttribute('data-status', 'active');
            await this.sleep(1000);
            steps[i].setAttribute('data-status', 'completed');
        }
    }

    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    updateProgress(step, message) {
        const progressSteps = document.querySelectorAll('.progress-step');
        if (progressSteps[step - 1]) {
            progressSteps[step - 1].setAttribute('data-status', 'active');
            const messageEl = progressSteps[step - 1].querySelector('.progress-step-message');
            if (messageEl) {
                messageEl.textContent = message;
            }
        }
    }

    showSuccess(result) {
        document.getElementById('deploy-progress-container').classList.add('hidden');
        const successEl = document.getElementById('deploy-success');
        successEl.classList.remove('hidden');
        
        if (result.url) {
            const urlEl = successEl.querySelector('.success-url');
            urlEl.textContent = result.url;
        }
    }

    showError(message) {
        alert(`Deployment failed: ${message}`);
        document.getElementById('wizard-deploy-btn').disabled = false;
    }
}

// Global wizard instance
let deployWizard = new DeployWizard();

// Global functions for inline event handlers
function openDeployWizard(workflowName, workflowCategory) {
    deployWizard.open(workflowName, workflowCategory);
}

function closeDeployWizard() {
    deployWizard.close();
}

function nextWizardStep() {
    deployWizard.nextStep();
}

function prevWizardStep() {
    deployWizard.prevStep();
}

function deployWorkflow() {
    deployWizard.deploy();
}

function viewWorkflow(workflowName) {
    window.location.href = `/workflows/${encodeURIComponent(workflowName)}`;
}
