import test from 'node:test';
import assert from 'node:assert/strict';

await import('./event_stream_utils.js');

const { EventStreamUtils } = globalThis;

test('getEventId extracts supported event ID fields', () => {
    assert.equal(EventStreamUtils.getEventId({ id: 42 }), '42');
    assert.equal(EventStreamUtils.getEventId({ event_id: 'evt-7' }), 'evt-7');
    assert.equal(EventStreamUtils.getEventId('evt-9'), 'evt-9');
    assert.equal(EventStreamUtils.getEventId({}), null);
});

test('createEventIdTracker skips duplicate IDs and allows new IDs', () => {
    const tracker = EventStreamUtils.createEventIdTracker();

    assert.equal(tracker.shouldProcess({ id: 'evt-1' }), true);
    assert.equal(tracker.shouldProcess({ id: 'evt-1' }), false);
    assert.equal(tracker.shouldProcess({ event_id: 'evt-2' }), true);
});

test('createEventIdTracker treats missing IDs as processable', () => {
    const tracker = EventStreamUtils.createEventIdTracker();

    assert.equal(tracker.shouldProcess({ type: 'output' }), true);
    assert.equal(tracker.shouldProcess(null), true);
    assert.equal(tracker.shouldProcess(undefined), true);
});

test('createEventIdTracker evicts old IDs when capacity is reached', () => {
    const tracker = EventStreamUtils.createEventIdTracker(2);

    assert.equal(tracker.shouldProcess('evt-1'), true);
    assert.equal(tracker.shouldProcess('evt-2'), true);
    assert.equal(tracker.shouldProcess('evt-3'), true);

    // evt-1 was evicted due to capacity, so it is processable again.
    assert.equal(tracker.shouldProcess('evt-1'), true);
});
