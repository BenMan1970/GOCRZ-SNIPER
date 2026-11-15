"""Journalisation sûre : les secrets ne sortent jamais dans les logs.

Le masquage est posé à la création de chaque LogRecord (record factory) : il
couvre donc TOUS les loggers (y compris tiers comme urllib3) et le texte des
tracebacks, contrairement à un filtre posé sur un logger.
"""

from __future__ import annotations

import logging
import threading

LOGGER_NAME = "bluestar_sniper"
_MASK = "[REDACTED]"

_lock = threading.Lock()
_secrets: set[str] = set()
_installed = False


def register_secret(value: str | None) -> None:
    if value and len(value) >= 6:
        with _lock:
            _secrets.add(value)
        _install()


def _mask(text: str) -> str:
    with _lock:
        secrets = tuple(_secrets)
    for secret in secrets:
        text = text.replace(secret, _MASK)
    return text


def _install() -> None:
    global _installed
    with _lock:
        if _installed:
            return
        _installed = True
    previous = logging.getLogRecordFactory()

    def factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        if not _secrets:
            return record
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - un log ne doit jamais lever
            message = str(record.msg)
        masked = _mask(message)
        if masked != message:
            record.msg, record.args = masked, ()
        if record.exc_info and not record.exc_text:
            text = logging.Formatter().formatException(record.exc_info)
            record.exc_text = _mask(text)
        return record

    logging.setLogRecordFactory(factory)

