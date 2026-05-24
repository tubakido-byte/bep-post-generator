#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import base64
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests_oauthlib import OAuth1
from config import X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, GEMINI_API_KEY, OPENAI_API_KEY, NEWS_SOURCES

def post_to_x(text: str, image_b64: str = None, credentials: dict = None) -> dict:
    # サーバーのCK/CSをベースに、ユーザーのAT/ATSがあれば優先使用
    ck = X_CONSUMER_KEY
    cs = X_CONSUMER_SECRET
    if credentials and credentials.get('at') and credentials.get('ats'):
        at  = credentials['at']
        ats = credentials['ats']
        # プレミアム手動設定: 独自CK/CSも上書き
        if credentials.get('ck') and credentials.get('cs'):
            ck = credentials['ck']
            cs = credentials['cs']
    else:
        at  = X_ACCESS_TOKEN
        ats = X_ACCESS_TOKEN_SECRET
    auth = OAuth1(ck, cs, at, ats)
    try:
        media_ids = []
        if image_b64:
            img_data = base64.b64decode(image_b64)
            up = requests.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                files={"media": ("image.png", img_data, "image/png")},
                auth=auth, timeout=60
            )
            print(f"[DEBUG] media upload status={up.status_code} body={up.text[:200]}")
            if up.status_code != 200:
                return {"success": False, "error": f"画像アップロード失敗({up.status_code}): {up.text[:150]}"}
            media_ids = [up.json()['media_id_string']]

        body = {"text": text[:280]}
        if media_ids:
            body["media"] = {"media_ids": media_ids}

        r = requests.post("https://api.twitter.com/2/tweets", json=body, auth=auth, timeout=30)
        if r.status_code == 201:
            tweet_id = r.json()['data']['id']
            tweet_url = f"https://x.com/i/web/status/{tweet_id}"
            return {"success": True, "tweet_id": tweet_id, "tweet_url": tweet_url}
        return {"success": False, "error": r.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _call_gemini(prompt: str, retries: int = 2) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    for attempt in range(retries):
        try:
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            if r.status_code == 429 and attempt < retries - 1:
                time.sleep(2)
                continue
        except Exception as e:
            print(f"[DEBUG] Gemini error (attempt {attempt+1}): {e}")
            if attempt < retries - 1:
                time.sleep(1)
    return ""

def _generate_one_image(prompt: str) -> str:
    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=120)
            if r.status_code == 200:
                b64 = r.json()['data'][0].get('b64_json', '')
                if b64:
                    return b64
            if r.status_code == 429 and attempt < 2:
                time.sleep(5 + attempt * 3)
                continue
            print(f"[DEBUG] OpenAI image error: {r.status_code} {r.text[:200]}")
        except Exception as e:
            print(f"[DEBUG] OpenAI image error (attempt {attempt+1}): {e}")
            if attempt < 2:
                time.sleep(2)
    return ""

