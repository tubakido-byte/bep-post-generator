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
    """Generate 3 patterns using Gemini API (staged approach)"""
    prompt = f"""## タスク：テキストの要素抽出と再構成

以下のテキストを読んでください：
【元のテキスト】
{topic}

## ステップ1：重要な要素を抽出してください
- 主な事実は何か
- 主張・意見は何か
- データ・証拠は何か

## ステップ2：3つの異なる「角度」から書き直してください

【パターン①】強い意見・主張を前面に：中心的な主張を強調
→ 元のテキストと全く異なる言葉で、意見を強調するアプローチで書く

【パターン②】バランス・多角的視点：複数の視点を含める
→ 元のテキストと全く異なる言葉で、複数の視点を含めて書く

【パターン③】事実と分析：冷徹に何が起きているかを述べる
→ 元のテキストと全く異なる言葉で、客観的アプローチで書く

## 出力ルール
- 各投稿は280文字以内
- 元のテキストの言い回しは使わない
- 同じ意味だが、全く異なる表現で書く
- 各パターンは独立した投稿として機能する

## 出力フォーマット
【パターン①】[ここに生成テキストを挿入]
【パターン②】[ここに生成テキストを挿入]
【パターン③】[ここに生成テキストを挿入]"""

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result:
                text = result['candidates'][0]['content']['parts'][0]['text']
                patterns = []
                markers = ["【パターン①】", "【パターン②】", "【パターン③】"]
                for marker in markers:
                    if marker in text:
                        start = text.find(marker) + len(marker)
                        next_marker_pos = -1
                        for next_m in markers:
                            pos = text.find(next_m, start)
                            if pos > -1 and (next_marker_pos == -1 or pos < next_marker_pos):
                                next_marker_pos = pos
                        end = next_marker_pos if next_marker_pos > -1 else len(text)
                        pattern_text = text[start:end].strip()
                        if pattern_text and len(pattern_text) > 5:
                            patterns.append(pattern_text)
                return patterns if len(patterns) > 0 else [topic]
    except Exception as e:
        import traceback
        traceback.print_exc()
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
