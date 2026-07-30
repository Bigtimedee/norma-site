"""Exception hierarchy for the ProphetX client.

Callers generally want to distinguish three cases: the key is wrong (fix
config), ProphetX is having a moment (retry later, degrade gracefully), or the
request was malformed (fix code). Everything derives from ProphetXError so a
single except clause can wrap the integration if that is all a caller needs.
"""

from __future__ import annotations


class ProphetXError(Exception):
    """Base class for every ProphetX integration failure."""


class ProphetXAuthError(ProphetXError):
    """API key missing, rejected, or lacking access to the requested resource."""


class ProphetXUnavailable(ProphetXError):
    """Network failure or 5xx after retries. Transient; degrade and retry later."""


class ProphetXRateLimited(ProphetXError):
    """HTTP 429. No published limits, so treat as a signal to slow down."""


class ProphetXDisabled(ProphetXError):
    """
    Raised when the availability gate is off.

    Distinct from a failure: this is the kill switch working as designed, and
    callers should treat it as "do not show ProphetX", not as an error to alert on.
    """
