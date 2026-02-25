(function(globalScope) {
    var TOKEN_STATUSES = {
        valid: "valid",
        expired: "expired",
        invalid: "invalid",
        unreachable: "unreachable",
        missing: "missing"
    };

    var TOKEN_STATUS_ALIASES = {
        active: TOKEN_STATUSES.valid,
        ok: TOKEN_STATUSES.valid,
        success: TOKEN_STATUSES.valid,
        error: TOKEN_STATUSES.unreachable,
        timeout: TOKEN_STATUSES.unreachable,
        network_error: TOKEN_STATUSES.unreachable,
        connection_error: TOKEN_STATUSES.unreachable
    };

    function normalizeTokenValidationStatus(rawStatus, configured) {
        if (rawStatus === null || rawStatus === undefined || rawStatus === "") {
            return configured ? TOKEN_STATUSES.valid : TOKEN_STATUSES.missing;
        }

        var normalized = String(rawStatus).trim().toLowerCase();
        if (TOKEN_STATUSES[normalized]) {
            return normalized;
        }

        if (TOKEN_STATUS_ALIASES[normalized]) {
            return TOKEN_STATUS_ALIASES[normalized];
        }

        return configured ? TOKEN_STATUSES.unreachable : TOKEN_STATUSES.missing;
    }

    function mapTokenValidationToUi(rawStatus, configured) {
        var normalized = normalizeTokenValidationStatus(rawStatus, configured);

        switch (normalized) {
            case TOKEN_STATUSES.valid:
                return { statusClass: "valid", text: "Connected" };
            case TOKEN_STATUSES.expired:
                return { statusClass: "invalid", text: "Expired token" };
            case TOKEN_STATUSES.invalid:
                return { statusClass: "invalid", text: "Invalid token" };
            case TOKEN_STATUSES.unreachable:
                return { statusClass: "warning", text: "Validation unreachable" };
            default:
                return { statusClass: "missing", text: "Not configured" };
        }
    }

    function mapTokenMetadataToUi(tokenMetadata) {
        var metadata = tokenMetadata || {};
        var configured = Boolean(metadata.configured);
        if (!configured) {
            return { statusClass: "missing", text: "Not configured" };
        }
        return mapTokenValidationToUi(metadata.validation_status, true);
    }

    globalScope.TokenLifecycle = {
        normalizeTokenValidationStatus: normalizeTokenValidationStatus,
        mapTokenValidationToUi: mapTokenValidationToUi,
        mapTokenMetadataToUi: mapTokenMetadataToUi
    };
})(typeof window !== "undefined" ? window : globalThis);
