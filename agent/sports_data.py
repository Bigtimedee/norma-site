from __future__ import annotations

import httpx
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Game:
    id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: datetime
    home_moneyline: Optional[int] = None
    away_moneyline: Optional[int] = None
    spread: Optional[float] = None
    spread_home_odds: Optional[int] = None
    over_under: Optional[float] = None

    @property
    def is_today(self) -> bool:
        today = datetime.now(timezone.utc).date()
        return self.commence_time.date() == today

    @property
    def time_str(self) -> str:
        # Convert UTC to Eastern for display
        from datetime import timedelta
        et = self.commence_time - timedelta(hours=4)  # rough ET offset
        return et.strftime("%-I:%M %p ET")

    @property
    def sport_emoji(self) -> str:
        emojis = {
            "americanfootball_nfl": "🏈",
            "basketball_nba": "🏀",
            "baseball_mlb": "⚾",
            "icehockey_nhl": "🏒",
        }
        return emojis.get(self.sport, "🏆")


# ESPN sport slug mapping for the public ESPN API (no key required)
_ESPN_SPORT_SLUGS = {
    "americanfootball_nfl": ("football", "nfl"),
    "basketball_nba": ("basketball", "nba"),
    "baseball_mlb": ("baseball", "mlb"),
    "icehockey_nhl": ("hockey", "nhl"),
}


def fetch_todays_games(odds_api_key: Optional[str], sports: list[str]) -> list[Game]:
    if odds_api_key:
        return _fetch_from_odds_api(odds_api_key, sports)
    return _fetch_from_espn(sports)


def _fetch_from_odds_api(odds_api_key: str, sports: list[str]) -> list[Game]:
    games: list[Game] = []
    for sport in sports:
        try:
            games.extend(_fetch_sport_odds(odds_api_key, sport))
        except Exception:
            pass
    return [g for g in games if g.is_today]


def _fetch_sport_odds(odds_api_key: str, sport: str) -> list[Game]:
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {
        "apiKey": odds_api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    resp = httpx.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    games = []
    for item in data:
        game = _parse_game(item, sport)
        if game:
            games.append(game)
    return games


def _fetch_from_espn(sports: list[str]) -> list[Game]:
    games: list[Game] = []
    for sport in sports:
        slugs = _ESPN_SPORT_SLUGS.get(sport)
        if not slugs:
            continue
        try:
            games.extend(_fetch_espn_sport(sport, slugs[0], slugs[1]))
        except Exception:
            pass
    return games


def _fetch_espn_sport(sport: str, espn_sport: str, espn_league: str) -> list[Game]:
    url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_sport}/{espn_league}/scoreboard"
    resp = httpx.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    games = []
    for event in data.get("events", []):
        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            home = next(c for c in competitors if c["homeAway"] == "home")
            away = next(c for c in competitors if c["homeAway"] == "away")
            date_str = event["date"]
            commence = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            game = Game(
                id=event["id"],
                sport=sport,
                home_team=home["team"]["displayName"],
                away_team=away["team"]["displayName"],
                commence_time=commence,
            )
            games.append(game)
        except (KeyError, StopIteration, ValueError):
            continue
    return games


def _parse_game(item: dict, sport: str) -> Optional[Game]:
    try:
        commence = datetime.fromisoformat(item["commence_time"].replace("Z", "+00:00"))
        game = Game(
            id=item["id"],
            sport=sport,
            home_team=item["home_team"],
            away_team=item["away_team"],
            commence_time=commence,
        )
        for bookmaker in item.get("bookmakers", [])[:1]:  # use first bookmaker
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == item["home_team"]:
                            game.home_moneyline = int(outcome["price"])
                        elif outcome["name"] == item["away_team"]:
                            game.away_moneyline = int(outcome["price"])
                elif market["key"] == "spreads":
                    for outcome in market["outcomes"]:
                        if outcome["name"] == item["home_team"]:
                            game.spread = outcome["point"]
                            game.spread_home_odds = int(outcome["price"])
                elif market["key"] == "totals":
                    if market["outcomes"]:
                        game.over_under = market["outcomes"][0]["point"]
        return game
    except (KeyError, ValueError):
        return None


def format_moneyline(ml: Optional[int]) -> str:
    if ml is None:
        return "N/A"
    return f"+{ml}" if ml > 0 else str(ml)
