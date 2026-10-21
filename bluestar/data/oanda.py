"""Read-only OANDA v20 candle client.

Only GET /v3/instruments/{instrument}/candles is used. Sessions are reused per
thread; parameters are explicit so we never depend on server defaults.
"""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from collections.abc import Callable
from typing import Protocol

import pandas as pd
import requests

from ..config import API_CANDLE_PARAMS, MAX_RETRIES, OANDA_API_HOSTS, RETRY_DELAY
from ..logging_utils import register_secret

logger = logging.getLogger("bluestar_sniper")

EMPTY_DF = pd.DataFrame(columns=["open", "high", "low", "close"])

TOKEN_INVALID = "TOKEN_INVALID"  # nosec B105
INSTRUMENT_UNAVAILABLE = "INSTRUMENT_UNAVAILABLE"
BAD_REQUEST = "BAD_REQUEST"
RATE_LIMITED = "RATE_LIMITED"
TIMEOUT = "TIMEOUT"
NETWORK_ERROR = "NETWORK_ERROR"
SERVER_ERROR = "SERVER_ERROR"
BAD_RESPONSE = "BAD_RESPONSE"
EMPTY_RESPONSE = "Aucune bougie complète"
MAX_RETRIES_ERROR = "MAX_RETRIES"


class AuthenticationError(RuntimeError):
    """Fatal: the API rejected the token. Never retry per instrument."""


class CandleSource(Protocol):
    def fetch(
        self, instrument: str, granularity: str, count: int
    ) -> tuple[pd.DataFrame, str | None]:
        ...


def redact(text: object, token: str) -> str:
    value = str(text)
    if token:
        value = value.replace(token, "[REDACTED]")
    return value


def classify_400(body: str) -> str:
    try:
        payload = json.loads(body)
    except (TypeError, ValueError):
        return BAD_REQUEST
    if not isinstance(payload, dict):
        return BAD_REQUEST
    code = str(payload.get("errorCode", "")).upper()
    message = str(payload.get("errorMessage", "")).upper()
    if code == "INSTRUMENT_NOT_FOUND" or "INSTRUMENT_NOT_FOUND" in message:
        return INSTRUMENT_UNAVAILABLE
    return BAD_REQUEST


def parse_candles(payload: object) -> pd.DataFrame:
    if not isinstance(payload, dict) or "candles" not in payload:
        raise ValueError("Réponse inattendue")
    rows = [
        {
            "time": pd.to_datetime(c["time"]),
            "open": float(c["mid"]["o"]),
            "high": float(c["mid"]["h"]),
            "low": float(c["mid"]["l"]),
            "close": float(c["mid"]["c"]),
        }
        for c in payload["candles"]
        if c.get("complete")
    ]
    return pd.DataFrame(rows)


class TokenBucket:
    """Thread-safe token bucket used to bound the global request rate."""

    def __init__(self, rate_per_s: float = 25.0, burst: float = 10.0):
        self.rate = rate_per_s
        self.capacity = burst
        self.tokens = burst
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(
                    self.capacity, self.tokens + (now - self.updated) * self.rate
                )
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            time.sleep(wait)


class OandaSource:
    def __init__(
        self,
        access_token: str,
        environment: str = "practice",
        timeout: tuple[float, float] = (5.0, 20.0),
        limiter: TokenBucket | None = None,
        max_retries: int = MAX_RETRIES,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if environment not in OANDA_API_HOSTS:
            raise ValueError("Unknown OANDA environment")
        self._token = access_token
        register_secret(access_token)
        self._host = OANDA_API_HOSTS[environment]
        self._timeout = timeout
        self._limiter = limiter
        self._max_retries = max_retries
        self._sleep = sleep
        self._local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(
                {
                    "Authorization": f"Bearer {self._token}",
                    "Accept-Encoding": "gzip, deflate",
                }
            )
            self._local.session = session
        return session

    def _delay(self, attempt: int, retry_after: str | None = None) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        base = RETRY_DELAY * attempt
        return base + random.uniform(0, base * 0.25)  # nosec B311

    def fetch(
        self, instrument: str, granularity: str, count: int
    ) -> tuple[pd.DataFrame, str | None]:
        params: dict[str, str | int] = {
            "count": count,
            "granularity": granularity,
            **API_CANDLE_PARAMS,
        }
        url = f"{self._host}/v3/instruments/{instrument}/candles"
        last_error = MAX_RETRIES_ERROR

        for attempt in range(1, self._max_retries + 1):
            if self._limiter is not None:
                self._limiter.acquire()
            try:
                response = self._session().get(
                    url, params=params, timeout=self._timeout
                )
            except requests.Timeout as exc:
                last_error = f"{TIMEOUT}: {redact(exc, self._token)[:120]}"
                logger.warning("[%s] %s attempt %s", instrument, TIMEOUT, attempt)
                if attempt < self._max_retries:
                    self._sleep(self._delay(attempt))
                    continue
                return EMPTY_DF.copy(), last_error
            except requests.RequestException as exc:
                last_error = f"{NETWORK_ERROR}: {redact(exc, self._token)[:120]}"
                logger.warning("[%s] %s attempt %s", instrument, NETWORK_ERROR, attempt)
                if attempt < self._max_retries:
                    self._sleep(self._delay(attempt))
                    continue
                return EMPTY_DF.copy(), last_error

            status = response.status_code
            if status in (401, 403):
                raise AuthenticationError(TOKEN_INVALID)
            if status == 400:
                detail = redact(response.text, self._token)[:120]
                return EMPTY_DF.copy(), f"{classify_400(response.text)}: {detail}"
            if status == 429:
                last_error = RATE_LIMITED
                if attempt < self._max_retries:
                    self._sleep(
                        self._delay(attempt, response.headers.get("Retry-After"))
                    )
                    continue
                return EMPTY_DF.copy(), last_error
            if status >= 500:
                last_error = f"{SERVER_ERROR}: HTTP {status}"
                if attempt < self._max_retries:
                    self._sleep(self._delay(attempt))
                    continue
                return EMPTY_DF.copy(), last_error
            if status != 200:
                return EMPTY_DF.copy(), f"HTTP_{status}"

            try:
                payload = response.json()
                df = parse_candles(payload)
            except (ValueError, KeyError, TypeError) as exc:
                last_error = f"{BAD_RESPONSE}: {redact(exc, self._token)[:120]}"
                if attempt < self._max_retries:
                    self._sleep(self._delay(attempt))
                    continue
                return EMPTY_DF.copy(), last_error

            if df.empty:
                return EMPTY_DF.copy(), EMPTY_RESPONSE
            df = df.set_index("time")
            idx = pd.DatetimeIndex(df.index)
            if idx.tz is None:
                idx = idx.tz_localize("UTC")
            df.index = idx
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="last")]
            return df, None

        return EMPTY_DF.copy(), last_error

    def close(self) -> None:
        session = getattr(self._local, "session", None)
        if session is not None:
            session.close()
            self._local.session = None


def fetch_oanda_data(
    access_token: str,
    environment: str,
    instrument: str,
    granularity: str,
    count: int,
) -> tuple[pd.DataFrame, str | None]:
    """Compatibility entry point (one client per call, as in V16)."""
    source = OandaSource(access_token, environment)
    try:
        return source.fetch(instrument, granularity, count)
    finally:
        source.close()
