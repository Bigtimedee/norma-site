#!/usr/bin/env python3
"""
Live smoke check for the ProphetX Market Data integration.

Run this the moment a key arrives, and after any base-URL change:

    PROPHETX_API_KEY=... python3 -m prophetx.smoke

It walks the full read path — tournaments, then events for one tournament,
then markets for one event — and reports what came back. Read-only, so it is
safe to run against production.

Exit codes:
    0  everything worked
    1  a call failed
    2  not configured (no API key)
"""

from __future__ import annotations

import logging
import os
import sys

from .client import SANDBOX_BASE_URL, client_from_env
from .errors import ProphetXAuthError, ProphetXError


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    try:
        client = client_from_env()
    except ProphetXAuthError as exc:
        print(f"NOT CONFIGURED: {exc}")
        return 2

    base = os.environ.get("PROPHETX_BASE_URL", SANDBOX_BASE_URL)
    env = "SANDBOX" if base == SANDBOX_BASE_URL else "PRODUCTION"
    print(f"\nProphetX smoke check — {env}\n  base: {base}\n")

    try:
        with client:
            tournaments = client.get_tournaments(has_active_events=True)
            print(f"[1/3] get_tournaments -> {len(tournaments)} with active events")
            for t in tournaments[:8]:
                print(f"        {str(t.id):>6}  {t.name}  ({t.sport.name or 'sport n/a'})")
            if not tournaments:
                print("      No active tournaments. Nothing further to check; this is a "
                      "valid state out of season, not a failure.")
                return 0

            target = tournaments[0]
            events = client.get_sport_events(tournament_id=target.id)
            print(f"\n[2/3] get_sport_events(tournament_id={target.id}) -> {len(events)} events")
            for e in events[:5]:
                who = " vs ".join(c.display_name or c.name or "?" for c in e.competitors) or e.name
                print(f"        {str(e.event_id):>8}  {who}  [{e.status}]  {e.scheduled}")
            if not events:
                print("      No events for that tournament. Stopping here.")
                return 0

            ev = events[0]
            resp = client.get_markets(ev.event_id, market_types=["moneyline"])
            print(f"\n[3/3] get_markets(event_id={ev.event_id}, moneyline) "
                  f"-> {len(resp.markets)} markets")
            for m in resp.markets[:3]:
                levels = len(m.selections)
                print(f"        {m.display_name or m.name}  "
                      f"[{m.type}]  liquidity levels: {levels}")
                for s in m.best_selections[:4]:
                    print(f"            {s.display_name or s.name:<24} "
                          f"{s.display_price or s.price}   strike_id={s.strike_id}")

    except ProphetXError as exc:
        print(f"\nFAILED: {type(exc).__name__}: {exc}")
        return 1

    print("\nOK — full read path verified.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