def generate_images(tweet_text: str) -> list:
    nanobanana = """# Role
あなたはX(旧Twitter)で高いインプレッションとエンゲージメント（いいね・保存）を獲得する専門の「AI画像クリエイター兼マーケター」です。

# Mission
SNSのタイムラインでユーザーの指を止め、直感的に「保存したい」「誰かに見せたい」と思わせるクオリティの高い画像を生成してください。

# Guidelines for Image Generation
以下の[バズるための構成要素]を必ずプロンプトに組み込んでください。

1. 【視覚的インパクト】
   - ライティング：Cinematic lighting, Dramatic shadows, Ray tracing を活用し、立体感と高級感を出すこと。
   - 解像度：8k, Highly detailed, Masterpiece を使用し、細部まで描き込むこと。
2. 【共感と情緒】
   - 季節感、特定のシチュエーション（雨、朝の光、カフェ、未来的な都市など）を明確にし、見る人の感情に訴える「ストーリー性」を持たせること。
3. 【構図の最適化】
   - 視線誘導：被写体を強調し、背景と被写体のコントラストを最適化すること。
   - 没入感：スマホ画面越しにその空間に入り込めるような広角またはクローズアップ構図を選択すること。

# Output Format
- [Subject]: 被写体とアクションの詳細
- [Environment]: 背景と雰囲気（ムード）
- [Lighting]: 光の演出
- [Technical Tags]: (8k, masterpiece, highly detailed, cinematic, photorealistic/anime style)

# Constraint
- High quality, detailed anatomy 等を必ず含めること。
- ターゲットユーザーが「壁紙にしたくなる」高い美的センスを追求すること。"""

    combined = _call_gemini(
        f"{nanobanana}\n\nテーマ：{tweet_text}\n\n"
        f"【重要】まずテーマの主役（動物・人物・場所・象徴など）を特定し、その主役を必ず画像の中心被写体にすること。"
        f"例：クマのニュース→クマを主役、政治家の話題→その人物や政治の象徴を主役。汎用的な人物や風景だけにしない。\n\n"
        f"以下の形式で出力してください。\n"
        f"1行目：このテーマを端的に表す日本語タイトル（16文字以内）\n"
        f"2行目：スタイル1（フォトリアリスティック・報道写真風）主役を中心にした画像生成プロンプト（英語）\n"
        f"3行目：スタイル2（ドラマチック・シネマティック）主役を中心にした画像生成プロンプト（英語）\n"
        f"4行目：スタイル3（イラスト・アート系）主役を中心にした画像生成プロンプト（英語）\n"
        f"タイトルと3行のプロンプトのみ出力。各行は改行で区切る。"
    ) or tweet_text
    lines = [l.strip() for l in combined.split('\n') if l.strip()]
    jp_title = lines[0][:16] if lines else tweet_text[:16]
    prompts = lines[1:4] if len(lines) >= 4 else [tweet_text] * 3
    while len(prompts) < 3:
        prompts.append(prompts[0] if prompts else tweet_text)

    def _with_delay(args):
        prompt, delay = args
        if delay > 0:
            time.sleep(delay)
        return _generate_one_image(prompt)

    tasks = [(p, i * 3) for i, p in enumerate(prompts[:3])]
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(_with_delay, tasks))
    return {"images": [r for r in results if r], "title": jp_title}

def _shorten_to_280(text: str) -> str:
    if len(text) <= 280:
        return text
    shortened = _call_gemini(
        f"次の文章を、意味を保ちながら必ず280文字以内に短縮してください。"
        f"【重要】3段落構成（段落間は空行＝改行2つ）を必ず保持すること。文章が途中で切れないようにしてください。投稿文のみ出力。\n\n{text}"
    )
    return shortened[:280] if shortened else text[:277] + "..."

def generate_posts(topic: str) -> dict:
    rule = (
        "【厳守】必ず3段落構成で書くこと。段落と段落の間は空行（改行2つ）で区切ること。"
        "各段落は2〜3文、合計280文字以内。文章は必ず最後まで完結させること。"
        "投稿文のみ出力（説明・前置き・番号不要）。"
    )
    prompts_list = [
        f"X（Twitter）投稿を1つ書いてください。【文体】感情・共感を前面に出した文体。{rule}\n【元のテキスト】{topic}",
        f"X（Twitter）投稿を1つ書いてください。【文体】客観的な事実と分析の文体。{rule}\n【元のテキスト】{topic}",
        f"X（Twitter）投稿を1つ書いてください。【文体】読者への問いかけ・対話を促す文体。{rule}\n【元のテキスト】{topic}",
    ]
    patterns = [None, None, None]
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_idx = {executor.submit(_call_gemini, p): i for i, p in enumerate(prompts_list)}
        try:
            for future in as_completed(future_to_idx, timeout=50):
                idx = future_to_idx[future]
                try:
                    text = future.result()
                    if text and len(text) > 5:
                        patterns[idx] = _shorten_to_280(text)
                except Exception as e:
                    print(f"[DEBUG] Future error: {e}")
        except Exception:
            pass
    for i, p in enumerate(patterns):
        if p is None:
            result = _call_gemini(prompts_list[i])
            patterns[i] = _shorten_to_280(result) if result else None
    result = [p for p in patterns if p]
    posts = result if result else [topic]
    return {"prompts": posts, "labels": posts}

