import os
from logging import getLogger, StreamHandler, DEBUG
from typing import Any
import tweepy

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)
logger.setLevel(DEBUG)


class TweetHandler:
    def __init__(self):
        logger.info("Initializing TweetHandler")
        self.client = tweepy.Client(
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
        )

    def post_tweet(self, content: str) -> Any:
        logger.info("Posting tweet")
        try:
            response = self.client.create_tweet(text=content)
            logger.info("Tweet posted successfully")
            return response
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            raise
