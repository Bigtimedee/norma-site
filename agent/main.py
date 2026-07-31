#!/usr/bin/env python3
"""
NORMA Social Media Agent
Runs twice daily via GitHub Actions to post game previews and app highlights to X/Twitter.

Post types (selected by POST_TYPE env var or CLI arg):
  game_preview  – sports alert card image + tweet about today's games
  app_highlight – phone mockup image + tweet showcasing the NORMA app

Exit codes:
  0   posted successfully
  1   a real failure (network, API rejection, bad data)
  78  not configured — required secrets are absent (EX_CONFIG)

78 is separated from 1 on purpose. A scheduled job that has never been given
its credentials is not broken, and reporting it as broken twice a day trains
everyone to ignore the alert that eventually matters.
"""

from __future__ import annotations

import argparse
import os
import sys
import logging

from config import Config, ConfigurationError, REQUIRED_ENV, SECRETS_LOCATION
from sports_data import fetch_todays_games
from media_generator import generate_game_alert_card, generate_app_mockup
from content_generator import generate_game_preview_tweet, generate_app_highlight_tweet
from twitter_client import TwitterClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

POST_TYPES = ("game_preview", "app_highlight")

EX_CONFIG = 78  # sysexits.h — configuration error


def run(post_type: str) -> int:
    log.info("Starting NORMA agent | post_type=%s", post_type)

    try:
        cfg = Config.from_env()
    except ConfigurationError as exc:
        _report_missing_config(exc)
        return EX_CONFIG

    log.info("Fetching today's games...")
    games = fetch_todays_games(cfg.odds_api_key, cfg.sports)
    log.info("Found %d games today", len(games))

    twitter = TwitterClient(cfg)

    if post_type == "game_preview":
        log.info("Generating game alert card...")
        image = generate_game_alert_card(games)
        log.info("Generating tweet text...")
        text = generate_game_preview_tweet(games, cfg.anthropic_api_key)
        log.info("Tweet: %s", text)
        tweet_id = twitter.post_with_image(text, image, filename="norma_games.png")
        log.info("Posted game preview tweet: https://x.com/i/web/status/%s", tweet_id)

    elif post_type == "app_highlight":
        log.info("Generating app mockup...")
        image = generate_app_mockup(games)
        log.info("Generating tweet text...")
        text = generate_app_highlight_tweet(games, cfg.anthropic_api_key)
        log.info("Tweet: %s", text)
        tweet_id = twitter.post_with_image(text, image, filename="norma_app.png")
        log.info("Posted app highlight tweet: https://x.com/i/web/status/%s", tweet_id)

    else:
        log.error("Unknown post_type: %s. Choose from: %s", post_type, POST_TYPES)
        return 1

    return 0


def _report_missing_config(exc: ConfigurationError) -> None:
    """
    Say what is missing, where it comes from, and where to put it.

    The previous behaviour was an unhandled traceback ending in
    `OSError: Missing required env vars: ...`, which named the variables but
    not what they were for or where to set them.
    """
    log.error("NORMA agent is not configured — nothing was posted.")
    log.error("")
    log.error("Missing %d of %d required secrets:", len(exc.missing), len(REQUIRED_ENV))
    for name in exc.missing:
        log.error("  %-30s from %s", name, REQUIRED_ENV[name])
    present = [k for k in REQUIRED_ENV if k not in exc.missing]
    if present:
        log.error("Already set: %s", ", ".join(present))
    log.error("")
    log.error("Set them here: %s", SECRETS_LOCATION)
    log.error("Names must match exactly. An unset secret becomes an empty string, "
              "which counts as missing.")


def main() -> int:
    parser = argparse.ArgumentParser(description="NORMA X/Twitter publishing agent")
    parser.add_argument(
        "post_type",
        nargs="?",
        default=os.environ.get("POST_TYPE", "game_preview"),
        choices=POST_TYPES,
        help="Type of post to publish (default: game_preview)",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Report configuration status and exit without posting",
    )
    args = parser.parse_args()

    if args.check_config:
        missing = Config.missing_env()
        if missing:
            _report_missing_config(ConfigurationError(missing))
            return EX_CONFIG
        log.info("All %d required secrets are set.", len(REQUIRED_ENV))
        return 0

    return run(args.post_type)


if __name__ == "__main__":
    sys.exit(main())
