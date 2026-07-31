from __future__ import annotations

from io import BytesIO
import tweepy

from config import Config


class TwitterClient:
    def __init__(self, cfg: Config):
        # v1.1 client needed for media upload
        auth = tweepy.OAuth1UserHandler(
            cfg.twitter_api_key,
            cfg.twitter_api_secret,
            cfg.twitter_access_token,
            cfg.twitter_access_token_secret,
        )
        self._v1 = tweepy.API(auth)

        # v2 client for creating tweets
        self._v2 = tweepy.Client(
            bearer_token=cfg.twitter_bearer_token,
            consumer_key=cfg.twitter_api_key,
            consumer_secret=cfg.twitter_api_secret,
            access_token=cfg.twitter_access_token,
            access_token_secret=cfg.twitter_access_token_secret,
        )

    def upload_image(self, image_bytes: BytesIO, filename: str = "norma.png") -> str:
        image_bytes.seek(0)
        media = self._v1.media_upload(filename=filename, file=image_bytes)
        return media.media_id_string

    def post_tweet(self, text: str, media_ids: list[str] | None = None) -> str:
        kwargs: dict = {"text": text}
        if media_ids:
            kwargs["media_ids"] = media_ids
        response = self._v2.create_tweet(**kwargs)
        return response.data["id"]

    def post_with_image(self, text: str, image_bytes: BytesIO, filename: str = "norma.png") -> str:
        media_id = self.upload_image(image_bytes, filename)
        return self.post_tweet(text, media_ids=[media_id])
