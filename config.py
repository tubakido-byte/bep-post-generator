import os

X_OAUTH2_ACCESS_TOKEN = os.environ.get('X_OAUTH2_ACCESS_TOKEN', '')
X_API_ENDPOINT = os.environ.get('X_API_ENDPOINT', 'https://api.twitter.com/2/tweets')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

NEWS_SOURCES = {
    "🏛️ NHK": "https://www3.nhk.or.jp/rss/news/cat0.xml",
    "🌍 BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "🚀 TechCrunch": "https://techcrunch.com/feed/"
}
