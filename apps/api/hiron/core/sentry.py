"""Sentry configuration and initialization."""

import sentry_sdk

def sentry_before_send(event: dict, hint: dict) -> dict:
    """Strictly strip sensitive PII and AI prompts from Sentry events."""
    if "request" in event:
        request = event["request"]
        if "headers" in request:
            headers = request["headers"]
            if "authorization" in headers:
                headers["authorization"] = "[Filtered]"
            if "cookie" in headers:
                headers["cookie"] = "[Filtered]"

        # Scrub raw request bodies to prevent leaking resumes or candidate notes
        if "data" in request:
            request["data"] = "[Filtered payload]"

    return event

def init_sentry(dsn: str | None, environment: str) -> None:
    """Initialize Sentry SDK with standard configuration."""
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=0.1,  # Conservative sample rate
            send_default_pii=False,
            include_local_variables=False,
            before_send=sentry_before_send,
        )
