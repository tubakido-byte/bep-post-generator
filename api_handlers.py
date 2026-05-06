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

def generate_posts(topic: str) -> list:
    """Generate 3 patterns using Gemini API with JSON output"""
    prompt = f"""以下のテキストを元に、X（Twitter）投稿用の文章を3パターン作成してください。

元のテキスト：
{topic}

ルール：
- pattern1：感情・共感を前面に出した文体（280文字以内）
- pattern2：客観的な事実と分析の文体（280文字以内）
- pattern3：問いかけ・対話を促す文体（280文字以内）
- 各パターンは全く異なる表現で書く"""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "pattern1": {"type": "string"},
                        "pattern2": {"type": "string"},
                        "pattern3": {"type": "string"}
                    },
                    "required": ["pattern1", "pattern2", "pattern3"]
                }
            }
        }
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result:
                import json
                text = result['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(text)
                patterns = [
                    data.get('pattern1', ''),
                    data.get('pattern2', ''),
                    data.get('pattern3', '')
                ]
                patterns = [p[:280] for p in patterns if p and len(p) > 5]
                if len(patterns) >= 1:
                    return patterns
    except Exception as e:
        print(f"[DEBUG] Generate error: {str(e)}")
    return [topic]

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
