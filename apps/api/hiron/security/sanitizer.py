"""Input sanitization and prompt injection detection utilities for security hardening per Phase 16."""

import html
import re

# Common prompt injection patterns (case-insensitive)
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt",
    r"override\s+system\s+prompt",
    r"you\s+are\s+now\s+in\s+dan\s+mode",
    r"jailbreak",
    r"pretend\s+you\s+are\s+unrestricted",
    r"do\s+anything\s+now",
]


def sanitize_text(text: str | None) -> str | None:
    """Sanitize user text inputs by stripping HTML tags and escaping special characters to prevent XSS."""
    if text is None:
        return None

    # Strip HTML tags
    clean = re.sub(r"<[^>]*>", "", text)
    # HTML entity escape remaining characters
    clean = html.escape(clean)
    return clean.strip()


def detect_prompt_injection(text: str | None) -> bool:
    """
    Detect potential adversarial prompt injection vectors in candidate resumes or user prompts.

    NOTE: This is a secondary telemetry signal, not an automatic content blocker.
    Legitimate resume/job content containing prompt-related terminology must remain processable
    unless a separately defined high-confidence blocking policy exists.
    """
    if not text:
        return False

    text_lower = text.lower()
    return any(re.search(pattern, text_lower) is not None for pattern in PROMPT_INJECTION_PATTERNS)
