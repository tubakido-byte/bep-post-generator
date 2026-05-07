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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
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

def generate_images(prompt: str) -> list:
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(_generate_one_image, [prompt] * 3))
    return [r for r in results if r]

def generate_posts(topic: str) -> list:
    system = """# Role
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
画像生成の際は、常に以下の構成でプロンプトを構築すること。

- [Subject]: 被写体とアクションの詳細
- [Environment]: 背景と雰囲気（ムード）
- [Lighting]: 光の演出（ゴールデンアワー、ネオン、自然光など）
- [Technical Tags]: (8k, masterpiece, highly detailed, cinematic, photorealistic/anime style)

# Constraint
- 「AI生成特有の不自然さ（指の数や崩れ）」を回避するキーワード（High quality, detailed anatomy等）を必ず含めること。
- ターゲットユーザーが「壁紙にしたくなる」「保存して眺めたくなる」ような高い美的センスを追求すること。"""

    prompts = [
        f"{system}\n\nテーマ：{topic}\n\nパターン1（フォトリアリスティック風）の画像生成プロンプトを英語で1つだけ出力してください。プロンプト文のみ出力。",
        f"{system}\n\nテーマ：{topic}\n\nパターン2（アニメ・イラスト風）の画像生成プロンプトを英語で1つだけ出力してください。プロンプト文のみ出力。",
        f"{system}\n\nテーマ：{topic}\n\nパターン3（ムード重視・映画的）の画像生成プロンプトを英語で1つだけ出力してください。プロンプト文のみ出力。",
    ]
    patterns = [None, None, None]
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_call_gemini, p): i for i, p in enumerate(prompts)}
        for future in futures:
            idx = futures[future]
            try:
                text = future.result()
                if text and len(text) > 5:
                    patterns[idx] = text[:280]
            except Exception as e:
                print(f"[DEBUG] Future error: {e}")
    result = [p for p in patterns if p]
    return result if result else [topic]

def get_news_articles(source: str) -> list:
    try:
        feed_url = NEWS_SOURCES.get(source, list(NEWS_SOURCES.values())[0])
        resp = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15)
        root = ET.fromstring(resp.content)
        raw = []
        for item in root.findall('.//item')[:5]:
            title_el = item.find('title')
            link_el = item.find('link')
            title = (title_el.text or '').strip() if title_el is not None else 'No title'
            link = (link_el.text or link_el.get('href', '#') or '#').strip() if link_el is not None else '#'
            if ' - ' in title:
                title = title.rsplit(' - ', 1)[0].strip()
            raw.append({"title": title, "link": link})

        if '産経新聞' not in source and raw:
            numbered = "\n".join([f"{i+1}. {a['title']}" for i, a in enumerate(raw)])
            prompt = f"次の英語タイトルを日本語に翻訳してください。番号付きリストのみ出力。\n{numbered}"
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                r2 = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
                if r2.status_code == 200:
                    lines = r2.json()['candidates'][0]['content']['parts'][0]['text'].strip().split('\n')
                    parsed = [l.split('. ', 1)[-1].strip() for l in lines if l.strip() and l.strip()[0].isdigit()]
                    if len(parsed) == len(raw):
                        return [{"title": t, "summary": '', "link": a['link']} for t, a in zip(parsed, raw)]
            except Exception as e:
                print(f"[DEBUG] Translate error: {e}")

        return [{"title": a['title'], "summary": '', "link": a['link']} for a in raw] or \
               [{"title": "記事なし", "summary": "RSS に記事が見つかりません", "link": "#"}]
    except Exception as e:
        print(f"[DEBUG] News error: {e}")
        return [{"title": "テスト記事", "summary": "ニュース取得に失敗しました", "link": "#"}]
