import os

X_CONSUMER_KEY = os.environ.get('X_CONSUMER_KEY', '')
X_CONSUMER_SECRET = os.environ.get('X_CONSUMER_SECRET', '')
X_ACCESS_TOKEN = os.environ.get('X_ACCESS_TOKEN', '')
X_ACCESS_TOKEN_SECRET = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

NEWS_SOURCES = {
    "🏛️ 産経新聞": "https://www3.nhk.or.jp/rss/news/cat0.xml",
    "🌍 Axios": "http://feeds.bbci.co.uk/news/rss.xml",
    "🚀 Fox News": "https://techcrunch.com/feed/"
}
