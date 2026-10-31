"""Redact registered secrets from every log record on the app logger."""

from __future__ import annotations

import logging

LOGGER_NAME = "bluestar_sniper"
_SECRETS: set[str] = set()


def register_secret(value: str | None) -> None:
    if value and len(value) >= 8:
        _SECRETS.add(value)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not _SECRETS:
            return True
        # Redact in the rendered message.
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001
            message = str(record.msg)
        redacted = message
        for secret in _SECRETS:
            redacted = redacted.replace(secret, "[REDACTED]")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        # Redact in exception text / traceback.
        if record.exc_text:
            exc_text = record.exc_text
            for secret in _SECRETS:
                exc_text = exc_text.replace(secret, "[REDACTED]")
            record.exc_text = exc_text
        if record.stack_info:
            stack = record.stack_info
            for secret in _SECRETS:
                stack = stack.replace(secret, "[REDACTED]")
            record.stack_info = stack
        return True


def install_filter() -> None:
    # Apply to the app logger AND the root logger so third-party loggers
    # (urllib3, requests, streamlit) are also covered.
    for name in (LOGGER_NAME, None):
        logger = logging.getLogger(name) if name else logging.getLogger()
        if not any(isinstance(f, RedactingFilter) for f in logger.filters):
            logger.addFilter(RedactingFilter())


install_filter()
