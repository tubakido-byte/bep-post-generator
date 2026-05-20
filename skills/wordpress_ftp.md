# skill: wordpress_ftp — WordPress FTP操作ルール

## FTP接続情報
- host: 202.172.26.37
- user: ins
- pass: dpLMWxhYnisy
- WP root: public_html/www.ins-japan.com/

## mu-pluginsへのアップロード（Python）
```python
import ftplib, io
with ftplib.FTP('202.172.26.37') as ftp:
    ftp.login('ins', 'dpLMWxhYnisy')
    with open('local_file.php', 'rb') as f:
        ftp.storbinary('STOR public_html/www.ins-japan.com/wp-content/mu-plugins/file.php', f)
```

## 重要ルール
- WP管理画面ログイン：insjapan119@gmail.com / a228b2229@（adminは無効）
- paramiko(SFTP)は接続不可 → ftplibのFTP(port 21)のみ使用
- mu-pluginsに置いたPHPは自動実行される（要注意）
- 会員レベル：無料=5、有料=5以外
