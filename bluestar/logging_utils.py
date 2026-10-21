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
        message = record.getMessage()
        redacted = message
        for secret in _SECRETS:
            redacted = redacted.replace(secret, "[REDACTED]")
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_filter() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    if not any(isinstance(f, RedactingFilter) for f in logger.filters):
        logger.addFilter(RedactingFilter())


install_filter()
