#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API Handler Functions"""

import requests
from config import X_OAUTH2_ACCESS_TOKEN, X_API_ENDPOINT, GEMINI_API_KEY, NEWS_SOURCES

def post_to_x(text: str) -> dict:
    """Post text to X"""
    if not text or len(text) == 0:
        return {"success": False, "error": "テキストが空です"}

    if len(text) > 280:
        text = text[:276] + "..."

    headers = {
        "Authorization": f"Bearer {X_OAUTH2_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        print(f"[DEBUG] Posting text: {text[:80]}...")
        response = requests.post(
            X_API_ENDPOINT,
            headers=headers,
            json={"text": text},
            timeout=30
        )

        print(f"[DEBUG] Response status: {response.status_code}")
        if response.status_code == 201:
            result = response.json()
            tweet_id = result.get('data', {}).get('id', '')
            print(f"[DEBUG] Success! Tweet ID: {tweet_id}")
            return {"success": True, "tweet_id": tweet_id}
        else:
            error_msg = response.json().get('detail', response.text) if response.text else f"HTTP {response.status_code}"
            print(f"[DEBUG] Error: {error_msg}")
            return {"success": False, "error": f"HTTP {response.status_code}: {error_msg}"}
    except Exception as e:
        error_msg = str(e)
        print(f"[DEBUG] Exception: {type(e).__name__}: {error_msg}")
        return {"success": False, "error": error_msg}

def _call_gemini(prompt: str) -> str:
    """Single Gemini API call, returns text"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    if response.status_code == 200:
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text'].strip()
    return ""

def generate_posts(topic: str) -> list:
    """Generate 3 patterns via 3 separate Gemini calls"""
    prompts = [
        f"X（Twitter）投稿を1つだけ書いてください。感情・共感を前面に出した文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
        f"X（Twitter）投稿を1つだけ書いてください。客観的な事実と分析の文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
        f"X（Twitter）投稿を1つだけ書いてください。読者への問いかけ・対話を促す文体。280文字以内。説明不要、投稿文のみ出力。\n元のテキスト：{topic}",
    ]
    patterns = []
    for prompt in prompts:
        try:
            text = _call_gemini(prompt)
            if text and len(text) > 5:
                patterns.append(text[:280])
        except Exception as e:
            print(f"[DEBUG] Generate error: {str(e)}")
    return patterns if patterns else [topic]

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
            timeout=30
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
        import feedparser
        feed_url = NEWS_SOURCES.get(source, list(NEWS_SOURCES.values())[0])
        feedparser.USER_AGENT = "Mozilla/5.0 (compatible; BEPGenerator/1.0)"
        feed = feedparser.parse(feed_url)
        articles = []

        needs_translation = 'NHK' not in source

        for entry in feed.entries[:5]:
            title = entry.get('title', 'No title')
            summary = entry.get('summary', '')[:150]

            if needs_translation:
                title = translate_text(title)

            articles.append({
                "title": title,
                "summary": summary,
                "link": entry.get('link', '#')
            })

        return articles
    except Exception as e:
        print(f"[DEBUG] News fetch error: {str(e)}")
        return [{"title": "テスト記事", "summary": "ニュース取得に失敗しました", "link": "#"}]
