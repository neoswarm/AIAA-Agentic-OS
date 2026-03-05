import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

globalThis.document = {
    addEventListener() {},
    createElement() {
        let rawText = '';
        return {
            set textContent(value) {
                rawText = escapeHtml(value);
            },
            get innerHTML() {
                return rawText;
            },
        };
    },
};

const moduleUrl = pathToFileURL(
    path.resolve('railway_apps/aiaa_dashboard/static/js/chat.js')
).href;

await import(moduleUrl);

const helpers = globalThis.ChatUIErrorMessages;
const markdown = globalThis.ChatUIMarkdown;

test('chat error helpers are exposed globally', () => {
    assert.equal(typeof helpers, 'object');
    assert.equal(typeof helpers.formatChatErrorMessage, 'function');
});

test('chat markdown renderer is exposed globally', () => {
    assert.equal(typeof markdown, 'object');
    assert.equal(typeof markdown.renderChatMarkdown, 'function');
});

test('gateway auth failures map to actionable settings guidance', () => {
    const message = helpers.formatChatErrorMessage(
        'Gateway authentication failed: unauthorized (401)'
    );
    assert.equal(
        message,
        'Claude gateway authentication failed. Check your Anthropic API key in Settings and try again.'
    );
});

test('runtime failures map to retry guidance', () => {
    const message = helpers.formatChatErrorMessage(
        'Command failed with exit code 1\nCheck stderr output for details'
    );
    assert.equal(
        message,
        'The chat runtime failed before completion. Retry your message, or start a new session if this keeps happening.'
    );
});

test('non-classified errors are preserved', () => {
    const message = helpers.formatChatErrorMessage('Session is already running');
    assert.equal(message, 'Session is already running');
});

test('markdown renderer formats headings and inline emphasis', () => {
    const html = markdown.renderChatMarkdown('# Title\n\nThis is **bold** and *italic* text.');
    assert.match(html, /<h1>Title<\/h1>/);
    assert.match(html, /<strong>bold<\/strong>/);
    assert.match(html, /<em>italic<\/em>/);
});

test('markdown renderer formats tables with alignment', () => {
    const md = '| Name | Score |\n| :--- | ---: |\n| Alice | 9 |\n| Bob | 7 |';
    const html = markdown.renderChatMarkdown(md);
    assert.match(html, /<table>/);
    assert.match(html, /<th[^>]*>Name<\/th>/);
    assert.match(html, /<th style="text-align:right;">Score<\/th>/);
    assert.match(html, /<td>Alice<\/td>/);
    assert.match(html, /<td style="text-align:right;">9<\/td>/);
});

test('markdown renderer strips internal tool transcript artifacts', () => {
    const md = [
        "I'll research this now.",
        'Phase 1-3: Skill Check',
        '',
        '<tool_call>',
        '{"name":"read_file","parameters":{"path":"context/agency.md"}}',
        '</tool_call>',
        '<tool_response>Agency context loaded.</tool_response>',
        '',
        '## Final Summary',
        'Company has strong positioning.',
    ].join('\n');

    const html = markdown.renderChatMarkdown(md);
    assert.doesNotMatch(html, /tool_call/i);
    assert.doesNotMatch(html, /tool_response/i);
    assert.doesNotMatch(html, /Phase 1-3/i);
    assert.match(html, /<h2>Final Summary<\/h2>/);
    assert.match(html, /Company has strong positioning/);
});
