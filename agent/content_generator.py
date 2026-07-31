"""
Uses Claude (claude-haiku-4-5) with prompt caching to generate tweet text
for each post type: game previews and app-highlight posts.
"""

from __future__ import annotations

import anthropic
from sports_data import Game, format_moneyline

_SYSTEM_PROMPT = """You write punchy, engaging tweets for NORMA — a sports alerts and wager tracking app.

NORMA helps fans:
- Get instant game alerts for their teams
- Track their wagers in one place
- See live odds from major sportsbooks
- Monitor Kalshi and Polymarket predictions

Tone: energetic, knowledgeable sports fan. No fluff. No em-dashes.
Rules:
- Max 240 characters (leave room for image)
- 1-2 relevant hashtags max
- No gambling advice or picks
- End with a subtle NORMA CTA when natural
- No quotation marks around the tweet"""


def generate_game_preview_tweet(games: list[Game], api_key: str) -> str:
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

    games_text = "\n".join(game_summaries)
    prompt = f"""Write a tweet previewing today's games. Here are the matchups with odds:

{games_text}

Pick the most interesting matchup or angle. Do not give a pick or gambling advice."""

    return _call_claude(prompt, api_key)


def generate_app_highlight_tweet(games: list[Game], api_key: str) -> str:
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

    prompt = f"""Write a tweet showcasing the NORMA app.
Context: There are {game_count} games today across {sports_str}.
Highlight how NORMA makes tracking alerts and wagers easy.
Show the app screenshot and drive people to download it."""

    return _call_claude(prompt, api_key)


def _call_claude(user_prompt: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()
