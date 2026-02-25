/**
 * Dashboard chat UI for Claude agent streaming.
 */

function includesAny(value, needles) {
    return needles.some((needle) => value.includes(needle));
}

function isGatewayAuthFailure(message) {
    const text = String(message || '').toLowerCase();
    if (!text) {
        return false;
    }
    return includesAny(text, [
        'gateway auth',
        'gateway authentication',
        'authentication failed',
        'unauthorized',
        'invalid api key',
        'invalid x-api-key',
        'invalid x-api key',
        'anthropic_api_key',
        'anthropic_auth_token',
        '401',
        'forbidden',
        'permission denied',
    ]);
}

function isRuntimeFailure(message) {
    const text = String(message || '').toLowerCase();
    if (!text) {
        return false;
    }
    return includesAny(text, [
        'agent execution failed',
        'runtime failed',
        'command failed with exit code',
        'check stderr output for details',
        'cli stderr',
        'internal error',
    ]);
}

function formatChatErrorMessage(message) {
    const text = String(message || '').trim();
    if (isGatewayAuthFailure(text)) {
        return 'Claude gateway authentication failed. Check your Anthropic API key in Settings and try again.';
    }
    if (isRuntimeFailure(text)) {
        return 'The chat runtime failed before completion. Retry your message, or start a new session if this keeps happening.';
    }
    return text || 'Chat failed. Please try again.';
}

if (typeof globalThis !== 'undefined') {
    globalThis.ChatUIErrorMessages = {
        isGatewayAuthFailure,
        isRuntimeFailure,
        formatChatErrorMessage,
    };
}

class ChatUI {
    constructor() {
        this.sessionId = null;
        this.eventSource = null;
        this.currentAgentBubble = null;
        this.sessions = Array.isArray(window.chatInitialSessions) ? window.chatInitialSessions : [];
        this.hasToken = window.chatHasToken === true || window.chatHasToken === 'true';

        this.sessionListEl = document.getElementById('chatSessionList');
        this.messagesEl = document.getElementById('chatMessages');
        this.emptyEl = document.getElementById('chatEmptyState');
        this.formEl = document.getElementById('chatComposer');
        this.inputEl = document.getElementById('chatInput');
        this.sendBtnEl = document.getElementById('chatSendBtn');
        this.newSessionBtnEl = document.getElementById('newSessionBtn');
    }

    init() {
        if (!this.formEl || !this.messagesEl) {
            return;
        }

        this.bindEvents();
        this.renderSessions();

        if (this.sessions.length > 0) {
            this.openSession(this.sessions[0].id);
        }
    }

