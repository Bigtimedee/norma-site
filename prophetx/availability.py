"""
Server-driven availability gate for the ProphetX integration.

Why this exists, concretely. ProphetX received CFTC approval as a DCM and DCO
on 11 June 2026 and launched nationwide on 18 June 2026, but whether federal
registration displaces state gambling law is unresolved litigation: the Third
Circuit ruled for preemption on 6 April 2026 while state regulators prevailed
at the preliminary-injunction stage in Nevada, Maryland and Ohio, and on
28 July 2026 a coalition of 44 states asserted the CFTC lacks authority
entirely. That position has moved repeatedly inside four months.

The engineering consequence: whether NORMA surfaces ProphetX, and where, must
be changeable without shipping an app release. So it is remote configuration,
not a build-time constant.

Two deliberate design choices:

  * Fail closed. If configuration cannot be loaded and nothing valid is cached,
    ProphetX is treated as unavailable. The cost of wrongly hiding a market is
    a missing feature; the cost of wrongly showing one is a compliance problem.

  * No jurisdiction list is hard-coded here. NORMA has not been told which
    states ProphetX serves, and inventing that list would be worse than having
    none. `allowed_regions` stays empty until ProphetX supplies it, and an
    empty list combined with `region_gating` means "unknown -> deny".
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

log = logging.getLogger("prophetx.availability")

DEFAULT_TTL_SECONDS = 300


@dataclass(frozen=True)
class Availability:
    """
    Resolved availability state.

    `enabled` is the master switch. `region_gating` says whether
    `allowed_regions` should be enforced at all — separated so that ProphetX
    can be switched on nationally without an exhaustive region list, and
    switched to per-region enforcement the moment that list is known.
    """
    enabled: bool = False
    region_gating: bool = True
    allowed_regions: frozenset[str] = frozenset()
    source: str = "default"
    fetched_at: float = 0.0
    note: str = ""

    def is_available(self, region: Optional[str] = None) -> bool:
        if not self.enabled:
            return False
        if not self.region_gating:
            return True
        if not region:
            # Region gating is on but we do not know the user's region: deny.
            return False
        return region.strip().upper() in self.allowed_regions

    @classmethod
    def parse(cls, d: dict, source: str) -> "Availability":
        regions = d.get("allowed_regions") or []
        return cls(
            enabled=bool(d.get("enabled", False)),
            region_gating=bool(d.get("region_gating", True)),
            allowed_regions=frozenset(
                str(r).strip().upper() for r in regions if str(r).strip()
            ),
            source=source,
            fetched_at=time.time(),
            note=str(d.get("note", "")),
        )


# Fail-closed default used when nothing else is available.
DISABLED = Availability(
    enabled=False,
    note="Default state. No configuration loaded; ProphetX is not surfaced.",
)


class AvailabilityGate:
    """
    Caches remote availability config with a TTL, falling back safely.

    Resolution order:
      1. Fresh cached value (within TTL)
      2. Remote config fetch
      3. Stale cached value, if any (better than losing a working config)
      4. DISABLED
    """

    def __init__(
        self,
        config_url: Optional[str] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        timeout: float = 5.0,
        client: Optional[httpx.Client] = None,
    ):
        self.config_url = config_url or os.environ.get("PROPHETX_CONFIG_URL", "")
        self.ttl_seconds = ttl_seconds
        self.timeout = timeout
        self._client = client
        self._cached: Optional[Availability] = None
        self._lock = threading.Lock()

    def get(self, force_refresh: bool = False) -> Availability:
        with self._lock:
            cached = self._cached
            if not force_refresh and cached and self._is_fresh(cached):
                return cached

            if not self.config_url:
                if cached:
                    return cached
                log.info("PROPHETX_CONFIG_URL unset — ProphetX stays disabled")
                return DISABLED

            fetched = self._fetch()
            if fetched is not None:
                self._cached = fetched
                return fetched

            if cached:
                log.warning("ProphetX config refresh failed — serving stale config from %.0fs ago",
                            time.time() - cached.fetched_at)
                return cached

            log.warning("ProphetX config unavailable and nothing cached — failing closed")
            return DISABLED

    def is_available(self, region: Optional[str] = None) -> bool:
        return self.get().is_available(region)

    def _is_fresh(self, a: Availability) -> bool:
        return (time.time() - a.fetched_at) < self.ttl_seconds

    def _fetch(self) -> Optional[Availability]:
        try:
            client = self._client or httpx
            resp = client.get(self.config_url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("ProphetX config fetch failed: %s", type(exc).__name__)
            return None

        if not isinstance(data, dict):
            log.warning("ProphetX config was %s, expected object", type(data).__name__)
            return None
        return Availability.parse(data, source=self.config_url)


def load_local(path: str) -> Availability:
    """Load availability config from a file. Used in tests and for local runs."""
    try:
        with open(path, encoding="utf-8") as fh:
            return Availability.parse(json.load(fh), source=path)
    except Exception as exc:
        log.warning("Could not load ProphetX config from %s: %s", path, type(exc).__name__)
        return DISABLED
