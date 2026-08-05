#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KDP書籍 X投稿スクリプト（CSVベース）
X投稿管理.csvから未投稿の投稿を1件取得し、Xへ投稿する。

使用法:
  dry-run:          python post_kdp_from_csv.py --post-id 01_1 --dry-run
  指定ID実投稿:     python post_kdp_from_csv.py --post-id 01_1 --execute
  次件自動:         python post_kdp_from_csv.py --next --execute
  ラウンドロビン:   python post_kdp_from_csv.py --next-round-robin --execute

--execute がない限り絶対にXへ投稿しない。
"""
import os, sys, json, csv, time, shutil, argparse
from pathlib import Path
from datetime import datetime, date
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv
import traceback # 追加

# ── パス設定 ──
REPO_DIR = Path(__file__).resolve().parent
CRED_PATH = REPO_DIR / ".env.pr"
CSV_PATH = Path(r"C:\Users\htate\Documents\キンドル出版_原稿\10冊制作\X自動投稿\X投稿管理.csv")
XLSX_PATH = Path(r"C:\Users\htate\Documents\キンドル出版_原稿\10冊制作\X自動投稿\X投稿一覧.xlsx")
LOG_DIR = REPO_DIR / "pr_post_logs"

FIELD_NAMES = [
    "book_num", "book_title", "post_index", "pattern_id", "pattern_name",
    "variation", "post_text", "char_count", "generated_at",
    "asin", "amazon_url",
    "status", "scheduled_at", "posted_at", "x_post_id",
    "error_message", "retry_count", "last_updated_at",
]

# ── 認証読み込み ──
def load_credentials():
    """OAuth1認証情報を.env.prから読み込む"""
    if not CRED_PATH.exists():
        raise FileNotFoundError(f"認証ファイルが見つかりません: {CRED_PATH}")
    creds = {}
    with open(CRED_PATH, 'r', encoding='utf-8-sig') as f: # 修正
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                creds[k.strip()] = v.strip().strip('"').strip("'")
    required = ['X_CONSUMER_KEY', 'X_CONSUMER_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']
    for k in required:
        if not creds.get(k):
            raise ValueError(f"認証情報不足: {k} が.env.prにありません")
    return creds

# ── CSV操作 ──
def read_csv():
    """CSVを読み込む"""
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def write_csv(rows):
    """安全にCSVを書き込む（一時ファイル経由）"""
    tmp = CSV_PATH.with_suffix(".csv.tmp")
    with open(tmp, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES, extrasaction='ignore')
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in FIELD_NAMES})
    shutil.move(str(tmp), str(CSV_PATH))

def sync_excel(rows):
    """CSV内容をExcelに同期する"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
        wb = Workbook()
        ws = wb.active
        ws.title = "X投稿一覧"
        hdrs = ["書籍番号","書籍名","投稿No","パターン","バリエーション",
                "投稿本文","文字数","ASIN","Amazon販売URL",
                "状態","予定日時","投稿日時","X投稿ID","エラー","再試行","更新日時"]
        hfill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        hfont = Font(name="游ゴシック", bold=True, color="FFFFFF", size=10)
        tb = Border(left=Side(style='thin'),right=Side(style='thin'),
                    top=Side(style='thin'),bottom=Side(style='thin'))
        for col, h in enumerate(hdrs, 1):
            c = ws.cell(row=1, column=col, value=h)
            c.fill = hfill; c.font = hfont
            c.alignment = Alignment(horizontal='center', vertical='center'); c.border = tb
        rows_sorted = sorted(rows, key=lambda r: (int(r['book_num']), int(r['post_index'])))
        bfont = Font(name="游ゴシック", size=9)
        for i, r in enumerate(rows_sorted, 2):
            vals = [r.get("book_num",""), r.get("book_title",""), r.get("post_index",""),
                    r.get("pattern_name",""), r.get("variation",""), r.get("post_text",""),
                    r.get("char_count",""), r.get("asin",""), r.get("amazon_url",""),
                    r.get("status",""), r.get("scheduled_at",""), r.get("posted_at",""),
                    r.get("x_post_id",""), r.get("error_message",""), r.get("retry_count",""),
                    r.get("last_updated_at","")]
            for col, val in enumerate(vals, 1):
                c = ws.cell(row=i, column=col, value=val)
                c.font = bfont; c.border = tb
                if col == 6: c.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        for col, w in enumerate([10,50,8,20,12,60,8,14,38,8,18,18,22,25,5,18], 1):
            ws.column_dimensions[chr(64+col) if col<=26 else 'A'].width = w
        wb.save(XLSX_PATH)
