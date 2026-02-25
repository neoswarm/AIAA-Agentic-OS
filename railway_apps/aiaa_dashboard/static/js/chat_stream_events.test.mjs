import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

globalThis.document = { addEventListener() {} };

const moduleUrl = pathToFileURL(
    path.resolve('railway_apps/aiaa_dashboard/static/js/chat.js')
).href;

await import(moduleUrl);

const helpers = globalThis.ChatUIStreamEvents;

test('normalizer is exposed globally', () => {
    assert.equal(typeof helpers, 'object');
    assert.equal(typeof helpers.normalizeStreamEvent, 'function');
});

test('normalizer preserves legacy chat stream events', () => {
    const legacy = {
        type: 'tool_use',
        tool: 'Read',
        input: 'Reading ./README.md',
    };

    const normalized = helpers.normalizeStreamEvent(legacy);

    assert.deepEqual(normalized, legacy);
});

test('normalizer maps translated gateway tool use events', () => {
    const translated = {
        type: 'tool',
        payload: {
            kind: 'tool_use',
            tool: 'Bash',
            input: 'npm test',
        },
    };

    const normalized = helpers.normalizeStreamEvent(translated);

    assert.equal(normalized.type, 'tool_use');
    assert.equal(normalized.tool, 'Bash');
    assert.equal(normalized.input, 'npm test');
});

test('normalizer maps translated gateway tool result events', () => {
    const translated = {
        type: 'tool',
        payload: {
            kind: 'tool_result',
            content: 'All tests passed',
        },
    };

    const normalized = helpers.normalizeStreamEvent(translated);

    assert.equal(normalized.type, 'tool_result');
    assert.equal(normalized.content, 'All tests passed');
});

test('normalizer maps translated result/system/error content payloads', () => {
    const translatedResult = helpers.normalizeStreamEvent({
        type: 'result',
        payload: { content: 'assistant chunk' },
    });
    const translatedSystem = helpers.normalizeStreamEvent({
        type: 'system',
        payload: { content: 'using profile safe' },
    });
    const translatedError = helpers.normalizeStreamEvent({
        type: 'error',
        payload: { content: 'gateway auth failed' },
    });

    assert.equal(translatedResult.content, 'assistant chunk');
    assert.equal(translatedSystem.content, 'using profile safe');
    assert.equal(translatedError.content, 'gateway auth failed');
});
