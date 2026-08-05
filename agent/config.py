import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    # X/Twitter API v2
    twitter_api_key: str
    twitter_api_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str
    twitter_bearer_token: str

    # Anthropic
    anthropic_api_key: str

    # The Odds API (https://the-odds-api.com) — optional; falls back to ESPN
    odds_api_key: Optional[str]

    # Optional: sport to focus on (default covers major US sports)
    sport: str = "americanfootball_nfl,basketball_nba,baseball_mlb,icehockey_nhl"

    @classmethod
    def from_env(cls) -> "Config":
        missing = []
        required = [
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
            "TWITTER_BEARER_TOKEN",
            "ANTHROPIC_API_KEY",
        ]
        for key in required:
            if not os.environ.get(key):
                missing.append(key)
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

        return cls(
            twitter_api_key=os.environ["TWITTER_API_KEY"],
            twitter_api_secret=os.environ["TWITTER_API_SECRET"],
            twitter_access_token=os.environ["TWITTER_ACCESS_TOKEN"],
            twitter_access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
            twitter_bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            odds_api_key=os.environ.get("ODDS_API_KEY") or None,
            sport=os.environ.get("NORMA_SPORT", cls.sport),
        )