# ── 投稿本文組み立て ──
def assemble_post_text(row):
    """投稿本文にAmazon URLを追加する"""
    text = row['post_text'].strip()
    url = row.get('amazon_url', '').strip()
    if url and url not in text:
        remaining = 280 - len(text) - len(url) - 1
        if remaining >= 0:
            text = text + "\n" + url
        else:
            print(f"[WARN] URLを含めると{len(text)+len(url)+1}文字になるため、280文字を超えます")
    return text[:280]

# ── X投稿 ──
def post_to_x(text, credentials):
    """OAuth 1.0a認証を使用してXへ投稿する"""
    auth = OAuth1(
        credentials['X_CONSUMER_KEY'],
        credentials['X_CONSUMER_SECRET'],
        credentials['X_ACCESS_TOKEN'],
        credentials['X_ACCESS_TOKEN_SECRET'],
    )
    body = {"text": text[:280]}
    r = requests.post("https://api.twitter.com/2/tweets", json=body, auth=auth, timeout=30)
    if r.status_code == 201:
        data = r.json()['data']
        return True, data['id'], f"https://x.com/i/web/status/{data['id']}"
    return False, "", r.text[:200]

# ── 重複チェック ──
def find_duplicates(rows, target_row):
    """同じ投稿本文がすでに投稿済みでないか確認する"""
    target_text = target_row['post_text'][:80]
    target_id = f"{target_row['book_num']}_{target_row['post_index']}"
    for r in rows:
        if f"{r['book_num']}_{r['post_index']}" == target_id:
            continue
        if r.get('status') == '投稿済み' and r['post_text'][:80] == target_text:
            return True, f"{r['book_num']}_{r['post_index']}"
    return False, ""

