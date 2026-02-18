/**
 * Visual Cron Schedule Builder
 * Generates cron expressions with a user-friendly interface
 */

class CronBuilder {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.mode = 'minutes'; // minutes, hours, daily, weekly, monthly, custom
        this.interval = 5;
        this.minute = 0;
        this.hour = 0;
        this.day = 1;
        this.dayOfWeek = 1;
        
        this.render();
        this.updatePreview();
    }

    render() {
        this.container.innerHTML = `
            <div class="cron-builder">
                <div class="cron-mode-selector">
                    <label class="cron-label">Run this workflow...</label>
                    <select class="cron-select" id="cron-mode" onchange="window.cronBuilder.changeMode(this.value)">
                        <option value="minutes">Every X minutes</option>
                        <option value="hours">Every X hours</option>
                        <option value="daily">Daily at specific time</option>
                        <option value="weekly">Weekly on specific day</option>
                        <option value="monthly">Monthly on specific day</option>
                        <option value="custom">Custom cron expression</option>
                    </select>
                </div>
                
                <div id="cron-config-area" class="cron-config-area">
                    ${this.renderModeConfig()}
                </div>
                
                <div class="cron-preview">
                    <div class="preview-label">Preview:</div>
                    <div class="preview-description" id="cron-description"></div>
                    <div class="preview-next-runs">
                        <span class="preview-label-small">Next runs:</span>
                        <ul id="next-runs-list"></ul>
                    </div>
                    <div class="preview-expression">
                        <span class="preview-label-small">Cron expression:</span>
                        <code id="cron-expression"></code>
                    </div>
                </div>
            </div>
        `;
    }

    renderModeConfig() {
        switch (this.mode) {
            case 'minutes':
                return `
                    <div class="cron-input-group">
                        <label class="cron-label">Every</label>
                        <input type="number" class="cron-input" id="minute-interval" 
                               value="${this.interval}" min="1" max="59" 
                               onchange="window.cronBuilder.setInterval(this.value)">
                        <span class="cron-label">minutes</span>
                    </div>
                `;
            case 'hours':
                return `
                    <div class="cron-input-group">
                        <label class="cron-label">Every</label>
                        <input type="number" class="cron-input" id="hour-interval" 
                               value="${this.interval}" min="1" max="24" 
                               onchange="window.cronBuilder.setInterval(this.value)">
                        <span class="cron-label">hours at minute</span>
                        <input type="number" class="cron-input" id="minute-offset" 
                               value="${this.minute}" min="0" max="59" 
                               onchange="window.cronBuilder.setMinute(this.value)">
                    </div>
                `;
            case 'daily':
                return `
                    <div class="cron-input-group">
                        <label class="cron-label">Daily at</label>
                        <input type="time" class="cron-input" id="daily-time" 
                               value="${this.formatTime()}"
                               onchange="window.cronBuilder.setTime(this.value)">
                    </div>
                `;
            case 'weekly':
                return `
                    <div class="cron-input-group">
                        <label class="cron-label">Every</label>
                        <select class="cron-select" id="day-of-week" onchange="window.cronBuilder.setDayOfWeek(this.value)">
                            <option value="0" ${this.dayOfWeek === 0 ? 'selected' : ''}>Sunday</option>
                            <option value="1" ${this.dayOfWeek === 1 ? 'selected' : ''}>Monday</option>
                            <option value="2" ${this.dayOfWeek === 2 ? 'selected' : ''}>Tuesday</option>
                            <option value="3" ${this.dayOfWeek === 3 ? 'selected' : ''}>Wednesday</option>
                            <option value="4" ${this.dayOfWeek === 4 ? 'selected' : ''}>Thursday</option>
                            <option value="5" ${this.dayOfWeek === 5 ? 'selected' : ''}>Friday</option>
                            <option value="6" ${this.dayOfWeek === 6 ? 'selected' : ''}>Saturday</option>
                        </select>
                        <span class="cron-label">at</span>
                        <input type="time" class="cron-input" id="weekly-time" 
                               value="${this.formatTime()}"
                               onchange="window.cronBuilder.setTime(this.value)">
                    </div>
                `;
            case 'monthly':
                return `
                    <div class="cron-input-group">
                        <label class="cron-label">Day</label>
                        <input type="number" class="cron-input" id="day-of-month" 
                               value="${this.day}" min="1" max="31" 
                               onchange="window.cronBuilder.setDay(this.value)">
                        <span class="cron-label">at</span>
                        <input type="time" class="cron-input" id="monthly-time" 
                               value="${this.formatTime()}"
                               onchange="window.cronBuilder.setTime(this.value)">
                    </div>
                `;
            case 'custom':
                return `
                    <div class="cron-input-group">
                        <label class="cron-label">Cron expression:</label>
                        <input type="text" class="cron-input-full" id="custom-cron" 
                               placeholder="0 */3 * * *"
                               onchange="window.cronBuilder.setCustomCron(this.value)">
                        <small class="cron-hint">Format: minute hour day month day-of-week</small>
                    </div>
                `;
        }
    }

    changeMode(mode) {
        this.mode = mode;
        document.getElementById('cron-config-area').innerHTML = this.renderModeConfig();
        this.updatePreview();
    }

    setInterval(value) {
        this.interval = parseInt(value);
        this.updatePreview();
    }

    setMinute(value) {
        this.minute = parseInt(value);
        this.updatePreview();
    }

    setTime(timeString) {
        const [hours, minutes] = timeString.split(':');
        this.hour = parseInt(hours);
        this.minute = parseInt(minutes);
        this.updatePreview();
    }

    setDay(value) {
        this.day = parseInt(value);
        this.updatePreview();
    }

    setDayOfWeek(value) {
        this.dayOfWeek = parseInt(value);
        this.updatePreview();
    }

    setCustomCron(value) {
        this.customCron = value;
        this.updatePreview();
    }

    formatTime() {
        return `${String(this.hour).padStart(2, '0')}:${String(this.minute).padStart(2, '0')}`;
    }

    getCronExpression() {
        switch (this.mode) {
            case 'minutes':
                return `*/${this.interval} * * * *`;
            case 'hours':
                return `${this.minute} */${this.interval} * * *`;
            case 'daily':
                return `${this.minute} ${this.hour} * * *`;
            case 'weekly':
                return `${this.minute} ${this.hour} * * ${this.dayOfWeek}`;
            case 'monthly':
                return `${this.minute} ${this.hour} ${this.day} * *`;
            case 'custom':
                return this.customCron || '0 * * * *';
            default:
                return '0 * * * *';
        }
    }

    getDescription() {
        switch (this.mode) {
            case 'minutes':
                return `Runs every ${this.interval} minute${this.interval > 1 ? 's' : ''}`;
            case 'hours':
                return `Runs every ${this.interval} hour${this.interval > 1 ? 's' : ''} at minute ${this.minute}`;
            case 'daily':
                return `Runs daily at ${this.formatTime()}`;
            case 'weekly':
                const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                return `Runs every ${days[this.dayOfWeek]} at ${this.formatTime()}`;
            case 'monthly':
                return `Runs on day ${this.day} of every month at ${this.formatTime()}`;
            case 'custom':
                return `Custom schedule: ${this.getCronExpression()}`;
            default:
                return 'Invalid schedule';
        }
    }

    getNextRuns(count = 3) {
        const cron = this.getCronExpression();
        const now = new Date();
        const runs = [];

        try {
            for (let i = 0; i < count; i++) {
                const next = this.calculateNextRun(cron, i === 0 ? now : runs[i - 1]);
                if (next) {
                    runs.push(next);
                }
            }
        } catch (e) {
            console.error('Error calculating next runs:', e);
        }

        return runs;
    }

    calculateNextRun(cronExpr, fromDate) {
        // Simplified cron calculator (works for common patterns)
        const [minute, hour, day, month, dayOfWeek] = cronExpr.split(' ');
        const date = new Date(fromDate);

        if (this.mode === 'minutes') {
            date.setMinutes(date.getMinutes() + this.interval);
        } else if (this.mode === 'hours') {
            date.setHours(date.getHours() + this.interval);
        } else if (this.mode === 'daily') {
            date.setDate(date.getDate() + 1);
            date.setHours(this.hour);
            date.setMinutes(this.minute);
        } else if (this.mode === 'weekly') {
            date.setDate(date.getDate() + 7);
            date.setHours(this.hour);
            date.setMinutes(this.minute);
        } else if (this.mode === 'monthly') {
            date.setMonth(date.getMonth() + 1);
            date.setDate(this.day);
            date.setHours(this.hour);
            date.setMinutes(this.minute);
        } else {
            // For custom, add 1 hour (rough estimate)
            date.setHours(date.getHours() + 1);
        }

        return date;
    }

    formatDate(date) {
        const now = new Date();
        const diff = date - now;
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        let relative = '';
        if (days > 0) {
            relative = `in ${days}d ${hours % 24}h`;
        } else if (hours > 0) {
            relative = `in ${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            relative = `in ${minutes}m`;
        } else {
            relative = 'now';
        }

        const formatted = date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        return `${formatted} (${relative})`;
    }

    updatePreview() {
        const description = this.getDescription();
        const expression = this.getCronExpression();
        const nextRuns = this.getNextRuns(3);

        document.getElementById('cron-description').textContent = description;
        document.getElementById('cron-expression').textContent = expression;

        const nextRunsList = document.getElementById('next-runs-list');
        nextRunsList.innerHTML = nextRuns
            .map(date => `<li>${this.formatDate(date)}</li>`)
            .join('');
    }

    setFromCron(expression) {
        const [minute, hour, day, month, dayOfWeek] = expression.split(' ');

        // Detect mode from pattern
        if (minute.startsWith('*/')) {
            this.mode = 'minutes';
            this.interval = parseInt(minute.substring(2));
        } else if (hour.startsWith('*/')) {
            this.mode = 'hours';
            this.interval = parseInt(hour.substring(2));
            this.minute = parseInt(minute) || 0;
        } else if (dayOfWeek !== '*') {
            this.mode = 'weekly';
            this.dayOfWeek = parseInt(dayOfWeek);
            this.hour = parseInt(hour) || 0;
            this.minute = parseInt(minute) || 0;
        } else if (day !== '*') {
            this.mode = 'monthly';
            this.day = parseInt(day);
            this.hour = parseInt(hour) || 0;
            this.minute = parseInt(minute) || 0;
        } else if (hour !== '*' && minute !== '*') {
            this.mode = 'daily';
            this.hour = parseInt(hour) || 0;
            this.minute = parseInt(minute) || 0;
        } else {
            this.mode = 'custom';
            this.customCron = expression;
        }

        this.render();
        this.updatePreview();
    }
}

// Expose globally for inline event handlers
window.CronBuilder = CronBuilder;
