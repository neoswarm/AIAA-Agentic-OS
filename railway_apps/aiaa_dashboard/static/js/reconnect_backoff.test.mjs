import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const moduleUrl = pathToFileURL(
    path.resolve('railway_apps/aiaa_dashboard/static/js/reconnect_backoff.js')
).href;

await import(moduleUrl);

test('calculateReconnectDelay is exposed globally', () => {
    assert.equal(typeof globalThis.calculateReconnectDelay, 'function');
});

test('calculateReconnectDelay applies exponential backoff and cap', () => {
    const calc = globalThis.calculateReconnectDelay;
    const opts = { baseDelayMs: 1000, maxDelayMs: 8000 };

    assert.equal(calc(1, opts), 1000);
    assert.equal(calc(2, opts), 2000);
    assert.equal(calc(3, opts), 4000);
    assert.equal(calc(4, opts), 8000);
    assert.equal(calc(5, opts), 8000);
});

test('calculateReconnectDelay normalizes invalid inputs', () => {
    const calc = globalThis.calculateReconnectDelay;

    assert.equal(calc(0, { baseDelayMs: 1000, maxDelayMs: 8000 }), 1000);
    assert.equal(calc(-5, { baseDelayMs: 1000, maxDelayMs: 8000 }), 1000);
    assert.equal(calc('3', { baseDelayMs: 1000, maxDelayMs: 8000 }), 4000);
    assert.equal(calc(2, { baseDelayMs: -1, maxDelayMs: 5000 }), 4000);
});
