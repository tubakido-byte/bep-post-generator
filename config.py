import os

X_CONSUMER_KEY = os.environ.get('X_CONSUMER_KEY', '')
X_CONSUMER_SECRET = os.environ.get('X_CONSUMER_SECRET', '')
X_ACCESS_TOKEN = os.environ.get('X_ACCESS_TOKEN', '')
X_ACCESS_TOKEN_SECRET = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

NEWS_SOURCES = {
    "🏛️ 産経新聞": "https://news.google.com/rss/search?q=site:sankei.com&hl=ja&gl=JP&ceid=JP:ja",
    "🌍 Axios": "https://feeds.bloomberg.com/markets/news.rss",
    "🚀 Fox News": "https://feeds.foxnews.com/foxnews/latest"
}
