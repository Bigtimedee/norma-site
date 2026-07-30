"""
ProphetX read-only market data integration for NORMA.

Portable by design: this package depends only on `httpx` and the standard
library, and imports nothing from NORMA. It is written to be lifted wholesale
into NORMA's application repository, which was not reachable from the session
that produced it. See docs/prophetx/INTEGRATION-NOTES.md.

Scope is Path A of the integration plan — read-only market data. It cannot
place orders; see client.py for how that boundary is enforced.
"""

from .availability import DISABLED, Availability, AvailabilityGate, load_local
from .client import MARKET_TYPES, SANDBOX_BASE_URL, ProphetXClient, client_from_env
from .errors import (
    ProphetXAuthError,
    ProphetXDisabled,
    ProphetXError,
    ProphetXRateLimited,
    ProphetXUnavailable,
)
from .models import (
    DOCUMENTED_TOURNAMENTS,
    Competitor,
    Market,
    MarketsResponse,
    Selection,
    SportEvent,
    Tournament,
)

__all__ = [
    "Availability", "AvailabilityGate", "DISABLED", "load_local",
    "ProphetXClient", "client_from_env", "SANDBOX_BASE_URL", "MARKET_TYPES",
    "ProphetXError", "ProphetXAuthError", "ProphetXUnavailable",
    "ProphetXRateLimited", "ProphetXDisabled",
    "Tournament", "SportEvent", "Competitor", "Market", "Selection",
    "MarketsResponse", "DOCUMENTED_TOURNAMENTS",
]
