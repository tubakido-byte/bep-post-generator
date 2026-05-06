#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Handler Functions"""

import requests
from requests_oauthlib import OAuth1
from config import X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, GEMINI_API_KEY, NEWS_SOURCES

def post_to_x(text: str) -> dict:
    """Post text to X using OAuth 1.0a (no expiration)"""
    if not text or len(text) == 0:
        return {"success": False, "error": "テキストが空です"}

    if len(text) > 280:
        text = text[:276] + "..."

    try:
        auth = OAuth1(X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
        print(f"[DEBUG] Posting: {text[:80]}...")
        response = requests.post(
            "https://api.twitter.com/2/tweets",
            json={"text": text},
            auth=auth,
            timeout=30
        )
        print(f"[DEBUG] X API status: {response.status_code}")
        if response.status_code == 201:
            tweet_id = response.json()['data']['id']
            print(f"[DEBUG] Success! Tweet ID: {tweet_id}")
            return {"success": True, "tweet_id": tweet_id}
        else:
            print(f"[DEBUG] X API error: {response.text[:200]}")
            return {"success": False, "error": response.text[:200]}
    except Exception as e:
        print(f"[DEBUG] Post error: {type(e).__name__}: {e}")
        return {"success": False, "error": str(e)}

from concurrent.futures import ThreadPoolExecutor

def _call_gemini(prompt: str) -> str:
    """Single Gemini API call, returns text"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
        print(f"[DEBUG] Gemini status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            print(f"[DEBUG] Gemini text: {text[:100]}")
            return text
        else:
            print(f"[DEBUG] Gemini error body: {response.text[:300]}")
    except Exception as e:
        print(f"[DEBUG] Gemini exception: {type(e).__name__}: {e}")
    return ""

def generate_posts(topic: str) -> list:
    """Generate 3 patterns via parallel Gemini calls"""
    prompts = [
        f"X（Twitter）投稿を1つだけ書いてください。感情・共感を前面に出した文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
        f"X（Twitter）投稿を1つだけ書いてください。客観的な事実と分析の文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
        f"X（Twitter）投稿を1つだけ書いてください。読者への問いかけ・対話を促す文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
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
    print(f"[DEBUG] Total patterns: {len(result)}")
    return result if result else [topic]

def translate_text(text: str) -> str:
    """Translate text to Japanese"""
    if not text or len(text) < 3:
        return text

    try:
        text_short = text[:80]
        prompt = f"Translate to Japanese only: {text_short}"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={"Content-Type": "application/json"},
            timeout=25
        )

        if response.status_code == 200:
            result = response.json()
            translated = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if translated and len(translated) > 2:
                return translated
    except Exception as e:
        print(f"[DEBUG] Translation error: {str(e)}")

    return text

def get_news_articles(source: str) -> list:
    """Fetch news articles from RSS feed"""
    try:
        import xml.etree.ElementTree as ET
        feed_url = NEWS_SOURCES.get(source, list(NEWS_SOURCES.values())[0])
        print(f"[DEBUG] Fetching: {feed_url}")

        resp = requests.get(
            feed_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=15
        )
        print(f"[DEBUG] HTTP {resp.status_code}, {len(resp.content)} bytes")

        root = ET.fromstring(resp.content)
        items = root.findall('.//item')
        print(f"[DEBUG] Found {len(items)} items")

        articles = []
        needs_translation = '産経新聞' not in source

        for item in items[:5]:
            title_el = item.find('title')
            title = (title_el.text or '').strip() if title_el is not None else 'No title'
            link_el = item.find('link')
            link = (link_el.text or '#').strip() if link_el is not None else '#'

            if needs_translation and title:
                title = translate_text(title)

            articles.append({"title": title, "summary": '', "link": link})

        return articles if articles else [{"title": "記事なし", "summary": "RSS に記事が見つかりません", "link": "#"}]

    except Exception as e:
        print(f"[DEBUG] News error: {type(e).__name__}: {e}")
        return [{"title": "テスト記事", "summary": "ニュース取得に失敗しました", "link": "#"}]
