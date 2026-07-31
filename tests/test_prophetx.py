"""
Tests for the ProphetX read-only integration.

No network and no credentials required: every HTTP interaction is served by an
httpx MockTransport. Fixtures use the exact field names from ProphetX's
published OpenAPI definitions; the values are synthetic and are only ever used
to prove the parser maps fields correctly.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx
import pytest

from prophetx import (
    Availability,
    AvailabilityGate,
    MarketsResponse,
    ProphetXAuthError,
    ProphetXClient,
    ProphetXRateLimited,
    ProphetXUnavailable,
    SANDBOX_BASE_URL,
)
from prophetx.availability import DISABLED

API_KEY = "test-key-not-a-real-credential"


# ── fixtures shaped from the published OpenAPI schemas ──────────────────────
TOURNAMENTS = {
    "tournaments": [
        {"id": 31, "name": "NFL", "banner": "b.png", "image": "i.png",
         "updated_at": 1753800000,
         "sport": {"id": 1, "name": "Football"},
         "category": {"id": 7, "name": "USA"}},
        {"id": 132, "name": "NBA"},
    ]
}

SPORT_EVENTS = {
    "sport_events": [{
        "event_id": 9001, "name": "Team A at Team B", "display_name": "A @ B",
        "scheduled": "2026-09-10T00:20:00Z", "status": "not_started",
        "type": "game", "sub_type": "regular", "sport_name": "Football",
        "tournament_id": 31, "tournament_name": "NFL",
        "live_disabled": False, "updated_at": 1753800001,
        "competitors": [
            {"id": 501, "name": "Team A", "display_name": "A",
             "abbreviation": "AAA", "country": "USA", "side": "away"},
            {"id": 502, "name": "Team B", "display_name": "B",
             "abbreviation": "BBB", "country": "USA", "side": "home"},
        ],
    }]
}

# selections is array-of-arrays (liquidity levels), per the v3 changelog.
MARKETS = {
    "event_id": 9001,
    "markets": [{
        "id": 77, "name": "Moneyline", "display_name": "Moneyline",
        "type": "moneyline", "sub_type": "regular", "category_name": "Game Lines",
        "group_name": "Main", "line": 0, "player_id": 0, "favourite": True,
        "selections": [
            [
                {"name": "Team A", "display_name": "A", "price": -110.0,
                 "display_price": "-110", "strike": 0.0, "display_strike": "",
                 "strike_id": "abc123", "adjusted_price": -108.0,
                 "competitor_id": 501, "outcome_id": 1, "quantity": 250.0,
                 "value": 1.0, "updated_at": 1753800002},
                {"name": "Team B", "display_name": "B", "price": 105.0,
                 "display_price": "+105", "strike_id": "def456",
                 "competitor_id": 502, "outcome_id": 2},
            ],
            [
                {"name": "Team A", "display_price": "-115", "price": -115.0,
                 "strike_id": "abc124", "quantity": 900.0},
            ],
        ],
    }],
}


def make_client(handler, **kw) -> ProphetXClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    kw.setdefault("min_interval", 0)   # no pacing sleeps in tests
    return ProphetXClient(api_key=API_KEY, client=http, **kw)


# ── the read-only boundary ──────────────────────────────────────────────────
def test_client_source_contains_no_mutating_http_verbs():
    """
    Structural guarantee: the client cannot place an order because it contains
    no mutating request call at all. This test is the enforcement mechanism for
    NORMA Terms of Service section 3.
    """
    src = Path(__file__).resolve().parent.parent / "prophetx" / "client.py"
    text = src.read_text(encoding="utf-8")
    forbidden = re.findall(r"\.(post|put|patch|delete)\s*\(", text, re.I)
    assert forbidden == [], f"Mutating HTTP call found in read-only client: {forbidden}"


def test_client_refuses_paths_outside_affiliate_namespace():
    def handler(request):  # pragma: no cover - must never be reached
        raise AssertionError(f"request escaped the guard: {request.url}")

    c = make_client(handler)
    for bad in ("/mm-get-balance-2", "/v4/mm-get-order-history", "/partner/other"):
        with pytest.raises(ValueError, match="read-only market data"):
            c._get(bad, {})


def test_only_get_requests_are_issued():
    seen = []

    def handler(request):
        seen.append(request.method)
        return httpx.Response(200, json=TOURNAMENTS)

    c = make_client(handler)
    c.get_tournaments()
    c.get_sport_events(tournament_id=31)
    assert set(seen) == {"GET"}


# ── request construction ────────────────────────────────────────────────────
def test_auth_header_and_base_url():
    captured = {}

    def handler(request):
        captured["auth"] = request.headers.get("Authorization")
        captured["url"] = str(request.url)
        return httpx.Response(200, json=TOURNAMENTS)

    make_client(handler).get_tournaments(has_active_events=True)
    assert captured["auth"] == API_KEY          # apiKey in Authorization header
    assert captured["url"].startswith(SANDBOX_BASE_URL + "/affiliate/get_tournaments")
    assert "has_active_events=true" in captured["url"]


def test_event_ids_are_comma_separated_single_param():
    """OpenAPI declares style=form, explode=false for event_ids."""
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json=SPORT_EVENTS)

    make_client(handler).get_sport_events(event_ids=[1, 2, 3])
    assert "event_ids=1%2C2%2C3" in captured["url"] or "event_ids=1,2,3" in captured["url"]


def test_get_markets_requires_event_id_and_validates_market_types():
    def handler(request):
        return httpx.Response(200, json=MARKETS)

    c = make_client(handler)
    with pytest.raises(ValueError, match="Unknown market_types"):
        c.get_markets(9001, market_types=["moneyline", "parlay"])

    captured = {}

    def handler2(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json=MARKETS)

    make_client(handler2).get_markets(9001, market_types=["moneyline", "total"])
    assert "event_id=9001" in captured["url"]
    assert "moneyline" in captured["url"] and "total" in captured["url"]


# ── parsing ─────────────────────────────────────────────────────────────────
def test_tournaments_parse():
    c = make_client(lambda r: httpx.Response(200, json=TOURNAMENTS))
    ts = c.get_tournaments()
    assert [t.id for t in ts] == [31, 132]
    assert ts[0].name == "NFL"
    assert ts[0].sport.name == "Football"
    assert ts[0].category.name == "USA"
    assert ts[1].sport.name is None      # absent nested object must not raise


def test_sport_events_parse():
    c = make_client(lambda r: httpx.Response(200, json=SPORT_EVENTS))
    e = c.get_sport_events(tournament_id=31)[0]
    assert e.event_id == 9001
    assert e.tournament_name == "NFL"
    assert [x.side for x in e.competitors] == ["away", "home"]
    assert e.live_disabled is False


def test_markets_preserve_liquidity_levels():
    """
    selections is array-of-arrays. Flattening would merge price levels and
    misstate the book, so the nesting must survive parsing.
    """
    c = make_client(lambda r: httpx.Response(200, json=MARKETS))
    resp = c.get_markets(9001)
    assert resp.event_id == 9001
    m = resp.markets[0]
    assert len(m.selections) == 2                    # two liquidity levels
    assert len(m.best_selections) == 2               # two outcomes at top level
    assert m.best_selections[0].display_price == "-110"
    assert m.best_selections[0].strike_id == "abc123"
    assert m.selections[1][0].display_price == "-115"


def test_partial_selection_fields_do_not_raise():
    c = make_client(lambda r: httpx.Response(200, json=MARKETS))
    second = c.get_markets(9001).markets[0].best_selections[1]
    assert second.display_price == "+105"
    assert second.quantity is None                   # field absent -> None


def test_unknown_future_fields_are_ignored():
    payload = {"tournaments": [{"id": 1, "name": "X", "brand_new_field": "surprise"}]}
    c = make_client(lambda r: httpx.Response(200, json=payload))
    assert c.get_tournaments()[0].name == "X"


def test_empty_payload_yields_empty_list():
    c = make_client(lambda r: httpx.Response(200, json={}))
    assert c.get_tournaments() == []


# ── failure handling ────────────────────────────────────────────────────────
def test_auth_failure_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    with pytest.raises(ProphetXAuthError):
        make_client(handler).get_tournaments()
    assert len(calls) == 1, "auth errors must not be retried"


def test_documented_error_body_shape_is_handled():
    """
    Observed live from the sandbox on 30 Jul 2026: an unauthenticated GET to
    /partner/affiliate/get_tournaments returns HTTP 401 with
    {"error": "unauthorized", "message": "token expired"}, matching the
    response.ErrorResponse schema. Both 401 variants must surface as auth
    errors rather than being retried.
    """
    for body in ({"error": "unauthorized", "message": "token expired"},
                 {"error": "unauthorized", "message": "Unauthorized"}):
        calls = []

        def handler(request, _b=body):
            calls.append(1)
            return httpx.Response(401, json=_b)

        with pytest.raises(ProphetXAuthError):
            make_client(handler).get_tournaments()
        assert len(calls) == 1


def test_server_errors_are_retried_then_raise():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(ProphetXUnavailable):
        make_client(handler, max_retries=3).get_tournaments()
    assert len(calls) == 3


def test_retry_succeeds_after_transient_failure():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=TOURNAMENTS)

    assert len(make_client(handler).get_tournaments()) == 2


def test_rate_limit_raises_after_retries():
    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "0"})

    with pytest.raises(ProphetXRateLimited):
        make_client(handler, max_retries=2).get_tournaments()


def test_api_key_is_never_logged(caplog):
    def handler(request):
        return httpx.Response(500)

    caplog.set_level(logging.DEBUG)
    with pytest.raises(ProphetXUnavailable):
        make_client(handler, max_retries=2).get_tournaments()
    assert API_KEY not in caplog.text


def test_empty_api_key_rejected():
    with pytest.raises(ValueError):
        ProphetXClient(api_key="   ")


# ── availability gate ───────────────────────────────────────────────────────
def test_gate_fails_closed_with_no_config():
    assert AvailabilityGate(config_url="").get() is DISABLED
    assert AvailabilityGate(config_url="").is_available("NJ") is False


def test_gate_fails_closed_when_fetch_fails():
    def handler(request):
        return httpx.Response(500)

    gate = AvailabilityGate(config_url="https://cfg.example/p.json",
                            client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert gate.is_available("NJ") is False


def test_gate_enables_with_region_gating():
    cfg = {"enabled": True, "region_gating": True, "allowed_regions": ["nj", "WY"]}
    gate = AvailabilityGate(
        config_url="https://cfg.example/p.json",
        client=httpx.Client(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=cfg))))
    assert gate.is_available("NJ") is True
    assert gate.is_available("wy") is True
    assert gate.is_available("NV") is False
    assert gate.is_available(None) is False      # unknown region -> deny


def test_gate_national_mode_skips_region_check():
    cfg = {"enabled": True, "region_gating": False}
    gate = AvailabilityGate(
        config_url="https://cfg.example/p.json",
        client=httpx.Client(transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json=cfg))))
    assert gate.is_available(None) is True


def test_gate_serves_stale_config_when_refresh_fails():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(200, json={"enabled": True, "region_gating": False})
        return httpx.Response(500)

    gate = AvailabilityGate(config_url="https://cfg.example/p.json", ttl_seconds=0,
                            client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert gate.get().enabled is True
    assert gate.get(force_refresh=True).enabled is True   # stale beats losing config


def test_disabled_config_hides_prophetx_even_with_regions():
    cfg = {"enabled": False, "region_gating": False, "allowed_regions": ["NJ"]}
    assert Availability.parse(cfg, "test").is_available("NJ") is False
