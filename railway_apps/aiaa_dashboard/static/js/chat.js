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

function _asPayloadObject(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        return null;
    }
    return value;
}

function _firstString(...values) {
    for (const value of values) {
        if (typeof value === 'string') {
            return value;
        }
    }
    return '';
}

function normalizeStreamEvent(eventData) {
    if (!eventData || typeof eventData !== 'object') {
        return null;
    }

    const payload = _asPayloadObject(eventData.payload);
    if (!payload) {
        return eventData;
    }

    if (eventData.type === 'tool') {
        const kind = _firstString(payload.kind).toLowerCase();
        if (kind === 'tool_use') {
            return {
                ...eventData,
                type: 'tool_use',
                tool: _firstString(eventData.tool, payload.tool),
                input: _firstString(eventData.input, payload.input, payload.content),
            };
        }
        if (kind === 'tool_result') {
            return {
                ...eventData,
                type: 'tool_result',
                content: _firstString(eventData.content, payload.content),
            };
        }
        return eventData;
    }

    if (eventData.type === 'result' || eventData.type === 'system' || eventData.type === 'error') {
        return {
            ...eventData,
            content: _firstString(eventData.content, payload.content),
        };
    }

    return eventData;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = String(text || '');
    return div.innerHTML;
}

function _stripInternalTranscriptArtifacts(text) {
    const raw = String(text || '');
    if (!raw) {
        return '';
    }

    let cleaned = raw;
    const hadToolTrace = /<tool_(?:call|response)>/i.test(cleaned);
    cleaned = cleaned.replace(/<tool_(?:call|response)>[\s\S]*?<\/tool_(?:call|response)>/gi, '');
    cleaned = cleaned.replace(/<\/?tool_(?:call|response)>/gi, '');

    if (hadToolTrace) {
        cleaned = cleaned.replace(
            /^\s*(phase\s+\d+[^\n]*|let me [^\n]*|i(?:'|’)ll [^\n]*(?:run|load|research)[^\n]*)\s*$/gim,
            '',
        );
    }

    cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();
    return cleaned || raw;
}

function _splitTableRow(line) {
    const normalized = String(line || '').trim();
    if (!normalized.includes('|')) {
        return [];
    }
    const withoutEdges = normalized.replace(/^\|/, '').replace(/\|$/, '');
    return withoutEdges.split('|').map((cell) => cell.trim());
}

function _isTableSeparatorCell(cell) {
    return /^:?-{3,}:?$/.test(String(cell || '').replace(/\s+/g, ''));
}

function _isTableSeparatorRow(line) {
    const cells = _splitTableRow(line);
    return cells.length > 0 && cells.every((cell) => _isTableSeparatorCell(cell));
}

function _tableAlignmentFromCell(cell) {
    const compact = String(cell || '').replace(/\s+/g, '');
    const starts = compact.startsWith(':');
    const ends = compact.endsWith(':');
    if (starts && ends) {
        return 'center';
    }
    if (ends) {
        return 'right';
    }
    return 'left';
}

function _renderInlineMarkdown(text) {
    let output = String(text || '');
    const codeTokens = [];

    output = output.replace(/`([^`]+)`/g, (_match, code) => {
        const token = `@@CODE_SPAN_${codeTokens.length}@@`;
        codeTokens.push(`<code>${code}</code>`);
        return token;
    });

    output = output.replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>',
    );

    output = output.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
    output = output.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    output = output.replace(/(^|[\s(>])\*([^*\n]+)\*(?=$|[\s),.!?:;])/g, '$1<em>$2</em>');
    output = output.replace(/(^|[\s(>])_([^_\n]+)_(?=$|[\s),.!?:;])/g, '$1<em>$2</em>');
    output = output.replace(/~~([^~\n]+)~~/g, '<del>$1</del>');

    output = output.replace(/@@CODE_SPAN_(\d+)@@/g, (_match, index) => {
        const parsed = Number(index);
        return codeTokens[parsed] || '';
    });

    return output.replace(/\n/g, '<br>');
}

function _renderMarkdownTable(headers, alignments, rows) {
    const headerHtml = headers.map((cell, index) => {
        const align = alignments[index] || 'left';
        const attr = align === 'left' ? '' : ` style="text-align:${align};"`;
        return `<th${attr}>${_renderInlineMarkdown(cell)}</th>`;
    }).join('');

    const bodyHtml = rows.map((row) => {
        const cells = row.map((cell, index) => {
            const align = alignments[index] || 'left';
            const attr = align === 'left' ? '' : ` style="text-align:${align};"`;
            return `<td${attr}>${_renderInlineMarkdown(cell)}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');

    return `<div class="chat-md-table-wrap"><table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
}

function _isMarkdownBlockBoundary(line, nextLine) {
    const trimmed = String(line || '').trim();
    if (!trimmed) {
        return true;
    }
    if (/^@@CODE_BLOCK_\d+@@$/.test(trimmed)) {
        return true;
    }
    if (/^(#{1,6})\s+/.test(trimmed)) {
        return true;
    }
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
        return true;
    }
    if (/^&gt;\s?/.test(trimmed)) {
        return true;
    }
    if (/^[-*+]\s+/.test(trimmed)) {
        return true;
    }
    if (/^\d+\.\s+/.test(trimmed)) {
        return true;
    }
    if (String(line || '').includes('|') && _isTableSeparatorRow(nextLine || '')) {
        return true;
    }
    return false;
}

function renderChatMarkdown(text) {
    if (!text) {
        return '';
    }

    const source = _stripInternalTranscriptArtifacts(String(text).replace(/\r\n/g, '\n'));
    const escaped = escapeHtml(source);
    const codeBlocks = [];
    const withCodePlaceholders = escaped.replace(/```([\w-]*)\n?([\s\S]*?)```/g, (_match, language, code) => {
        const token = `@@CODE_BLOCK_${codeBlocks.length}@@`;
        const safeLanguage = String(language || '').trim().replace(/[^\w-]/g, '');
        const classAttr = safeLanguage ? ` class="language-${safeLanguage}"` : '';
        codeBlocks.push(`<pre><code${classAttr}>${code}</code></pre>`);
        return token;
    });

    const lines = withCodePlaceholders.split('\n');
    const blocks = [];
    let index = 0;

    while (index < lines.length) {
        const line = lines[index];
        const trimmed = String(line || '').trim();

        if (!trimmed) {
            index += 1;
            continue;
        }

        if (/^@@CODE_BLOCK_\d+@@$/.test(trimmed)) {
            blocks.push(trimmed);
            index += 1;
            continue;
        }

        if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
            blocks.push('<hr>');
            index += 1;
            continue;
        }

        const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
        if (headingMatch) {
            const level = Math.min(6, Math.max(1, headingMatch[1].length));
            blocks.push(`<h${level}>${_renderInlineMarkdown(headingMatch[2])}</h${level}>`);
            index += 1;
            continue;
        }

        if (/^&gt;\s?/.test(trimmed)) {
            const quoteLines = [];
            while (index < lines.length) {
                const quoteLine = String(lines[index] || '').trim();
                const match = quoteLine.match(/^&gt;\s?(.*)$/);
                if (!match) {
                    break;
                }
                quoteLines.push(match[1]);
                index += 1;
            }
            blocks.push(`<blockquote>${_renderInlineMarkdown(quoteLines.join('\n'))}</blockquote>`);
            continue;
        }

        if (String(line || '').includes('|') && _isTableSeparatorRow(lines[index + 1] || '')) {
            const headers = _splitTableRow(line);
            const separator = _splitTableRow(lines[index + 1] || '');
            if (headers.length > 0 && separator.length === headers.length) {
                const alignments = separator.map((cell) => _tableAlignmentFromCell(cell));
                const rows = [];
                index += 2;
                while (index < lines.length) {
                    const rowLine = String(lines[index] || '');
                    const rowTrimmed = rowLine.trim();
                    if (!rowTrimmed || !rowLine.includes('|')) {
                        break;
                    }
                    let rowCells = _splitTableRow(rowLine);
                    if (rowCells.length === 0) {
                        break;
                    }
                    if (rowCells.length < headers.length) {
                        rowCells = rowCells.concat(Array(headers.length - rowCells.length).fill(''));
                    } else if (rowCells.length > headers.length) {
                        rowCells = rowCells.slice(0, headers.length);
                    }
                    rows.push(rowCells);
                    index += 1;
                }
                blocks.push(_renderMarkdownTable(headers, alignments, rows));
                continue;
            }
        }

        const unordered = trimmed.match(/^[-*+]\s+(.+)$/);
        if (unordered) {
            const items = [];
            while (index < lines.length) {
                const itemLine = String(lines[index] || '').trim();
                const match = itemLine.match(/^[-*+]\s+(.+)$/);
                if (!match) {
                    break;
                }
                items.push(`<li>${_renderInlineMarkdown(match[1])}</li>`);
                index += 1;
            }
            blocks.push(`<ul>${items.join('')}</ul>`);
            continue;
        }

        const ordered = trimmed.match(/^\d+\.\s+(.+)$/);
        if (ordered) {
            const items = [];
            while (index < lines.length) {
                const itemLine = String(lines[index] || '').trim();
                const match = itemLine.match(/^\d+\.\s+(.+)$/);
                if (!match) {
                    break;
                }
                items.push(`<li>${_renderInlineMarkdown(match[1])}</li>`);
                index += 1;
            }
            blocks.push(`<ol>${items.join('')}</ol>`);
            continue;
        }

        const paragraphLines = [line];
        index += 1;
        while (index < lines.length) {
            const nextLine = lines[index];
            const nextTrimmed = String(nextLine || '').trim();
            if (!nextTrimmed) {
                break;
            }
            if (_isMarkdownBlockBoundary(nextLine, lines[index + 1])) {
                break;
            }
            paragraphLines.push(nextLine);
            index += 1;
        }
        blocks.push(`<p>${_renderInlineMarkdown(paragraphLines.join('\n'))}</p>`);
    }

    let html = blocks.join('\n');
    html = html.replace(/@@CODE_BLOCK_(\d+)@@/g, (_match, tokenIndex) => {
        const parsed = Number(tokenIndex);
        return codeBlocks[parsed] || '';
    });
    return html;
}

if (typeof globalThis !== 'undefined') {
    globalThis.ChatUIErrorMessages = {
        isGatewayAuthFailure,
        isRuntimeFailure,
        formatChatErrorMessage,
    };
    globalThis.ChatUIStreamEvents = {
        normalizeStreamEvent,
    };
    globalThis.ChatUIMarkdown = {
        renderChatMarkdown,
    };
}

class ChatUI {
    static STREAM_RENDER_MIN_INTERVAL_MS = 48;

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

    getSessionStatus(sessionId) {
        const session = this.sessions.find((item) => item.id === sessionId);
        return session ? String(session.status || '').toLowerCase() : '';
    }

    getSessionLastError(sessionId) {
        const session = this.sessions.find((item) => item.id === sessionId);
        return session ? String(session.last_error || '').trim() : '';
    }

    async fetchSessionState(sessionId) {
        if (!sessionId) {
            return null;
        }
        const resp = await fetchAPI(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
            method: 'GET',
            showError: false,
        });
        const sessionObj = resp && resp.session && typeof resp.session === 'object'
            ? resp.session
            : null;
        if (!sessionObj) {
            return null;
        }
        const snapshot = {
            id: String(sessionObj.id || sessionId),
            title: String(sessionObj.title || 'New chat'),
            status: String(sessionObj.status || ''),
            last_error: String(sessionObj.last_error || ''),
            updated_at: sessionObj.updated_at || '',
        };
        const existingIndex = this.sessions.findIndex((item) => item.id === snapshot.id);
        if (existingIndex >= 0) {
            this.sessions[existingIndex] = { ...this.sessions[existingIndex], ...snapshot };
        } else {
            this.sessions.unshift(snapshot);
        }
        return snapshot;
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
        const content = text || '';
        if (role === 'assistant') {
            bubble.classList.add('markdown');
            bubble.dataset.rawContent = content;
            bubble.innerHTML = renderChatMarkdown(content);
        } else {
            bubble.textContent = content;
        }

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
        bubble.classList.add('markdown');
        bubble.dataset.rawContent = '';
        bubble.innerHTML = '';

        const trace = document.createElement('details');
        trace.className = 'chat-tool-trace';
        trace.hidden = true;

        const summary = document.createElement('summary');
        summary.className = 'chat-tool-trace-summary';

        const traceLabel = document.createElement('span');
        traceLabel.className = 'chat-tool-trace-label';
        traceLabel.textContent = 'Agent activity';

        const traceCount = document.createElement('span');
        traceCount.className = 'chat-tool-trace-count';
        traceCount.textContent = '(0)';

        summary.appendChild(traceLabel);
        summary.appendChild(traceCount);

        const steps = document.createElement('div');
        steps.className = 'chat-tool-steps';

        trace.appendChild(summary);
        trace.appendChild(steps);
        row.appendChild(bubble);
        row.appendChild(trace);
        this.messagesEl.appendChild(row);
        this.scrollToBottom();
        return {
            row,
            bubble,
            trace,
            steps,
            traceCount,
            stepCount: 0,
            lastStepSignature: '',
            lastStepRepeatCount: 1,
            lastStepEl: null,
            pendingText: '',
            renderScheduled: false,
            lastRenderAt: 0,
        };
    }

    appendText(agentBubble, content) {
        if (!agentBubble || !content) {
            return;
        }
        agentBubble.pendingText = (agentBubble.pendingText || '') + content;
        this.scheduleBubbleRender(agentBubble);
    }

    scheduleBubbleRender(agentBubble) {
        if (!agentBubble || agentBubble.renderScheduled) {
            return;
        }
        agentBubble.renderScheduled = true;

        const flush = () => {
            agentBubble.renderScheduled = false;
            this.flushBubbleRender(agentBubble);
        };
        const now = Date.now();
        const lastRenderAt = Number(agentBubble.lastRenderAt || 0);
        const elapsed = Math.max(0, now - lastRenderAt);
        const delay = Math.max(0, ChatUI.STREAM_RENDER_MIN_INTERVAL_MS - elapsed);
        setTimeout(flush, delay);
    }

    flushBubbleRender(agentBubble) {
        if (!agentBubble) {
            return;
        }
        const pending = String(agentBubble.pendingText || '');
        if (!pending) {
            return;
        }
        const existing = agentBubble.bubble.dataset.rawContent || '';
        const next = existing + pending;
        agentBubble.pendingText = '';
        agentBubble.bubble.dataset.rawContent = next;
        agentBubble.bubble.innerHTML = renderChatMarkdown(next);
        agentBubble.lastRenderAt = Date.now();
        this.scrollToBottom();
    }

    appendToolStep(agentBubble, label, content) {
        if (!agentBubble) {
            return;
        }

        const safeLabel = String(label || 'Tool').trim() || 'Tool';
        const safeContent = String(content || '').trim();
        const signature = `${safeLabel}::${safeContent}`;

        if (signature && agentBubble.lastStepSignature === signature && agentBubble.lastStepEl) {
            agentBubble.lastStepRepeatCount += 1;
            const suffix = ` (x${agentBubble.lastStepRepeatCount})`;
            agentBubble.lastStepEl.textContent = `${safeLabel}: ${safeContent}${suffix}`;
            this.scrollToBottom();
            return;
        }

        const item = document.createElement('div');
        item.className = 'chat-tool-step';
        item.textContent = `${safeLabel}: ${safeContent}`;
        agentBubble.steps.appendChild(item);
        agentBubble.stepCount = Number(agentBubble.stepCount || 0) + 1;
        if (agentBubble.traceCount) {
            agentBubble.traceCount.textContent = `(${agentBubble.stepCount})`;
        }
        if (agentBubble.trace) {
            agentBubble.trace.hidden = false;
        }
        agentBubble.lastStepSignature = signature;
        agentBubble.lastStepEl = item;
        agentBubble.lastStepRepeatCount = 1;
        this.scrollToBottom();
    }

    appendError(agentBubble, content) {
        const message = formatChatErrorMessage(content);
        if (agentBubble && agentBubble.bubble) {
            agentBubble.row.classList.add('error');
            agentBubble.bubble.classList.remove('markdown');
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
        const raw = String(agentBubble.bubble.dataset.rawContent || '').trim();
        if (!raw) {
            agentBubble.bubble.dataset.rawContent = 'Completed.';
            agentBubble.bubble.innerHTML = renderChatMarkdown('Completed.');
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
            const parsed = normalizeStreamEvent(data);
            if (!parsed) {
                return;
            }

            switch (parsed.type) {
                case 'tool_use':
                    this.appendToolStep(agentBubble, parsed.tool || 'Tool', parsed.input || '');
                    break;
                case 'tool_result':
                    this.appendToolStep(agentBubble, 'Result', parsed.content || '');
                    break;
                case 'text':
                case 'result':
                    this.appendText(agentBubble, parsed.content || '');
                    break;
                case 'system':
                    this.appendToolStep(agentBubble, 'System', parsed.content || '');
                    break;
                case 'error':
                    terminalReceived = true;
                    this.flushBubbleRender(agentBubble);
                    this.appendError(agentBubble, parsed.content || 'Agent failed');
                    this.setSending(false);
                    this.closeStream();
                    this.refreshSessions();
                    break;
                case 'done':
                    terminalReceived = true;
                    this.flushBubbleRender(agentBubble);
                    this.markComplete(agentBubble);
                    this.setSending(false);
                    this.closeStream();
                    this.refreshSessions();
                    break;
                default:
                    break;
            }
        };

        es.onerror = async () => {
            // EventSource may emit an error event when the server closes normally.
            if (!terminalReceived) {
                // Let EventSource reconnect automatically for transient network interruptions.
                if (es.readyState === EventSource.CONNECTING) {
                    return;
                }
                let shouldShowDropError = true;
                let fallbackMessage = '';
                try {
                    const state = await this.fetchSessionState(sessionId);
                    if (state) {
                        const status = String(state.status || '').toLowerCase();
                        fallbackMessage = String(state.last_error || '').trim();
                        if (!fallbackMessage) {
                            shouldShowDropError = status === 'running';
                        }
                    } else if (es.readyState === EventSource.CLOSED) {
                        await this.refreshSessions();
                        shouldShowDropError = this.getSessionStatus(sessionId) === 'running';
                        fallbackMessage = this.getSessionLastError(sessionId);
                    }
                } catch (error) {
                    if (es.readyState === EventSource.CLOSED) {
                        try {
                            await this.refreshSessions();
                            shouldShowDropError = this.getSessionStatus(sessionId) === 'running';
                            fallbackMessage = this.getSessionLastError(sessionId);
                        } catch (_refreshError) {
                            shouldShowDropError = true;
                        }
                    }
                }
                if (fallbackMessage) {
                    this.appendError(agentBubble, fallbackMessage);
                } else if (shouldShowDropError) {
                    this.appendError(agentBubble, 'The chat runtime connection dropped before completion.');
                }
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
