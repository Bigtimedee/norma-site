"""
Read-only client for the ProphetX External Affiliate API (Market Data).

Scope is deliberately narrow and structurally enforced:

  * Only HTTP GET is possible. `_get` is the single transport method and it
    calls httpx.get directly. There is no code path that can POST, PUT, PATCH
    or DELETE, so this client cannot place an order even if a future caller
    asks it to.
  * Only /affiliate/* and /v4/affiliate/* paths are reachable; the request
    method rejects anything else before a connection is opened.

That boundary exists because NORMA's published Terms of Service state NORMA
"does not facilitate, process, or broker any wagers or bets" and "is not a
sportsbook, betting exchange, or gambling operator". Trading endpoints are out
of scope by contract, not by preference, so the restriction belongs in code.

Verified facts this implementation is built on (docs.prophetx.co, 30 Jul 2026):
  * Sandbox server: https://api-ss-sandbox.betprophet.co/partner
  * Auth: OpenAPI securityScheme "Token" = apiKey in the `Authorization` header
  * GET /affiliate/get_tournaments   ? has_active_events (bool)
  * GET /affiliate/get_sport_events  ? tournament_id (int), event_ids (int[])
  * GET /v4/affiliate/get_markets    ? event_id (int, required),
                                       market_types (csv), get_all_market (bool)

Unverified and therefore configurable rather than assumed:
  * The production base URL is not published. PROPHETX_BASE_URL must be set
    explicitly to go live; the default is the documented sandbox.
  * No rate limits are published, so the default pacing is conservative and
    adjustable. See docs/prophetx/OPEN-QUESTIONS.md.
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Iterable, Optional

import httpx

from .errors import (
    ProphetXAuthError,
    ProphetXError,
    ProphetXRateLimited,
    ProphetXUnavailable,
)
from .models import MarketsResponse, SportEvent, Tournament

log = logging.getLogger("prophetx")

# Documented sandbox server. Production URL is not published; see module docstring.
SANDBOX_BASE_URL = "https://api-ss-sandbox.betprophet.co/partner"

_ALLOWED_PREFIXES = ("/affiliate/", "/v4/affiliate/")

# Market types accepted by /v4/affiliate/get_markets, per its OpenAPI enum.
MARKET_TYPES = ("moneyline", "spread", "total")


class ProphetXClient:
    """
    Read-only ProphetX market data.

    The client never logs the API key and never returns it. Callers pass the
    key once at construction; it lives only in the session headers.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = SANDBOX_BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 3,
        min_interval: float = 0.25,
        client: Optional[httpx.Client] = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("ProphetX API key is required")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_interval = min_interval
        self._last_request_at = 0.0
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {
            "Authorization": api_key.strip(),
            "Accept": "application/json",
        }

    # ── public API ──────────────────────────────────────────────────────────
    def get_tournaments(self, has_active_events: Optional[bool] = None) -> list[Tournament]:
        params: dict[str, Any] = {}
        if has_active_events is not None:
            params["has_active_events"] = _bool(has_active_events)
        data = self._get("/affiliate/get_tournaments", params)
        return [Tournament.parse(t) for t in (data.get("tournaments") or []) if isinstance(t, dict)]

    def get_sport_events(
        self,
        tournament_id: Optional[int] = None,
        event_ids: Optional[Iterable[int]] = None,
    ) -> list[SportEvent]:
        params: dict[str, Any] = {}
        if tournament_id is not None:
            params["tournament_id"] = int(tournament_id)
        if event_ids:
            # OpenAPI: style=form, explode=false -> comma-separated single param
            params["event_ids"] = ",".join(str(int(e)) for e in event_ids)
        data = self._get("/affiliate/get_sport_events", params)
        return [SportEvent.parse(e) for e in (data.get("sport_events") or []) if isinstance(e, dict)]

    def get_markets(
        self,
        event_id: int,
        market_types: Optional[Iterable[str]] = None,
        get_all_market: Optional[bool] = None,
    ) -> MarketsResponse:
        """`event_id` is required by the endpoint's OpenAPI definition."""
        params: dict[str, Any] = {"event_id": int(event_id)}
        if market_types:
            requested = [m.strip().lower() for m in market_types]
            unknown = [m for m in requested if m not in MARKET_TYPES]
            if unknown:
                raise ValueError(
                    f"Unknown market_types {unknown}; documented values are {list(MARKET_TYPES)}"
                )
            params["market_types"] = ",".join(requested)
        if get_all_market is not None:
            params["get_all_market"] = _bool(get_all_market)
        return MarketsResponse.parse(self._get("/v4/affiliate/get_markets", params))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "ProphetXClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── transport ───────────────────────────────────────────────────────────
    def _get(self, path: str, params: dict) -> dict:
        """
        The only transport method in this client, and it is GET-only.

        Retries idempotent failures with exponential backoff and jitter. GET is
        safe to retry by definition, which is another reason the read-only
        scope is worth keeping.
        """
        if not path.startswith(_ALLOWED_PREFIXES):
            raise ValueError(
                f"Refusing to request {path!r}: this client is restricted to "
                f"{_ALLOWED_PREFIXES} (read-only market data)"
            )

        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None

        for attempt in range(self.max_retries):
            self._pace()
            try:
                resp = self._client.get(
                    url, params=params, headers=self._headers, timeout=self.timeout
                )
            except httpx.RequestError as exc:
                last_exc = exc
                log.warning("ProphetX %s network error (attempt %d/%d): %s",
                            path, attempt + 1, self.max_retries, type(exc).__name__)
                self._backoff(attempt)
                continue

            if resp.status_code in (401, 403):
                # Never retry auth failures; the key will not become valid.
                raise ProphetXAuthError(
                    f"ProphetX rejected the API key on {path} (HTTP {resp.status_code})"
                )
            if resp.status_code == 429:
                retry_after = _retry_after(resp)
                log.warning("ProphetX rate limited on %s; retry-after=%ss", path, retry_after)
                if attempt == self.max_retries - 1:
                    raise ProphetXRateLimited(f"Rate limited on {path}")
                time.sleep(retry_after if retry_after is not None else _delay(attempt))
                continue
            if resp.status_code >= 500:
                last_exc = ProphetXUnavailable(f"HTTP {resp.status_code} from {path}")
                log.warning("ProphetX %s server error %d (attempt %d/%d)",
                            path, resp.status_code, attempt + 1, self.max_retries)
                self._backoff(attempt)
                continue
            if resp.status_code >= 400:
                raise ProphetXError(f"HTTP {resp.status_code} from {path}: {resp.text[:200]}")

            try:
                data = resp.json()
            except ValueError as exc:
                raise ProphetXError(f"Non-JSON response from {path}") from exc

            if not isinstance(data, dict):
                raise ProphetXError(f"Expected a JSON object from {path}, got {type(data).__name__}")
            return data

        raise ProphetXUnavailable(
            f"ProphetX unreachable for {path} after {self.max_retries} attempts"
        ) from last_exc

    def _pace(self) -> None:
        """No published rate limit, so hold a conservative floor between calls."""
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _backoff(self, attempt: int) -> None:
        if attempt < self.max_retries - 1:
            time.sleep(_delay(attempt))


def _delay(attempt: int) -> float:
    return min(2.0 ** attempt, 8.0) + random.uniform(0, 0.25)


def _bool(v: bool) -> str:
    return "true" if v else "false"


def _retry_after(resp: httpx.Response) -> Optional[float]:
    raw = resp.headers.get("Retry-After")
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


def client_from_env(**overrides) -> ProphetXClient:
    """
    Build a client from environment configuration.

      PROPHETX_API_KEY   required
      PROPHETX_BASE_URL  optional; defaults to the documented sandbox

    Production must be opted into explicitly by setting PROPHETX_BASE_URL,
    because ProphetX does not publish the production host and silently
    defaulting to sandbox data in production would be worse than failing.
    """
    key = os.environ.get("PROPHETX_API_KEY", "")
    if not key:
        raise ProphetXAuthError(
            "PROPHETX_API_KEY is not set. Request Market Data API access first "
            "(see docs/prophetx/API-ACCESS-REQUEST.md)."
        )
    base = os.environ.get("PROPHETX_BASE_URL", SANDBOX_BASE_URL)
    if base == SANDBOX_BASE_URL:
        log.info("ProphetX client using documented SANDBOX base URL")
    return ProphetXClient(api_key=key, base_url=base, **overrides)
