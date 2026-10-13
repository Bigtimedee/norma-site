"""
Deterministic template-based tweet text for each post type:
game previews and app-highlight posts. No external AI provider.
"""

from __future__ import annotations

import logging
import re

from sports_data import Game, format_moneyline

log = logging.getLogger(__name__)

_PREAMBLE_RE = re.compile(
    r"^(here'?s\s+(a\s+)?tweet|here\s+is\s+(a\s+)?tweet|tweet:)",
    re.I,
)
_CHAR_COUNT_RE = re.compile(r"\*?\*?character\s+count:?\s*\d+\*?\*?", re.I)


def sanitize_tweet(text: str) -> str:
    """Strip meta-commentary (preambles, separators, char-count notes)."""
    # Drop everything after a --- separator
    text = re.split(r"\n\s*---", text, maxsplit=1)[0].strip()

    # Remove a leading preamble line ("Here's a tweet for you:", etc.)
    lines = text.splitlines()
    if lines and _PREAMBLE_RE.match(lines[0].strip()):
        lines = lines[1:]

    # Remove character-count annotation lines
    lines = [ln for ln in lines if not _CHAR_COUNT_RE.search(ln)]

    return "\n".join(lines).strip()


def _truncate_at_word(text: str, limit: int = 280) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    last_space = cut.rfind(" ")
    return (cut[:last_space] if last_space > 0 else cut).rstrip()


def generate_game_preview_tweet(games: list[Game], api_key: str = "") -> str:
    if not games:
        return "Big sports day ahead. Track every game alert in real time with NORMA. 🏆 #Sports"

    game_summaries = []
    for g in games[:3]:
        away = g.away_team.split()[-1]
        home = g.home_team.split()[-1]
        ml_home = format_moneyline(g.home_moneyline)
        ml_away = format_moneyline(g.away_moneyline)
        spread = f"Spread: {g.spread:+.1f}" if g.spread else ""
        ou = f"O/U: {g.over_under}" if g.over_under else ""
        game_summaries.append(
            f"{g.sport_emoji} {away} @ {home} | {g.time_str} | ML: {away} {ml_away} / {home} {ml_home} | {spread} | {ou}"
        )

    lead = game_summaries[0]
    text = f"Today's slate: {lead}. {len(games)} games on the board. Live alerts and odds in NORMA. #NORMA"
    return _finalize(text)


def generate_app_highlight_tweet(games: list[Game], api_key: str = "") -> str:
    game_count = len(games)
    sports = list({g.sport for g in games})
    sport_names = {
        "americanfootball_nfl": "NFL",
        "basketball_nba": "NBA",
        "baseball_mlb": "MLB",
        "icehockey_nhl": "NHL",
    }
    sport_labels = [sport_names.get(s, s) for s in sports]
    sports_str = " + ".join(sport_labels)

    text = (
        f"{game_count} games today across {sports_str or 'the board'}. "
        "Alerts, live odds and every wager in one place. Get NORMA. #NORMA"
    )
    return _finalize(text)


def _finalize(text: str) -> str:
    text = _truncate_at_word(sanitize_tweet(text), 280)
    log.info("Final tweet (%d chars): %s", len(text), text)
    return text
