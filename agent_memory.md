# agent_memory.md — BEP Post Generator プロジェクト記憶

最終更新：2026-05-20

---

## 技術スタック
- Flask 3.0.0 / Python 3.x
- Gunicorn（本番）/ threading.Timer（予約投稿）
- Gemini API（gemini-2.5-flash）/ X API OAuth1
- デプロイ先：Render（無料プラン）
- GitHub：tubakido-byte/bep-post-generator（mainブランチ）

## プロジェクト構成
```
bep-deploy/
├── app.py                  # Flaskルート定義
├── api_handlers.py         # Gemini・X API処理
├── config.py               # 環境変数読み込み
├── requirements.txt
├── templates/
│   ├── dashboard.html      # メインUI（4タブ）
│   ├── manual_free.html    # 無料会員マニュアル
│   └── manual_paid.html    # 有料会員マニュアル
├── static/
│   ├── app.js              # フロントエンドJS
│   └── styles.css
├── wordpress_plugins/
│   └── premium_email_hook.php  # WP mu-plugin
└── agent_memory.md         # このファイル
```

## 確定済みアーキテクチャ決定事項

### 予約投稿
- **threading.Timer** を使用（APSchedulerは永久禁止）
- 理由：gunicornマルチワーカーとの非互換性でサーバークラッシュ

### 認証方式
- Flaskログイン画面は廃止済み
- WordPressのSimple Membershipで入口管理
- マルチアカウント認証情報はlocalStorageに保存（サーバー側は保持しない）

### プレミアム認証
- `/api/verify-premium` でサーバー側のPREMIUM_CODE環境変数と照合
- Render環境変数：`PREMIUM_CODE=XPOST-PRO-2024`

### SURGE機能（旧XBOOST）
- 5つのGemini APIエンドポイント（`/api/surge/*`）
- コンテキスト（魂）設定はlocalStorageのみ
- 投稿カレンダーはlocalStorageのみ

---

## 解決済み重要バグ

| バグ | 原因 | 解決策 |
|---|---|---|
| 500エラー（起動不能） | `templates/login.html`がGitにない | `git add`してコミット |
| 予約投稿が即時投稿になる | スケジュールUIが投稿フローと切り離されていた | datetime-localを各投稿セクションに統合 |
| 3タブ目が開かない | switchTabが2タブしか対応していなかった | `btn`を引数に渡す方式に変更 |
| APScheduler起動エラー | gunicornと非互換 | threading.Timerに全面置き換え |

---

## 環境変数（Render設定済み）
- `GEMINI_API_KEY`
- `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET`
- `X_CONSUMER_KEY` / `X_CONSUMER_SECRET`
- `PREMIUM_CODE`
- `SECRET_KEY`

---

## WordPressとの連携
- 本番URL：https://www.ins-japan.com/x-post-generator/
- mu-plugins：`premium_email_hook.php`（会員登録時の自動メール）
- 無料会員level：5 / 有料会員：level≠5
- WP管理画面ログイン：insjapan119@gmail.com / a228b2229@

---

## 次のタスク
- LP最終仕上げ・販売開始準備（post 3665）
