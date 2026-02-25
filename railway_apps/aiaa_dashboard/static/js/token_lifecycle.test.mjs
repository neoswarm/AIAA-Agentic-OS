import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const moduleUrl = pathToFileURL(
    path.resolve('railway_apps/aiaa_dashboard/static/js/token_lifecycle.js')
).href;

await import(moduleUrl);

const { TokenLifecycle } = globalThis;

test('normalizeTokenValidationStatus maps empty statuses by configured state', () => {
    assert.equal(TokenLifecycle.normalizeTokenValidationStatus('', true), 'valid');
    assert.equal(TokenLifecycle.normalizeTokenValidationStatus('', false), 'missing');
});

test('normalizeTokenValidationStatus supports backend aliases', () => {
    assert.equal(TokenLifecycle.normalizeTokenValidationStatus('success', true), 'valid');
    assert.equal(TokenLifecycle.normalizeTokenValidationStatus('network_error', true), 'unreachable');
});

test('mapTokenValidationToUi maps lifecycle statuses to ui labels', () => {
    assert.deepEqual(
        TokenLifecycle.mapTokenValidationToUi('valid', true),
        { statusClass: 'valid', text: 'Connected' }
    );
    assert.deepEqual(
        TokenLifecycle.mapTokenValidationToUi('expired', true),
        { statusClass: 'invalid', text: 'Expired token' }
    );
    assert.deepEqual(
        TokenLifecycle.mapTokenValidationToUi('invalid', true),
        { statusClass: 'invalid', text: 'Invalid token' }
    );
    assert.deepEqual(
        TokenLifecycle.mapTokenValidationToUi('timeout', true),
        { statusClass: 'warning', text: 'Validation unreachable' }
    );
    assert.deepEqual(
        TokenLifecycle.mapTokenValidationToUi(undefined, false),
        { statusClass: 'missing', text: 'Not configured' }
    );
});

test('mapTokenMetadataToUi reads configured/validation_status payloads', () => {
    assert.deepEqual(
        TokenLifecycle.mapTokenMetadataToUi({ configured: true, validation_status: 'error' }),
        { statusClass: 'warning', text: 'Validation unreachable' }
    );
    assert.deepEqual(
        TokenLifecycle.mapTokenMetadataToUi({ configured: false, validation_status: 'valid' }),
        { statusClass: 'missing', text: 'Not configured' }
    );
});
