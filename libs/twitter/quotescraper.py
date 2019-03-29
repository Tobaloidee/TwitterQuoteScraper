import re
import html
import emoji
import unidecode
import tweepy
import collections
from . import API
from ..helpers import compose

QUOTE_PATTERN = re.compile(r'^"(?P<phrase>.*)"\s*?-\s*?(?P<author>.*)$')

Quote = collections.namedtuple('Quote', 'author phrase url')


class QuoteScraper:

    def __init__(self, twitter_creds: dict):
        self.api = API(twitter_creds)

    def get_quotes(self, tweeter_handle: str, status_since_id: str):
        tweeter_handle = tweeter_handle.lstrip('@')

        for status in tweepy.Cursor(self.api.user_timeline,
                                    screen_name=tweeter_handle,
                                    since_id=status_since_id,
                                    tweet_mode='extended').items():

            tweet = status._json

            tweet_id = tweet.get('id_str')
            tweet_context = tweet.get('full_text')
            tweet_entities = tweet.get('entities')

            normalize_tweet = compose(self.strip_emojis,
                                      self.strip_hashtags(tweet_entities),
                                      self.to_ascii,
                                      lambda s: s.replace('--', '-'))

            tweet_context = normalize_tweet(tweet_context)

            is_reply = tweet.get('in_reply_to_status_id')
            is_retweet = tweet.get('retweeted_status')
            has_url = tweet_entities.get('urls')
            has_media = tweet_entities.get('media')
            match = QUOTE_PATTERN.match(tweet_context)

            if any([is_reply,
                    is_retweet,
                    has_url,
                    has_media,
                    match is None]):
                continue

            url = 'https://twitter.com/CodeWisdom/status/{}'.format(tweet_id)
            phrase = self.strip_and_unescape(match.group('phrase'))
            author = self.strip_and_unescape(match.group('author'))

            yield Quote(author, phrase, url)

    @staticmethod
    def strip_emojis(tweet_context):
        return emoji.get_emoji_regexp().sub('', tweet_context)

    @staticmethod
    def strip_hashtags(tweet_entities: dict):
        hashtag_entities = tweet_entities.get('hashtags')
        hashtags = ['#{}'.format(e.get('text')) for e in hashtag_entities]

        def _strip_hashtags(tweet_context):
            for hashtag in hashtags:
                tweet_context = tweet_context.replace(hashtag, '')

            return tweet_context

        return _strip_hashtags

    @staticmethod
    def to_ascii(tweet_context):
        return unidecode.unidecode(tweet_context)

    @staticmethod
    def strip_and_unescape(tweet_context):
        function = compose(lambda s: s.strip(),
                           lambda s: html.unescape(s))

        return function(tweet_context)