def _fetch_rss(url: str) -> list:
    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }, timeout=15)
    root = ET.fromstring(resp.content)
    raw = []
    for item in root.findall('.//item')[:5]:
        title_el = item.find('title')
        link_el = item.find('link')
        title = (title_el.text or '').strip() if title_el is not None else ''
        link = (link_el.text or link_el.get('href', '#') or '#').strip() if link_el is not None else '#'
        if ' - ' in title:
            title = title.rsplit(' - ', 1)[0].strip()
        if title:
            raw.append({"title": title, "link": link})
    return raw

def get_news_articles(source: str) -> list:
    urls = NEWS_SOURCES.get(source, list(NEWS_SOURCES.values())[0])
    raw = []
    for url in urls:
        try:
            raw = _fetch_rss(url)
            if raw:
                break
        except Exception as e:
            print(f"[DEBUG] RSS failed ({url}): {e}")

    if not raw:
        return [{"title": "記事なし", "summary": "RSS に記事が見つかりません", "link": "#"}]

    if '産経新聞' not in source:
        numbered = "\n".join([f"{i+1}. {a['title']}" for i, a in enumerate(raw)])
        prompt = f"次の英語タイトルを日本語に翻訳してください。番号付きリストのみ出力。\n{numbered}"
        try:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            r2 = requests.post(gemini_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
            if r2.status_code == 200:
                lines = r2.json()['candidates'][0]['content']['parts'][0]['text'].strip().split('\n')
                parsed = [l.split('. ', 1)[-1].strip() for l in lines if l.strip() and l.strip()[0].isdigit()]
                if len(parsed) == len(raw):
                    return [{"title": t, "summary": '', "link": a['link']} for t, a in zip(parsed, raw)]
        except Exception as e:
            print(f"[DEBUG] Translate error: {e}")

    return [{"title": a['title'], "summary": '', "link": a['link']} for a in raw]

def surge_long_post(topic: str, context: str = '') -> dict:
    ctx = f"\n\nユーザーの文体・製品情報（必ず反映）:\n{context}" if context else ''
    prompt = (
        f"あなたはX（旧Twitter）のアルゴリズムを熟知したプロのSNSマーケターです。"
        f"以下のネタで「動画＋長文」形式のXポストを作成してください。{ctx}\n\n"
        f"【厳守】\n"
        f"1. 冒頭2行：ターゲットを特定しソリューションを提示（例：〇〇で悩む人は〇〇すべき）\n"
        f"2. 本文：ステップ形式（3〜8ステップ）で数字付き箇条書き\n"
        f"3. 末尾：最も重要な結論を1行\n"
        f"4. 最終行：「▶ 動画には大きな文字でテロップを入れてください」\n"
        f"5. 1000文字以内で完結\n\n"
        f"【ネタ】{topic}\n\n投稿文のみ出力。"
    )
    result = _call_gemini(prompt)
    return {"post": result} if result else {"post": "", "error": "生成失敗"}

def surge_buzz(topic: str, style: str = 'list', context: str = '') -> dict:
    ctx = f"\n\nユーザーの文体・製品情報（必ず反映）:\n{context}" if context else ''
    if style == 'target':
        instruction = "「ターゲット＋ソリューション型」で生成。冒頭に「〇〇な人へ。〇〇することで〇〇できます」を置き、方法を3〜5個の番号リストで続ける。最後に一言まとめ。280文字以内。"
    else:
        instruction = "「リスト形式（ブックマーク誘発型）」で生成。タイトル行→数字付きリスト5〜8個→「保存して後で見返してください」等の締め。280文字以内。"
    prompt = (
        f"あなたはSNSバズのスペシャリストです。日本人がブックマークしたくなる投稿を作成してください。{ctx}\n\n"
        f"{instruction}\n\n【ネタ】{topic}\n\n投稿文のみ出力。"
    )
    result = _call_gemini(prompt)
    return {"post": result} if result else {"post": "", "error": "生成失敗"}

def surge_self_quote(past_post: str, context: str = '') -> dict:
    ctx = f"\n\nユーザーの文体（必ず反映）:\n{context}" if context else ''
    prompt = (
        f"過去のバズ投稿を元に自己引用（セルフQR）するための文章を作成してください。{ctx}\n\n"
        f"【戦略】\n"
        f"1. 好奇心をそそり元ポストを見に行きたくなる文章\n"
        f"2. 「最新事例を見つけました」「今の私ならこう付け加えます」等で価値を上乗せ\n"
        f"3. 140文字以内\n\n"
        f"【引用する過去の投稿】\n{past_post}\n\n自己引用文のみ出力。"
    )
    result = _call_gemini(prompt)
    return {"post": result} if result else {"post": "", "error": "生成失敗"}

def surge_inspo(theme: str = '') -> dict:
    base = f"テーマ：{theme}\n\n" if theme else ''
    prompt = (
        f"あなたはアテンション・エコノミーの専門家です。{base}"
        f"X（旧Twitter）でインプレッションが爆発するトピックを3つ提案してください。\n\n"
        f"各トピックの形式：\n"
        f"【タイトル】AかBか、極論を提示する切り口\n"
        f"【刺激要素】本能的に反応してしまう要素\n"
        f"【昇華】前向きな解決策への変換\n"
        f"【サンプル文】そのまま使える投稿の書き出し1〜2行\n\n"
        f"3トピックを番号付きで出力。"
    )
    result = _call_gemini(prompt)
    return {"topics": result} if result else {"topics": "", "error": "生成失敗"}

def surge_profile_check(profile: str, pinned_post: str = '', context: str = '') -> dict:
    ctx = f"\n\nアカウントの製品・ターゲット情報:\n{context}" if context else ''
    pinned = f"\n\n【固定ポスト】\n{pinned_post}" if pinned_post else ''
    prompt = (
        f"ユーザーのXプロフィールを分析しフォロー率を高める改善案を提示してください。{ctx}\n\n"
        f"【チェック項目】\n"
        f"1. 権威性と人間性：何者か一瞬で伝わるか\n"
        f"2. ベネフィット：フォローで得られる良いことが明確か\n"
        f"3. 固定ポストのフック：最強の動画＋長文になっているか\n"
        f"4. ファネル機能：製品・サービスへの導線として機能しているか\n\n"
        f"【現在のプロフィール】\n{profile}{pinned}\n\n"
        f"診断結果と具体的な改善案を日本語で出力。"
    )
    result = _call_gemini(prompt)
    return {"diagnosis": result} if result else {"diagnosis": "", "error": "生成失敗"}

def health_check() -> dict:
    results = {"gemini": "NG", "x_api": "NG", "env_vars": "NG", "overall": "NG"}

    missing = [k for k in ["GEMINI_API_KEY", "X_CONSUMER_KEY", "X_CONSUMER_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
               if not __import__('os').environ.get(k)]
    results["env_vars"] = "OK" if not missing else f"未設定: {', '.join(missing)}"

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        r = requests.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]}, timeout=10)
        results["gemini"] = "OK" if r.status_code == 200 else f"エラー {r.status_code}"
    except Exception as e:
        results["gemini"] = f"接続失敗: {str(e)[:50]}"

    results["x_api"] = "OK" if all([X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]) else "APIキー未設定"

    results["overall"] = "OK" if all(v == "OK" for v in [results["gemini"], results["x_api"], results["env_vars"]]) else "NG"
    return results
