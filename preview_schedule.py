# -*- coding: utf-8 -*-
"""今後N日間の投稿予定を表示する"""
import json, re, sys
from datetime import date, timedelta

BOOKS_JSON = r'C:\Users\htate\pr_meeting\bep-post-generator-repo\books_kanou.json'
with open(BOOKS_JSON, 'r', encoding='utf-8') as f:
    BOOKS = json.load(f)

POST_EPOCH = date(2026, 5, 29)
DAILY_SLOTS = 3
POST_TYPES = 10
BOOKS_COUNT = len(BOOKS)
TOTAL_SLOTS = POST_TYPES * BOOKS_COUNT
ASIN_RE = re.compile(r'^[A-Z0-9]{10}$')

def assign(day_offset, slot):
    total_slot = (day_offset * DAILY_SLOTS + slot) % TOTAL_SLOTS
    book_idx = total_slot % BOOKS_COUNT
    type_idx = total_slot // BOOKS_COUNT
    return BOOKS[book_idx], type_idx, book_idx

def main(days=14):
    today = date.today()
    start = max(0, (today - POST_EPOCH).days)
    print(f'書籍数: {BOOKS_COUNT} / タイプ数: {POST_TYPES} / サイクル: {TOTAL_SLOTS//DAILY_SLOTS}日')
    print(f'今日: {today}\n')
    print('--- 予定表（☆=ASIN未設定） ---')
    for d in range(start, start+days):
        day = POST_EPOCH + timedelta(days=d)
        labels = ['8:00', '11:50', '20:30']
        out = []
        for s in range(DAILY_SLOTS):
            book, typ, idx = assign(d, s)
            ok = bool(ASIN_RE.match(str(book.get('asin',''))))
            out.append(f"{labels[s]} {book['title'][:22]}(タイプ{typ}){' ☆' if not ok else ''}")
        print(f'{day}')
        for o in out:
            print('  '+o)

if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    main(days)