# ── ログ ──
def log_result(post_id, status, detail=""):
    """投稿結果をログファイルへ記録する"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{today}.log"
    ts = datetime.now().isoformat()
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {post_id} {status} {detail}\n")

# ── ラウンドロビン選択 ──
def round_robin_select(rows):
    """
    ラウンドロビン方式で次の1件を選択。
    1. 最後に投稿された書籍番号を確認
    2. 次の書籍番号（20→01へ循環）を選択
    3. その書籍の未投稿から最小post_indexを1件選択
    4. 同日に同じ書籍を投稿しない
    5. 戻り値: (target_row, rows) または未投稿なしの場合は (None, rows)
    """
    today_str = date.today().isoformat()
    all_book_nums = sorted(set(r['book_num'] for r in rows), key=lambda x: int(x))

    # 投稿済みの行を posted_at 降順で取得
    posted = [r for r in rows if r.get('status') == '投稿済み' and r.get('posted_at')]
    if posted:
        posted.sort(key=lambda r: r['posted_at'], reverse=True)
        last_book = posted[0]['book_num']
    else:
        # 未投稿のみの場合: 書籍01から開始
        last_book = "00"

    # 次の書籍番号を決定（最大20冊分ループ）
    current_idx = -1
    for i, bn in enumerate(all_book_nums):
        if bn == last_book:
            current_idx = i
            break
    if current_idx == -1:
        current_idx = 0  # 見つからなければ01から

    max_attempts = len(all_book_nums)
    for attempt in range(max_attempts):
        next_idx = (current_idx + 1 + attempt) % len(all_book_nums)
        next_book = all_book_nums[next_idx]

        # 同日チェック: この書籍が今日すでに投稿済みか
        same_day_posted = False
        for r in rows:
            if r['book_num'] == next_book and r.get('status') == '投稿済み' and r.get('posted_at', '').startswith(today_str):
                same_day_posted = True
                break
        if same_day_posted:
            continue

        # この書籍の未投稿を取得（retry_count < 2 のみ）
        candidates = [
            r for r in rows
            if r['book_num'] == next_book
            and r.get('status') == '未投稿'
            and int(r.get('retry_count', 0)) < 2
            and int(r.get('char_count', 999)) <= 280
        ]
        if not candidates:
            continue

        # post_index の昇順でソートして先頭を選択
        candidates.sort(key=lambda r: int(r['post_index']))
        target = candidates[0]
        return target, rows

    return None, rows

# ── メイン ──
def main():
    parser = argparse.ArgumentParser(description="KDP CSV X投稿")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--post-id", help="投稿ID (例: 01_1)")
    group.add_argument("--next", action="store_true", help="次の未投稿を自動選択")
    group.add_argument("--next-round-robin", action="store_true", dest="next_round_robin",
                       help="ラウンドロビン方式で次の書籍の未投稿を選択")
    parser.add_argument("--dry-run", action="store_true", help="実投稿せず確認のみ")
    parser.add_argument("--execute", action="store_true", help="実際にXへ投稿する")
    args = parser.parse_args()

    if not args.execute and not args.dry_run:
        print("ERROR: --dry-run または --execute を指定してください")
        sys.exit(1)
    if args.execute and args.dry_run:
        print("ERROR: --dry-run と --execute は同時に指定できません")
        sys.exit(1)

    # CSV読み込み
    rows = read_csv()
    if args.post_id:
        target = None
        for r in rows:
            pid = f"{r['book_num']}_{r['post_index']}"
            if pid == args.post_id:
                target = r
                break
        if not target:
            print(f"ERROR: 投稿ID {args.post_id} が見つかりません")
            sys.exit(1)
    elif args.next_round_robin:
        target, rows = round_robin_select(rows)
        if not target:
            print("INFO: 未投稿の投稿がありません（ラウンドロビン）")
            sys.exit(0)
    else:  # --next
        targets = [r for r in rows if r.get('status') == '未投稿']
        if not targets:
            print("INFO: 未投稿の投稿がありません")
            sys.exit(0)
        target = targets[0]

    pid = f"{target['book_num']}_{target['post_index']}"
    now = datetime.now().isoformat()

    # ── 事前チェック ──
    print(f"=== 投稿チェック: {pid} ===")
    print(f"書籍: {target['book_title'][:60]}...")
    print(f"パターン: {target['pattern_name']}")

    # status
    if target.get('status') == '投稿済み':
        print(f"SKIP: 既に投稿済みです (posted_at={target.get('posted_at','')})")
        sys.exit(0)

    # retry_count
    retry = int(target.get('retry_count', 0))
    if retry >= 2:
        print(f"SKIP: retry_count={retry} のため再投稿しません")
        sys.exit(0)

    # 文字数
    if int(target['char_count']) > 280:
        print(f"SKIP: 文字数超過 ({target['char_count']} > 280)")
        sys.exit(0)

    # 重複
    is_dup, dup_id = find_duplicates(rows, target)
    if is_dup:
        print(f"SKIP: 投稿 {dup_id} と本文が重複しています")
        sys.exit(0)

    # 最終投稿文
    final_text = assemble_post_text(target)
    print(f"最終文字数: {len(final_text)}字")
    print(f"
投稿本文:")
    print(f"---")
    print(final_text)
    print(f"---")

    # ASIN/URL
    print(f"ASIN: {target.get('asin','N/A')}")
    print(f"URL: {target.get('amazon_url','N/A')}")

    if args.dry_run:
        print(f"
[OK] DRY-RUN 完了")
        print(f"   状態: 未投稿のまま")
        print(f"   CSV: 未更新")
        print(f"   X実投稿: 未実施")
        print(f"   --execute で実投稿可能")
        return

    # ── 実投稿 ──
    print(f"
[POST] Xへ投稿中...")
    try:
        creds = load_credentials()
        success, x_id, detail = post_to_x(final_text, creds)

        if success:
            target['status'] = '投稿済み'
            target['posted_at'] = now
            target['x_post_id'] = x_id
            target['error_message'] = ''
            target['last_updated_at'] = now
            write_csv(rows)
            sync_excel(rows)
            log_result(pid, "OK", f"x_id={x_id}")
            print(f"[OK] 投稿成功: {detail}")
            print(f"   X投稿ID: {x_id}")
            print(f"   CSV/Excel: 更新済み")
        else:
            target['status'] = 'エラー'
            target['error_message'] = detail[:200]
            target['retry_count'] = str(retry + 1)
            target['last_updated_at'] = now
            write_csv(rows)
            sync_excel(rows)
            log_result(pid, "ERROR", detail[:100])
            print(f"[NG] 投稿失敗: {detail[:200]}")
            print(f"   retry_count: {retry + 1}")
            sys.exit(1) # 追加
    except Exception as e:
        target['status'] = 'エラー'
        target['error_message'] = str(e)[:200]
        target['retry_count'] = str(retry + 1)
        target['last_updated_at'] = now
        write_csv(rows)
        sync_excel(rows)
        log_result(pid, "ERROR", str(e)[:100])
        print(f"[NG] エラー: {e}")
        traceback.print_exc() # 追加
        sys.exit(1) # 追加

if __name__ == "__main__":
    main()
