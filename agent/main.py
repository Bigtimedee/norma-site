#!/usr/bin/env python3
"""
NORMA Social Media Agent
Runs twice daily via GitHub Actions to post game previews and app highlights to X/Twitter.

Post types (selected by POST_TYPE env var or CLI arg):
  game_preview  – sports alert card image + tweet about today's games
  app_highlight – phone mockup image + tweet showcasing the NORMA app
"""

from __future__ import annotations

import argparse
import os
import sys
import logging

from config import Config
from sports_data import fetch_todays_games
from media_generator import generate_game_alert_card, generate_app_mockup
from content_generator import generate_game_preview_tweet, generate_app_highlight_tweet
from twitter_client import TwitterClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

POST_TYPES = ("game_preview", "app_highlight")


def run(post_type: str):
    log.info("Starting NORMA agent | post_type=%s", post_type)

    cfg = Config.from_env()
    sports = [s.strip() for s in cfg.sport.split(",")]

    log.info("Fetching today's games...")
    games = fetch_todays_games(cfg.odds_api_key, sports)
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
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NORMA X/Twitter publishing agent")
    parser.add_argument(
        "post_type",
        nargs="?",
        default=os.environ.get("POST_TYPE", "game_preview"),
        choices=POST_TYPES,
        help="Type of post to publish (default: game_preview)",
    )
    args = parser.parse_args()
    run(args.post_type)


if __name__ == "__main__":
    main()
