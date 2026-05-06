import os

X_CONSUMER_KEY = os.environ.get('X_CONSUMER_KEY', '')
X_CONSUMER_SECRET = os.environ.get('X_CONSUMER_SECRET', '')
X_ACCESS_TOKEN = os.environ.get('X_ACCESS_TOKEN', '')
X_ACCESS_TOKEN_SECRET = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

NEWS_SOURCES = {
    "🏛️ NHK": "https://www3.nhk.or.jp/rss/news/cat0.xml",
    "🌍 BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "🚀 TechCrunch": "https://techcrunch.com/feed/"
}
