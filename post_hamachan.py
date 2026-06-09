import tweepy
import os
import sys
from datetime import datetime
import pytz

CONSUMER_KEY = os.environ['HAMA_CONSUMER_KEY']
CONSUMER_SECRET = os.environ['HAMA_CONSUMER_SECRET']
ACCESS_TOKEN = os.environ['HAMA_ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = os.environ['HAMA_ACCESS_TOKEN_SECRET']

NOTE_URL = "https://note.com/hanasaka_granpa/n/n2932d4d78385"

POSTS = [
    # slot 0 = 8:00 JST（共感・問題提起）
    f"""「もう歳だから仕方ない」って
自分に言い聞かせてませんか？

終活、お金、認知症、詐欺、孤独…

誰にも言えずにひとりで抱えてきた
高齢者の「本当の悩み」を

浜ちゃんが全部まとめました。

👇 noteに書きました（1,980円）
{NOTE_URL}

#高齢者 #老後 #シニアライフ #終活""",

    # slot 1 = 12:00 JST（具体的解決策）
    f"""詐欺電話が来たら
この一言だけ言ってください👇

「息子に確認してから折り返します」

これだけで詐欺師は逃げます。

本物の業者なら後で折り返せます。
詐欺師は折り返せません。

老後の9つの困りごと解決法を
noteにまとめました📝

{NOTE_URL}

#詐欺対策 #高齢者 #シニアライフ""",

    # slot 2 = 21:00 JST（感情・ストーリー）
    f"""70年生きてきてわかったことがあります。

悩みが増えるほど
相談できる場所が減っていく。

子供には心配かけたくない。
医者に聞くのは恥ずかしい。
友人にはプライドがあって言えない。

そんな「言えない悩み」をひとつでも
解決できたらと思って書きました。

→ note「高齢者の9つの困りごと解決」
{NOTE_URL}

フォローすると毎日届きます🌸

#高齢者 #老後不安 #シニア #終活""",
]

# スロット決定
if len(sys.argv) > 1:
    slot = int(sys.argv[1])
else:
    jst = pytz.timezone('Asia/Tokyo')
    hour = datetime.now(jst).hour
    if hour >= 20:
        slot = 2
    elif hour >= 11:
        slot = 1
    else:
        slot = 0

client = tweepy.Client(
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

text = POSTS[slot]
response = client.create_tweet(text=text)
print(f"✅ 投稿完了 slot={slot} / tweet_id={response.data['id']}")
