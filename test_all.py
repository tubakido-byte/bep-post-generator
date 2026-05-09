#!/usr/bin/env python3
"""デプロイ前の全機能チェックスクリプト"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from api_handlers import health_check, _call_gemini, get_news_articles, generate_posts

PASS = "✅ OK"
FAIL = "❌ NG"

def test(name, fn):
    try:
        result = fn()
        status = PASS if result else FAIL
        print(f"{status}  {name}: {result if not result or len(str(result)) < 80 else str(result)[:80]+'...'}")
        return bool(result)
    except Exception as e:
        print(f"{FAIL}  {name}: {e}")
        return False

print("=" * 50)
print("X Post Generator — 全機能テスト")
print("=" * 50)

results = []

# 1. 環境変数チェック
h = health_check()
results.append(h['overall'] == 'OK')
print(f"{'✅' if h['overall']=='OK' else '❌'}  環境変数: {h['env_vars']}")
print(f"{'✅' if h['gemini']=='OK' else '❌'}  Gemini API: {h['gemini']}")
print(f"{'✅' if h['x_api']=='OK' else '❌'}  X API設定: {h['x_api']}")

# 2. Gemini テキスト生成
results.append(test("Gemini テキスト生成", lambda: _call_gemini("「こんにちは」を英語で言うと？1語で答えてください")))

# 3. ニュース取得（NHK）
results.append(test("ニュース取得（産経新聞）", lambda: len(get_news_articles("🏛️ 産経新聞")) > 0))

# 4. ニュース取得（Axios）
results.append(test("ニュース取得（Axios）", lambda: len(get_news_articles("🌍 Axios")) > 0))

# 5. 投稿パターン生成
def test_generate():
    r = generate_posts("トランプ大統領が中国を訪問した")
    return len(r.get('prompts', [])) == 3
results.append(test("投稿パターン3種生成", test_generate))

print("=" * 50)
passed = sum(results)
total = len(results)
print(f"結果: {passed}/{total} テスト通過")
if passed == total:
    print("✅ 全テスト通過 — デプロイ可能")
else:
    print("❌ 失敗あり — デプロイ前に修正が必要")
print("=" * 50)
sys.exit(0 if passed == total else 1)
