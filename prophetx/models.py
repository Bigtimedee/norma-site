"""
Typed models for the ProphetX External Affiliate API.

Every field here is transcribed from ProphetX's published OpenAPI definitions,
retrieved 30 July 2026 from docs.prophetx.co/reference/*.md:

  contract.Tournament          -> Tournament
  contract.Sport / Category    -> Sport / Category
  contract.SportEvent          -> SportEvent
  contract.Competitor          -> Competitor
  v4.AffiliateMarketV4         -> Market
  v4.Selection                 -> Selection

No field is invented. Parsing is deliberately tolerant: ProphetX may add fields
(their own changelog shows v2 and v3 both added fields to existing responses),
and an unknown field must never crash a NORMA release. Fields absent from a
payload become None rather than raising, because a partial market is still
displayable and a hard failure here would take out a user's whole markets list.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _int(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _str(v: Any) -> Optional[str]:
    return v if isinstance(v, str) else (str(v) if v is not None else None)


@dataclass(frozen=True)
class Sport:
    id: Optional[int] = None
    name: Optional[str] = None

    @classmethod
    def parse(cls, d: Any) -> "Sport":
        d = d or {}
        return cls(id=_int(d.get("id")), name=_str(d.get("name")))


@dataclass(frozen=True)
class Category:
    id: Optional[int] = None
    name: Optional[str] = None

    @classmethod
    def parse(cls, d: Any) -> "Category":
        d = d or {}
        return cls(id=_int(d.get("id")), name=_str(d.get("name")))


@dataclass(frozen=True)
class Tournament:
    """OpenAPI: contract.Tournament"""
    id: Optional[int] = None
    name: Optional[str] = None
    sport: Sport = field(default_factory=Sport)
    category: Category = field(default_factory=Category)
    banner: Optional[str] = None
    image: Optional[str] = None
    updated_at: Optional[int] = None

    @classmethod
    def parse(cls, d: dict) -> "Tournament":
        return cls(
            id=_int(d.get("id")),
            name=_str(d.get("name")),
            sport=Sport.parse(d.get("sport")),
            category=Category.parse(d.get("category")),
            banner=_str(d.get("banner")),
            image=_str(d.get("image")),
            updated_at=_int(d.get("updated_at")),
        )


@dataclass(frozen=True)
class Competitor:
    """OpenAPI: contract.Competitor"""
    id: Optional[int] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    abbreviation: Optional[str] = None
    country: Optional[str] = None
    side: Optional[str] = None

    @classmethod
    def parse(cls, d: dict) -> "Competitor":
        return cls(
            id=_int(d.get("id")),
            name=_str(d.get("name")),
            display_name=_str(d.get("display_name")),
            abbreviation=_str(d.get("abbreviation")),
            country=_str(d.get("country")),
            side=_str(d.get("side")),
        )


@dataclass(frozen=True)
class SportEvent:
    """OpenAPI: contract.SportEvent"""
    event_id: Optional[int] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    scheduled: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    sub_type: Optional[str] = None
    sport_name: Optional[str] = None
    tournament_id: Optional[int] = None
    tournament_name: Optional[str] = None
    live_disabled: Optional[bool] = None
    updated_at: Optional[int] = None
    competitors: tuple[Competitor, ...] = ()

    @classmethod
    def parse(cls, d: dict) -> "SportEvent":
        comps = d.get("competitors") or []
        return cls(
            event_id=_int(d.get("event_id")),
            name=_str(d.get("name")),
            display_name=_str(d.get("display_name")),
            scheduled=_str(d.get("scheduled")),
            status=_str(d.get("status")),
            type=_str(d.get("type")),
            sub_type=_str(d.get("sub_type")),
            sport_name=_str(d.get("sport_name")),
            tournament_id=_int(d.get("tournament_id")),
            tournament_name=_str(d.get("tournament_name")),
            live_disabled=d.get("live_disabled") if isinstance(d.get("live_disabled"), bool) else None,
            updated_at=_int(d.get("updated_at")),
            competitors=tuple(Competitor.parse(c) for c in comps if isinstance(c, dict)),
        )


@dataclass(frozen=True)
class Selection:
    """
    OpenAPI: v4.Selection

    `price` is ProphetX's numeric price and `display_price` its rendered form.
    NORMA must display `display_price` rather than formatting `price` itself,
    so that what a user sees in NORMA matches what they see on ProphetX.
    """
    name: Optional[str] = None
    display_name: Optional[str] = None
    price: Optional[float] = None
    display_price: Optional[str] = None
    strike: Optional[float] = None
    display_strike: Optional[str] = None
    strike_id: Optional[str] = None
    adjusted_price: Optional[float] = None
    competitor_id: Optional[int] = None
    outcome_id: Optional[int] = None
    quantity: Optional[float] = None
    value: Optional[float] = None
    updated_at: Optional[int] = None

    @classmethod
    def parse(cls, d: dict) -> "Selection":
        return cls(
            name=_str(d.get("name")),
            display_name=_str(d.get("display_name")),
            price=_float(d.get("price")),
            display_price=_str(d.get("display_price")),
            strike=_float(d.get("strike")),
            display_strike=_str(d.get("display_strike")),
            strike_id=_str(d.get("strike_id")),
            adjusted_price=_float(d.get("adjusted_price")),
            competitor_id=_int(d.get("competitor_id")),
            outcome_id=_int(d.get("outcome_id")),
            quantity=_float(d.get("quantity")),
            value=_float(d.get("value")),
            updated_at=_int(d.get("updated_at")),
        )


@dataclass(frozen=True)
class Market:
    """
    OpenAPI: v4.AffiliateMarketV4

    `selections` is an array of arrays. ProphetX's own v3 changelog states the
    change was "selections: support multiple levels of liquidity", so the outer
    list is liquidity depth, not a flat list of outcomes. It is preserved as
    nested here; flattening it would silently merge price levels and misstate
    the book. Use `best_selections` for the top level only.
    """
    id: Optional[int] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[str] = None
    sub_type: Optional[str] = None
    category_name: Optional[str] = None
    group_name: Optional[str] = None
    line: Optional[float] = None
    player_id: Optional[int] = None
    favourite: Optional[bool] = None
    selections: tuple[tuple[Selection, ...], ...] = ()

    @classmethod
    def parse(cls, d: dict) -> "Market":
        raw = d.get("selections") or []
        levels: list[tuple[Selection, ...]] = []
        for level in raw:
            if isinstance(level, list):
                levels.append(tuple(Selection.parse(s) for s in level if isinstance(s, dict)))
            elif isinstance(level, dict):
                # Defensive: older documented versions expose a flat list.
                levels.append((Selection.parse(level),))
        return cls(
            id=_int(d.get("id")),
            name=_str(d.get("name")),
            display_name=_str(d.get("display_name")),
            type=_str(d.get("type")),
            sub_type=_str(d.get("sub_type")),
            category_name=_str(d.get("category_name")),
            group_name=_str(d.get("group_name")),
            line=_float(d.get("line")),
            player_id=_int(d.get("player_id")),
            favourite=d.get("favourite") if isinstance(d.get("favourite"), bool) else None,
            selections=tuple(levels),
        )

    @property
    def best_selections(self) -> tuple[Selection, ...]:
        """Top liquidity level only — the prices a user would see first."""
        return self.selections[0] if self.selections else ()


@dataclass(frozen=True)
class MarketsResponse:
    """OpenAPI: affiliate.ListAffiliateResponseV4"""
    event_id: Optional[int] = None
    markets: tuple[Market, ...] = ()

    @classmethod
    def parse(cls, d: dict) -> "MarketsResponse":
        d = d or {}
        return cls(
            event_id=_int(d.get("event_id")),
            markets=tuple(Market.parse(m) for m in (d.get("markets") or []) if isinstance(m, dict)),
        )


# Tournament IDs published in the get_sport_events documentation (30 Jul 2026).
# Treated as a convenience lookup, not an authority: the same endpoint returns
# the live list, and get_tournaments() should be preferred at runtime.
DOCUMENTED_TOURNAMENTS: dict[str, int] = {
    "MLB": 109,
    "KBO League": 2541,
    "Professional Baseball": 1036,
    "NFL Preseason": 233,
    "NFL": 31,
    "NHL": 234,
    "NBA": 132,
}
