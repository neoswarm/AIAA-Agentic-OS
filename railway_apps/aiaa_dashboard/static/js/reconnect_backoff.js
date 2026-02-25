/**
 * Reconnection/backoff utilities for transient frontend disconnects.
 */
(function(global) {
    const DEFAULT_BASE_DELAY_MS = 2000;
    const DEFAULT_MAX_DELAY_MS = 30000;

    /**
     * Calculate exponential reconnect delay with an upper cap.
     * @param {number} attempt - Reconnect attempt count (1-based)
     * @param {Object} options - Optional delay overrides
     * @param {number} options.baseDelayMs - Base delay in milliseconds
     * @param {number} options.maxDelayMs - Maximum delay in milliseconds
     * @returns {number} - Delay in milliseconds
     */
    function calculateReconnectDelay(attempt, options = {}) {
        const baseDelayMs = Number.isFinite(options.baseDelayMs) && options.baseDelayMs > 0
            ? options.baseDelayMs
            : DEFAULT_BASE_DELAY_MS;
        const maxDelayMs = Number.isFinite(options.maxDelayMs) && options.maxDelayMs > 0
            ? options.maxDelayMs
            : DEFAULT_MAX_DELAY_MS;
        const normalizedAttempt = Math.max(1, Math.floor(Number(attempt) || 1));
        const delay = baseDelayMs * Math.pow(2, normalizedAttempt - 1);
        return Math.min(maxDelayMs, delay);
    }

    global.calculateReconnectDelay = calculateReconnectDelay;
})(typeof window !== 'undefined' ? window : globalThis);
