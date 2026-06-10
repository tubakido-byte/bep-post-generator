import tweepy
import os
import sys
from datetime import datetime
import pytz

CONSUMER_KEY = os.environ['MIMA_CONSUMER_KEY']
CONSUMER_SECRET = os.environ['MIMA_CONSUMER_SECRET']
ACCESS_TOKEN = os.environ['MIMA_ACCESS_TOKEN']
ACCESS_TOKEN_SECRET = os.environ['MIMA_ACCESS_TOKEN_SECRET']

NOTE_URL = "https://note.com/mimamori_fukushi/n/n960c16a7e62f"

POSTS = [
    # slot 0 = 8:00 JST（問題提起・共感）
    f"""「終身サポート事業を始めたいが、何から手をつければいいか分からない」

社会福祉法人・NPOの担当者から
この相談を毎月何十件も受けます。

契約書の雛型すらない状態で
スタートして失敗した法人を
何度も見てきました。

正しい順番があります。👇
{NOTE_URL}

#終活支援 #社会福祉法人 #NPO #高齢者ビジネス""",

    # slot 1 = 12:00 JST（実績・権威）
    f"""厚労省ガイドラインの原型を作った機関が
全国19拠点・15年連続黒字を達成できた理由。

答えは「仕組み」です。

・契約書の標準化
・kintoneによる情報管理
・スタッフ教育マニュアル

この3つを整備した法人は
ほぼ例外なく黒字化しています。

詳しくはnoteで公開中👇
{NOTE_URL}

#終活 #介護経営 #社会福祉 #福祉経営""",

    # slot 2 = 21:00 JST（具体的価値・行動促進）
    f"""終身サポート事業で失敗する法人に共通する3つのパターン

①契約書を自作して法的リスクを抱える
②担当者の個人スキルに依存した運営
③監査対応の準備が後手に回る

講談社書籍2冊分のノウハウを
無料noteで公開しています。

社会福祉法人・NPO担当者の方へ↓
{NOTE_URL}

#社会福祉法人 #NPO #終活支援事業 #介護""",
]

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
