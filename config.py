import os

X_OAUTH2_ACCESS_TOKEN = os.environ.get('X_OAUTH2_ACCESS_TOKEN', '')
X_API_ENDPOINT = os.environ.get('X_API_ENDPOINT', 'https://api.twitter.com/2/tweets')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

NEWS_SOURCES = {
    "🌍 Axios": "https://feeds.bloomberg.com/markets/news.rss",
    "🏛️ 産経新聞": "https://news.google.com/rss/search?q=site:sankei.com&hl=ja&gl=JP&ceid=JP:ja",
    "🚀 Fox News": "https://feeds.foxnews.com/foxnews/latest"
}
