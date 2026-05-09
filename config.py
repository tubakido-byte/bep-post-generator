import os

X_CONSUMER_KEY = os.environ.get('X_CONSUMER_KEY', '')
X_CONSUMER_SECRET = os.environ.get('X_CONSUMER_SECRET', '')
X_ACCESS_TOKEN = os.environ.get('X_ACCESS_TOKEN', '')
X_ACCESS_TOKEN_SECRET = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

NEWS_SOURCES = {
    "🏛️ 産経新聞": [
        "https://www3.nhk.or.jp/rss/news/cat0.xml",
        "https://www3.nhk.or.jp/rss/news/cat1.xml",
        "https://www3.nhk.or.jp/rss/news/cat3.xml"
    ],
    "🌍 Axios": [
        "https://news.google.com/rss/search?q=site:axios.com&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=axios+news+today&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB?hl=en&gl=US&ceid=US:en"
    ],
    "🚀 Fox News": [
        "https://news.google.com/rss/search?q=site:foxnews.com&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=fox+news+today&hl=en&gl=US&ceid=US:en",
        "https://feeds.foxnews.com/foxnews/latest"
    ]
}
