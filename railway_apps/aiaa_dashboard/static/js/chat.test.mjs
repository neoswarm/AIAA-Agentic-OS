import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

globalThis.document = { addEventListener() {} };

const moduleUrl = pathToFileURL(
    path.resolve('railway_apps/aiaa_dashboard/static/js/chat.js')
).href;

await import(moduleUrl);

const helpers = globalThis.ChatUIErrorMessages;

test('chat error helpers are exposed globally', () => {
    assert.equal(typeof helpers, 'object');
    assert.equal(typeof helpers.formatChatErrorMessage, 'function');
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

