"""Error detection helpers for the agent loop."""

from config import EXECUTION_ERROR_INDICATORS, TIMEOUT_INDICATOR, FALLBACK_TRIGGERS


def has_execution_error(result_str: str) -> bool:
    """Detect if a tool result contains an execution error worth auto-fixing.

    Timeouts are NOT considered fixable errors.
    """
    if TIMEOUT_INDICATOR in result_str.lower():
        return False

    return any(indicator in result_str for indicator in EXECUTION_ERROR_INDICATORS)


def should_fallback(error_str: str) -> bool:
    """Check if an API error should trigger model fallback."""
    error_lower = error_str.lower()
    return any(trigger in error_lower for trigger in FALLBACK_TRIGGERS)
