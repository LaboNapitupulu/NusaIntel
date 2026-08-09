class BPSError(Exception):
    """Base error that is safe to log without request credentials."""

    category = "bps_error"


class BPSConfigurationError(BPSError):
    category = "configuration"


class BPSAuthenticationError(BPSError):
    category = "authentication"


class BPSRateLimitError(BPSError):
    category = "rate_limit"


class BPSTransientError(BPSError):
    category = "transient"


class BPSResponseError(BPSError):
    category = "response"


class BPSDataUnavailableError(BPSError):
    category = "data_unavailable"


class BPSPayloadError(BPSError):
    category = "payload"
