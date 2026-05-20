# skill: deploy — デプロイ手順

## Renderへのデプロイ
1. ローカルで変更を確認
2. `python -c "from app import app; print('OK')"` でimportテスト
3. `git add <ファイル>` → `git commit -m "メッセージ"` → `git push origin main`
4. Renderが自動デプロイ開始（2〜3分）
5. `https://bep-post-generator.onrender.com` で動作確認

## 絶対禁止事項
- APSchedulerの使用（gunicornと非互換）
- templates/以下のファイルをGit管理外にする
- 環境変数をコードにハードコード

## テンプレートファイルの追加時
必ずGitに追加してからpush（未コミットだと500エラー）:
```
git add templates/新ファイル.html
```
