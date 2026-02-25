/**
 * Event stream helpers for reconnect-safe frontend updates.
 * Prevents duplicate processing when servers replay events after reconnect.
 */
(function(root) {
    function getEventId(eventOrId) {
        if (eventOrId === null || eventOrId === undefined) return null;

        if (typeof eventOrId !== 'object') {
            var rawId = String(eventOrId).trim();
            return rawId ? rawId : null;
        }

        var candidate = eventOrId.id;
        if (candidate === null || candidate === undefined || candidate === '') {
            candidate = eventOrId.event_id;
        }

        if (candidate === null || candidate === undefined || candidate === '') {
            return null;
        }

        return String(candidate).trim() || null;
    }

    function createEventIdTracker(maxTrackedIds) {
        var limit = Number(maxTrackedIds) || 2000;
        if (limit < 1) limit = 1;

        var seenIds = new Set();
        var idQueue = [];

        function remember(id) {
            seenIds.add(id);
            idQueue.push(id);

            while (idQueue.length > limit) {
                var evicted = idQueue.shift();
                seenIds.delete(evicted);
            }
        }

        return {
            shouldProcess: function(eventOrId) {
                var eventId = getEventId(eventOrId);
                if (!eventId) return true;
                if (seenIds.has(eventId)) return false;

                remember(eventId);
                return true;
            },
            reset: function() {
                seenIds.clear();
                idQueue.length = 0;
            }
        };
    }

    root.EventStreamUtils = {
        getEventId: getEventId,
        createEventIdTracker: createEventIdTracker
    };
})(typeof globalThis !== 'undefined' ? globalThis : this);
