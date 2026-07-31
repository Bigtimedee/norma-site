import os
from dataclasses import dataclass


class ConfigurationError(Exception):
    """
    Required configuration is absent or empty.

    Deliberately not `EnvironmentError`: in Python 3 that is an alias for
    `OSError`, so raising it printed this as `OSError: Missing required env
    vars: ...` and read like a filesystem or I/O fault. It is neither. A
    distinct type lets callers separate "not configured yet" from "broken",
    which is the difference between a quiet skip and a real alert.
    """

    def __init__(self, missing: list[str]):
        self.missing = list(missing)
        super().__init__(
            "Missing required environment variables: " + ", ".join(self.missing)
        )


# Every variable the agent cannot run without, with a human-readable source so
# an operator reading a log knows where to go rather than having to guess.
REQUIRED_ENV: dict[str, str] = {
    "TWITTER_API_KEY": "X/Twitter developer portal",
    "TWITTER_API_SECRET": "X/Twitter developer portal",
    "TWITTER_ACCESS_TOKEN": "X/Twitter developer portal",
    "TWITTER_ACCESS_TOKEN_SECRET": "X/Twitter developer portal",
    "TWITTER_BEARER_TOKEN": "X/Twitter developer portal",
    "ANTHROPIC_API_KEY": "console.anthropic.com/settings/keys",
    "ODDS_API_KEY": "the-odds-api.com",
}

# Where to set them. Named in the error output so the fix does not require
# reading the source or asking whoever wrote it.
SECRETS_LOCATION = (
    "GitHub repository -> Settings -> Secrets and variables -> Actions "
    "-> New repository secret"
)


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

    # The Odds API (https://the-odds-api.com)
    odds_api_key: str

    # Optional: sport to focus on (default covers major US sports)
    sport: str = "americanfootball_nfl,basketball_nba,baseball_mlb,icehockey_nhl"

    @property
    def sports(self) -> list[str]:
        return [s.strip() for s in self.sport.split(",") if s.strip()]

    @classmethod
    def missing_env(cls) -> list[str]:
        """
        Which required variables are absent or empty, without raising.

        An unset GitHub Actions secret interpolates to an empty string rather
        than being absent, so emptiness is the condition that matters here, not
        presence of the key.
        """
        return [k for k in REQUIRED_ENV if not os.environ.get(k, "").strip()]

    @classmethod
    def is_configured(cls) -> bool:
        return not cls.missing_env()

    @classmethod
    def from_env(cls) -> "Config":
        missing = cls.missing_env()
        if missing:
            raise ConfigurationError(missing)

        return cls(
            twitter_api_key=os.environ["TWITTER_API_KEY"],
            twitter_api_secret=os.environ["TWITTER_API_SECRET"],
            twitter_access_token=os.environ["TWITTER_ACCESS_TOKEN"],
            twitter_access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
            twitter_bearer_token=os.environ["TWITTER_BEARER_TOKEN"],
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            odds_api_key=os.environ["ODDS_API_KEY"],
            sport=os.environ.get("NORMA_SPORT", cls.sport),
        )