    bindEvents() {
        this.formEl.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleSend();
        });

        this.inputEl.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.handleSend();
            }
        });

        this.newSessionBtnEl.addEventListener('click', () => this.createNewSession(true));

        this.sessionListEl.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-session-id]');
            if (!btn) {
                return;
            }
            const sessionId = btn.getAttribute('data-session-id');
            if (sessionId) {
                this.openSession(sessionId);
            }
        });

        document.querySelectorAll('[data-quick-prompt]').forEach((btn) => {
            btn.addEventListener('click', () => {
                this.inputEl.value = btn.getAttribute('data-quick-prompt') || '';
                this.inputEl.focus();
            });
        });
    }

    async refreshSessions() {
        try {
            const data = await fetchAPI('/api/chat/sessions', { method: 'GET', showError: false });
            if (data && Array.isArray(data.sessions)) {
                this.sessions = data.sessions;
                this.renderSessions();
            }
        } catch (error) {
            // Keep existing local session list if refresh fails.
        }
    }

    renderSessions() {
        this.sessionListEl.innerHTML = '';
        if (!this.sessions.length) {
            const empty = document.createElement('div');
            empty.className = 'chat-empty';
            empty.textContent = 'No sessions yet. Start a new chat.';
            this.sessionListEl.appendChild(empty);
            return;
        }

        this.sessions.forEach((session) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'chat-session-item' + (session.id === this.sessionId ? ' active' : '');
            button.setAttribute('data-session-id', session.id);

            const title = document.createElement('span');
            title.className = 'chat-session-title';
            title.textContent = session.title || 'New chat';

            const meta = document.createElement('span');
            meta.className = 'chat-session-meta';
            meta.textContent = this.formatSessionMeta(session);

            button.appendChild(title);
            button.appendChild(meta);
            this.sessionListEl.appendChild(button);
        });
    }

    formatSessionMeta(session) {
        const status = session.status || 'idle';
        const updated = session.updated_at ? new Date(session.updated_at) : null;
        if (!updated || Number.isNaN(updated.getTime())) {
            return status;
        }
        return `${status} • ${updated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }

    async createNewSession(selectAfterCreate = false) {
        if (!this.hasToken) {
            showToast('Claude token is required before creating sessions.', 'warning');
            return null;
        }

        const resp = await fetchAPI('/api/chat/sessions', {
            method: 'POST',
            body: JSON.stringify({}),
        });

        const created = resp.session || { id: resp.session_id };
        if (created && created.id) {
            this.sessions.unshift(created);
            this.sessionId = created.id;
            this.renderSessions();
            if (selectAfterCreate) {
                this.renderMessages([]);
            }
            return created.id;
        }
        return null;
    }

    async openSession(sessionId) {
        if (!sessionId) {
            return;
        }
        this.closeStream();
        this.sessionId = sessionId;
        this.renderSessions();

        try {
            const resp = await fetchAPI(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
                method: 'GET',
                showError: false,
            });
            const sessionObj = resp.session || {};
            this.renderMessages(sessionObj.messages || []);

            if (sessionObj.status === 'running') {
                this.currentAgentBubble = this.createAgentBubble();
                this.startStream(sessionId, this.currentAgentBubble);
            }
        } catch (error) {
            this.renderMessages([]);
            showToast('Could not load session history.', 'warning');
        }
    }

    renderMessages(messages) {
        this.messagesEl.innerHTML = '';
        if (!messages.length) {
            const empty = document.createElement('div');
            empty.className = 'chat-empty';
            empty.id = 'chatEmptyState';
            empty.textContent = 'Send a message to start. Tool activity and final outputs stream here in real time.';
            this.messagesEl.appendChild(empty);
            this.emptyEl = empty;
            return;
        }
        this.emptyEl = null;

        messages.forEach((message) => {
            const role = message.role === 'assistant' ? 'assistant' : 'user';
            this.appendMessage(role, message.content || '');
        });
        this.scrollToBottom();
    }

    ensureMessagesVisible() {
        if (this.emptyEl && this.emptyEl.parentElement) {
            this.emptyEl.remove();
            this.emptyEl = null;
        }
    }

    appendMessage(role, text) {
        this.ensureMessagesVisible();

        const row = document.createElement('div');
        row.className = `chat-message ${role}`;

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        bubble.textContent = text || '';

        row.appendChild(bubble);
        this.messagesEl.appendChild(row);
        this.scrollToBottom();
        return { row, bubble };
    }

    createAgentBubble() {
        this.ensureMessagesVisible();

        const row = document.createElement('div');
        row.className = 'chat-message assistant';

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';
        bubble.textContent = '';

        const steps = document.createElement('div');
        steps.className = 'chat-tool-steps';

        row.appendChild(bubble);
        row.appendChild(steps);
        this.messagesEl.appendChild(row);
        this.scrollToBottom();
        return { row, bubble, steps };
    }

    appendText(agentBubble, content) {
        if (!agentBubble || !content) {
            return;
        }
        const existing = agentBubble.bubble.textContent || '';
        agentBubble.bubble.textContent = existing + content;
        this.scrollToBottom();
    }

    appendToolStep(agentBubble, label, content) {
        if (!agentBubble) {
            return;
        }
        const item = document.createElement('div');
        item.className = 'chat-tool-step';
        item.textContent = `${label}: ${content || ''}`;
        agentBubble.steps.appendChild(item);
        this.scrollToBottom();
    }

    appendError(agentBubble, content) {
        const message = formatChatErrorMessage(content);
        if (agentBubble && agentBubble.bubble) {
            agentBubble.row.classList.add('error');
            agentBubble.bubble.textContent = message;
            this.scrollToBottom();
            return;
        }
        this.appendMessage('error', message);
    }

    markComplete(agentBubble) {
        if (!agentBubble) {
            return;
        }
        if (!agentBubble.bubble.textContent.trim()) {
            agentBubble.bubble.textContent = 'Completed.';
        }
    }

    async handleSend() {
        const text = (this.inputEl.value || '').trim();
        if (!text) {
            return;
        }
        if (!this.hasToken) {
            showToast('Claude token is not configured. Add it in Settings.', 'warning');
            return;
        }

        if (!this.sessionId) {
            const createdId = await this.createNewSession(true);
            if (!createdId) {
                return;
            }
        }

        this.appendMessage('user', text);
        this.inputEl.value = '';
        this.setSending(true);

        try {
            await fetchAPI('/api/chat/message', {
                method: 'POST',
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: text,
                }),
            });
        } catch (error) {
            this.appendError(null, error && error.message);
            this.setSending(false);
            return;
        }

        this.currentAgentBubble = this.createAgentBubble();
        this.startStream(this.sessionId, this.currentAgentBubble);
        this.refreshSessions();
    }

    startStream(sessionId, agentBubble) {
        this.closeStream();
        const streamUrl = `/api/chat/stream/${encodeURIComponent(sessionId)}`;
        const es = new EventSource(streamUrl);
        let terminalReceived = false;
        this.eventSource = es;

        es.onmessage = (event) => {
            let data = null;
            try {
                data = JSON.parse(event.data);
            } catch (err) {
                return;
            }

            switch (data.type) {
                case 'tool_use':
                    this.appendToolStep(agentBubble, data.tool || 'Tool', data.input || '');
                    break;
                case 'tool_result':
                    this.appendToolStep(agentBubble, 'Result', data.content || '');
                    break;
                case 'text':
                case 'result':
                    this.appendText(agentBubble, data.content || '');
                    break;
                case 'system':
                    this.appendToolStep(agentBubble, 'System', data.content || '');
                    break;
                case 'error':
                    terminalReceived = true;
                    this.appendError(agentBubble, data.content || 'Agent failed');
                    this.setSending(false);
                    this.closeStream();
                    this.refreshSessions();
                    break;
                case 'done':
                    terminalReceived = true;
                    this.markComplete(agentBubble);
                    this.setSending(false);
                    this.closeStream();
                    this.refreshSessions();
                    break;
                default:
                    break;
            }
        };

        es.onerror = () => {
            // EventSource may emit onerror once before close; close defensively.
            if (!terminalReceived) {
                this.appendError(agentBubble, 'The chat runtime connection dropped before completion.');
            }
            this.setSending(false);
            this.closeStream();
            this.refreshSessions();
        };
    }

    closeStream() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    setSending(isSending) {
        this.sendBtnEl.disabled = isSending;
        this.sendBtnEl.textContent = isSending ? 'Running...' : 'Send';
    }

    scrollToBottom() {
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }
}


if (typeof document !== 'undefined') {
    document.addEventListener('DOMContentLoaded', () => {
        const ui = new ChatUI();
        ui.init();
    });
}
