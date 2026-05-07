#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import base64
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from requests_oauthlib import OAuth1
from config import X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, GEMINI_API_KEY, NEWS_SOURCES

def post_to_x(text: str, image_b64: str = None) -> dict:
    auth = OAuth1(X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
    try:
        media_ids = []
        if image_b64:
            up = requests.post(
                "https://upload.twitter.com/1.1/media/upload.json",
                files={"media": base64.b64decode(image_b64)},
                auth=auth, timeout=60
            )
            if up.status_code != 200:
                return {"success": False, "error": f"画像アップロード失敗: {up.text[:100]}"}
            media_ids = [up.json()['media_id_string']]

        body = {"text": text[:280]}
        if media_ids:
            body["media"] = {"media_ids": media_ids}

        r = requests.post("https://api.twitter.com/2/tweets", json=body, auth=auth, timeout=30)
        if r.status_code == 201:
            return {"success": True, "tweet_id": r.json()['data']['id']}
        return {"success": False, "error": r.text[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _call_gemini(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25)
        if r.status_code == 200:
            return r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"[DEBUG] Gemini error: {e}")
    return ""

def _generate_one_image(prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            for part in r.json()['candidates'][0]['content']['parts']:
                if 'inlineData' in part:
                    return part['inlineData']['data']
        print(f"[DEBUG] Image gen error: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"[DEBUG] Image gen error: {e}")
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
        f"{nanobanana}\n\nテーマ：{tweet_text}\n\n以下の形式で出力してください。\n"
        f"1行目：このテーマを端的に表す日本語タイトル（16文字以内）\n"
        f"2行目：スタイル1（フォトリアリスティック・報道写真風）の画像生成プロンプト（英語）\n"
        f"3行目：スタイル2（ドラマチック・シネマティック）の画像生成プロンプト（英語）\n"
        f"4行目：スタイル3（イラスト・アート系）の画像生成プロンプト（英語）\n"
        f"タイトルと3行のプロンプトのみ出力。各行は改行で区切る。"
    ) or tweet_text
    lines = [l.strip() for l in combined.split('\n') if l.strip()]
    jp_title = lines[0][:16] if lines else tweet_text[:16]
    prompts = lines[1:4] if len(lines) >= 4 else [tweet_text] * 3
    while len(prompts) < 3:
        prompts.append(prompts[0] if prompts else tweet_text)

    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(_generate_one_image, prompts[:3]))
    return {"images": [r for r in results if r], "title": jp_title}

def generate_posts(topic: str) -> dict:
    prompts_list = [
        f"X（Twitter）投稿を1つだけ書いてください。感情・共感を前面に出した文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
        f"X（Twitter）投稿を1つだけ書いてください。客観的な事実と分析の文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
        f"X（Twitter）投稿を1つだけ書いてください。読者への問いかけ・対話を促す文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
    ]
    patterns = [None, None, None]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_call_gemini, p): i for i, p in enumerate(prompts_list)}
        for future in futures:
            idx = futures[future]
            try:
                text = future.result()
                if text and len(text) > 5:
                    patterns[idx] = text[:280]
            except Exception as e:
                print(f"[DEBUG] Future error: {e}")
    result = [p for p in patterns if p]
    posts = result if result else [topic]
    return {"prompts": posts, "labels": posts}

def _fetch_rss(url: str) -> list:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15)
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
