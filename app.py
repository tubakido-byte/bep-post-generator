from flask import Flask, render_template, request, jsonify, redirect, session
import os, requests, uuid, threading, hmac, hashlib, base64, time, sqlite3
from datetime import datetime, date as _date_cls
import pytz
from requests_oauthlib import OAuth1
from api_handlers import post_to_x, generate_posts, generate_images, get_news_articles, health_check, surge_long_post, surge_buzz, surge_self_quote, surge_inspo, surge_profile_check, generate_thread, post_thread_to_x, post_to_threads, STUDIO_KANOU_BOOKS
from config import GEMINI_API_KEY

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'xpost-secret-2024')
THREAD_CRON_SECRET = os.environ.get('THREAD_CRON_SECRET', 'kanou-thread-auto-7am')
_THREAD_EPOCH = _date_cls(2026, 5, 28)
THREADS_APP_ID = os.environ.get('THREADS_APP_ID', '2386770295177388')
THREADS_APP_SECRET = os.environ.get('THREADS_APP_SECRET', '')
THREADS_REDIRECT_URI = os.environ.get('THREADS_REDIRECT_URI', 'https://bep-post-generator.onrender.com/threads/callback')

def _get_today_book():
    idx = max(0, (_date_cls.today() - _THREAD_EPOCH).days) % len(STUDIO_KANOU_BOOKS)
    return idx, STUDIO_KANOU_BOOKS[idx]
PREMIUM_CODE = os.environ.get('PREMIUM_CODE', 'XPOST-PRO-2024')
PREMIUM_CODE_BASIC = os.environ.get('PREMIUM_CODE_BASIC', 'XPOST-BASIC-2024')
SWPM_LAUNCH_SECRET = os.environ.get('SWPM_LAUNCH_SECRET', 'xpost2024-swpm-8a3f-b2c1-d4e5f6')

IMAGE_LIMITS = {0: 0, 2: 30, 6: 100}  # level: 月間上限枚数（回）

def _verify_swpm_token(token: str) -> int:
    """SWPM levelを返す（無効なら-1）"""
    try:
        b64, sig = token.rsplit('.', 1)
        data = base64.b64decode(b64).decode()
        expected = hmac.new(SWPM_LAUNCH_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return -1
        parts = data.split(':')
        if time.time() - int(parts[2]) > 3600:
            return -1
        return int(parts[1])
    except Exception:
        return -1

def _get_swpm_user_id(token: str) -> str:
    try:
        b64, _ = token.rsplit('.', 1)
        data = base64.b64decode(b64).decode()
        return data.split(':')[0]
    except Exception:
        return ''

def _init_db():
    db = sqlite3.connect('/tmp/usage.db')
    db.execute('CREATE TABLE IF NOT EXISTS image_usage (user_id TEXT, ym TEXT, count INTEGER, PRIMARY KEY(user_id, ym))')
    db.commit()
    db.close()

def _get_usage(user_id: str, ym: str) -> int:
    db = sqlite3.connect('/tmp/usage.db')
    row = db.execute('SELECT count FROM image_usage WHERE user_id=? AND ym=?', (user_id, ym)).fetchone()
    db.close()
    return row[0] if row else 0

def _increment_usage(user_id: str, ym: str):
    db = sqlite3.connect('/tmp/usage.db')
    db.execute('INSERT INTO image_usage(user_id,ym,count) VALUES(?,?,1) ON CONFLICT(user_id,ym) DO UPDATE SET count=count+1', (user_id, ym))
    db.commit()
    db.close()

_init_db()
_jst = pytz.timezone('Asia/Tokyo')
scheduled_posts = {}
_timers = {}
image_jobs = {}

def _execute_scheduled_post(job_id, text, image='', credentials=None):
    result = post_to_x(text, image, credentials)
    if job_id in scheduled_posts:
        scheduled_posts[job_id]['status'] = '投稿済み ✅' if result.get('success') else '失敗 ❌'
    _timers.pop(job_id, None)

_oauth_temp = {}  # request_token → request_token_secret (一時保存)

@app.route('/oauth/start')
def oauth_start():
    ck = os.environ.get('X_CONSUMER_KEY', '')
    cs = os.environ.get('X_CONSUMER_SECRET', '')
    if not ck or not cs:
        return 'X_CONSUMER_KEY/SECRET が未設定です', 500
    callback = request.host_url.rstrip('/') + '/oauth/callback'
    auth = OAuth1(ck, cs, callback_uri=callback)
    r = requests.post('https://api.twitter.com/oauth/request_token', auth=auth, timeout=10)
    if r.status_code != 200:
        return f'リクエストトークン取得失敗: {r.text}', 400
    params = dict(p.split('=') for p in r.text.split('&'))
    _oauth_temp[params['oauth_token']] = params['oauth_token_secret']
    return redirect(f"https://api.twitter.com/oauth/authorize?oauth_token={params['oauth_token']}")

@app.route('/oauth/callback')
def oauth_callback():
    oauth_token    = request.args.get('oauth_token', '')
    oauth_verifier = request.args.get('oauth_verifier', '')
    token_secret   = _oauth_temp.pop(oauth_token, None)
    if not token_secret:
        return '認証セッションが無効です。もう一度お試しください', 400
    ck = os.environ.get('X_CONSUMER_KEY', '')
    cs = os.environ.get('X_CONSUMER_SECRET', '')
    auth = OAuth1(ck, cs, oauth_token, token_secret, verifier=oauth_verifier)
    r = requests.post('https://api.twitter.com/oauth/access_token', auth=auth, timeout=10)
    if r.status_code != 200:
        return f'アクセストークン取得失敗: {r.text}', 400
    p = dict(x.split('=') for x in r.text.split('&'))
    at  = p.get('oauth_token', '')
    ats = p.get('oauth_token_secret', '')
    sn  = p.get('screen_name', '')
    return redirect(f'/#oauth-done?at={at}&ats={ats}&sn={sn}')

@app.route('/logout')
def logout():
    return redirect('https://www.ins-japan.com/')

@app.route('/')
def dashboard():
    swpm_level = None
    t = request.args.get('t', '')
    if t:
        lvl = _verify_swpm_token(t)
        if lvl >= 0:
            swpm_level = lvl
            session['swpm_level'] = lvl
            session['user_id'] = _get_swpm_user_id(t)
    return render_template('dashboard.html', swpm_level=swpm_level)

@app.route('/api/health')
def api_health():
    return jsonify(health_check())

@app.route('/api/news')
def api_news():
    source = request.args.get('source', '🌍 Axios')
    try:
        articles = get_news_articles(source)
        return jsonify({'articles': articles})
    except Exception as e:
        return jsonify({'articles': [], 'error': f'ニュース取得失敗: {str(e)[:100]}'})

@app.route('/api/post', methods=['POST'])
def api_post():
    data = request.get_json()
    if not data or not data.get('text', '').strip():
        return jsonify({'success': False, 'error': '投稿テキストが空です'})
    credentials = data.get('credentials')
    return jsonify(post_to_x(data.get('text', ''), data.get('image', ''), credentials))

@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        topic = request.get_json().get('topic', 'X投稿')
        result = generate_posts(topic)
        if not result.get('prompts'):
            return jsonify({'prompts': [], 'error': 'AI生成に失敗しました。しばらく待ってから再試行してください'})
        return jsonify(result)
    except Exception as e:
        msg = 'AI生成がタイムアウトしました。もう一度お試しください' if 'futures' in str(e).lower() or 'timeout' in str(e).lower() else f'生成エラー: {str(e)[:80]}'
        return jsonify({'prompts': [], 'error': msg})

@app.route('/api/debug-image')
def api_debug_image():
    import os
    import re as _re
    key = _re.sub(r'[^a-zA-Z0-9\-_]', '', os.environ.get('OPENAI_API_KEY', ''))
    key_preview = key[:10] + '...' + key[-4:] if len(key) > 14 else f'空({len(key)}文字)'
    try:
        import requests as req
        r = req.post('https://api.openai.com/v1/images/generations',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': 'gpt-image-1', 'prompt': 'a red apple', 'n': 1, 'size': '1024x1024'},
            timeout=120)
        d = r.json()
        if 'data' in d:
            return jsonify({'key': key_preview, 'status': 'OK', 'img_len': len(d['data'][0].get('b64_json',''))})
        return jsonify({'key': key_preview, 'status': 'FAIL', 'error': d.get('error',{}).get('message','')[:200]})
    except Exception as e:
        return jsonify({'key': key_preview, 'status': 'EXCEPTION', 'error': str(e)[:200]})

@app.route('/api/generate-images', methods=['POST'])
def api_generate_images():
    try:
        user_id = session.get('user_id', '')
        level = session.get('swpm_level', 0)
        ym = datetime.now(_jst).strftime('%Y-%m')
        limit = IMAGE_LIMITS.get(level, 0)
        if user_id and limit > 0:
            usage = _get_usage(user_id, ym)
            if usage >= limit:
                return jsonify({'error': f'今月の画像生成上限（{limit}回）に達しました。来月までお待ちください。'})
        prompt = request.get_json().get('prompt', '')
        job_id = str(uuid.uuid4())[:8]
        image_jobs[job_id] = {'status': 'pending'}
        def _run():
            try:
                result = generate_images(prompt)
                image_jobs[job_id] = {'status': 'done', **result}
                if user_id and result.get('images'):
                    _increment_usage(user_id, ym)
            except Exception as e:
                image_jobs[job_id] = {'status': 'error', 'error': str(e)[:100]}
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return jsonify({'job_id': job_id, 'status': 'pending'})
    except Exception as e:
        return jsonify({'error': f'画像生成開始エラー: {str(e)[:100]}'})

@app.route('/api/image-status/<job_id>')
def api_image_status(job_id):
    job = image_jobs.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'error': 'ジョブが見つかりません'})
    return jsonify(job)

@app.route('/api/schedule', methods=['POST'])
def api_schedule():
    data = request.get_json()
    text = data.get('text', '').strip()
    image = data.get('image', '')
    scheduled_time_str = data.get('scheduled_time', '')
    if not text or not scheduled_time_str:
        return jsonify({'success': False, 'error': '投稿テキストまたは日時が未入力です'})
    try:
        dt = None
        for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
            try:
                dt = datetime.strptime(scheduled_time_str, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return jsonify({'success': False, 'error': f'日時フォーマットエラー（受信値: {scheduled_time_str[:30]}）'})
        dt = _jst.localize(dt)
        delay = (dt - datetime.now(_jst)).total_seconds()
        if delay <= 0:
            return jsonify({'success': False, 'error': '過去の日時は指定できません'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'日時解析エラー: {str(e)[:60]}'})
    credentials = data.get('credentials')
    job_id = str(uuid.uuid4())[:8]
    timer = threading.Timer(delay, _execute_scheduled_post, args=[job_id, text, image, credentials])
    timer.daemon = True
    timer.start()
    _timers[job_id] = timer
    scheduled_posts[job_id] = {
        'text': text[:50] + '…' if len(text) > 50 else text,
        'full_text': text,
        'scheduled_time': scheduled_time_str,
        'status': '待機中 ⏳'
    }
    return jsonify({'success': True, 'job_id': job_id})

@app.route('/api/scheduled-posts')
def api_scheduled_posts():
    return jsonify({'posts': [{'id': k, **v} for k, v in scheduled_posts.items()]})

@app.route('/api/cancel-schedule/<job_id>', methods=['POST'])
def api_cancel_schedule(job_id):
    timer = _timers.pop(job_id, None)
    if timer:
        timer.cancel()
    if job_id in scheduled_posts:
        scheduled_posts[job_id]['status'] = 'キャンセル ❌'
    return jsonify({'success': True})

@app.route('/api/verify-premium', methods=['POST'])
def api_verify_premium():
    code = request.get_json().get('code', '').strip().upper()
    if code == PREMIUM_CODE.upper():
        return jsonify({'valid': True, 'plan': 'premium'})
    if code == PREMIUM_CODE_BASIC.upper():
        return jsonify({'valid': True, 'plan': 'basic'})
    return jsonify({'valid': False})

@app.route('/api/surge/long-post', methods=['POST'])
def api_surge_long_post():
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        context = data.get('context', '')
        if not topic:
            return jsonify({'post': '', 'error': 'ネタを入力してください'})
        return jsonify(surge_long_post(topic, context))
    except Exception as e:
        return jsonify({'post': '', 'error': str(e)[:100]})

@app.route('/api/surge/buzz', methods=['POST'])
def api_surge_buzz():
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        style = data.get('style', 'list')
        context = data.get('context', '')
        if not topic:
            return jsonify({'post': '', 'error': 'ネタを入力してください'})
        return jsonify(surge_buzz(topic, style, context))
    except Exception as e:
        return jsonify({'post': '', 'error': str(e)[:100]})

@app.route('/api/surge/self-quote', methods=['POST'])
def api_surge_self_quote():
    try:
        data = request.get_json()
        past_post = data.get('past_post', '').strip()
        context = data.get('context', '')
        if not past_post:
            return jsonify({'post': '', 'error': '過去の投稿を入力してください'})
        return jsonify(surge_self_quote(past_post, context))
    except Exception as e:
        return jsonify({'post': '', 'error': str(e)[:100]})

@app.route('/api/surge/inspo', methods=['POST'])
def api_surge_inspo():
    try:
        data = request.get_json()
        theme = data.get('theme', '')
        return jsonify(surge_inspo(theme))
    except Exception as e:
        return jsonify({'topics': '', 'error': str(e)[:100]})

@app.route('/api/surge/profile-check', methods=['POST'])
def api_surge_profile_check():
    try:
        data = request.get_json()
        profile = data.get('profile', '').strip()
        pinned_post = data.get('pinned_post', '')
        context = data.get('context', '')
        if not profile:
            return jsonify({'diagnosis': '', 'error': 'プロフィールを入力してください'})
        return jsonify(surge_profile_check(profile, pinned_post, context))
    except Exception as e:
        return jsonify({'diagnosis': '', 'error': str(e)[:100]})

@app.route('/threads/auth')
def threads_auth():
    auth_url = (
        f"https://threads.net/oauth/authorize"
        f"?client_id={THREADS_APP_ID}"
        f"&redirect_uri={THREADS_REDIRECT_URI}"
        f"&scope=threads_basic,threads_content_publish"
        f"&response_type=code"
    )
    return redirect(auth_url)

@app.route('/threads/callback')
def threads_callback():
    all_params = dict(request.args)
    code = request.args.get('code', '')
    error = request.args.get('error', '')
    error_reason = request.args.get('error_reason', '')
    error_description = request.args.get('error_description', '')
    if error:
        return f'<h2>認証エラー: {error}</h2><p>{error_reason}: {error_description}</p><p>全パラメータ: {all_params}</p>', 400
    if not code:
        return f'<h2>認証コードが見つかりません</h2><p>受信パラメータ: {all_params}</p>', 400
    r = requests.post('https://graph.threads.net/oauth/access_token', data={
        'client_id': THREADS_APP_ID,
        'client_secret': THREADS_APP_SECRET,
        'grant_type': 'authorization_code',
        'redirect_uri': THREADS_REDIRECT_URI,
        'code': code
    }, timeout=30)
    if r.status_code != 200:
        return f'<h2>トークン取得失敗: {r.text[:200]}</h2>', 400
    data = r.json()
    short_token = data.get('access_token', '')
    user_id = str(data.get('user_id', ''))
    r2 = requests.get('https://graph.threads.net/access_token', params={
        'grant_type': 'th_exchange_token',
        'client_secret': THREADS_APP_SECRET,
        'access_token': short_token
    }, timeout=30)
    long_token = r2.json().get('access_token', short_token) if r2.status_code == 200 else short_token
    return f'''<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:800px;margin:40px auto;padding:20px;">
    <h2>✅ Threads認証完了！</h2>
    <p>以下の2つをRenderの環境変数に設定してください。</p>
    <p><strong>THREADS_USER_ID:</strong></p>
    <input type="text" value="{user_id}" readonly style="width:100%;padding:8px;font-size:14px;" onclick="this.select()">
    <p><strong>THREADS_ACCESS_TOKEN:</strong></p>
    <textarea rows="4" readonly style="width:100%;padding:8px;font-size:12px;" onclick="this.select();">{long_token}</textarea>
    <p style="color:red;">⚠️ このページを閉じる前に必ず保存してください。</p>
    </body></html>'''

@app.route('/api/auto-thread/status')
def api_auto_thread_status():
    idx, book = _get_today_book()
    next_idx = (idx + 1) % len(STUDIO_KANOU_BOOKS)
    return jsonify({
        'today_index': idx,
        'today_book': book['title'],
        'next_book': STUDIO_KANOU_BOOKS[next_idx]['title'],
        'total_books': len(STUDIO_KANOU_BOOKS)
    })

@app.route('/api/auto-thread/run')
def api_auto_thread_run():
    secret = request.args.get('secret', '')
    if secret != THREAD_CRON_SECRET:
        return jsonify({'error': '認証エラー'}), 403
    idx, book = _get_today_book()
    amazon_url = f"https://www.amazon.co.jp/dp/{book['asin']}"
    thread_result = generate_thread(book['title'], amazon_url)
    if not thread_result.get('tweets'):
        return jsonify({'success': False, 'error': 'スレッド生成失敗', 'book': book['title']})
    post_result = post_thread_to_x(thread_result['tweets'])
    return jsonify({
        'success': post_result.get('success', False),
        'book': book['title'],
        'book_index': idx,
        'posted': post_result.get('posted', 0),
        'total': post_result.get('total', 0),
        'thread_url': post_result.get('thread_url', '')
    })

@app.route('/api/auto-threads/run')
def api_auto_threads_run():
    secret = request.args.get('secret', '')
    if secret != THREAD_CRON_SECRET:
        return jsonify({'error': '認証エラー'}), 403
    idx, book = _get_today_book()
    amazon_url = f"https://www.amazon.co.jp/dp/{book['asin']}"
    thread_result = generate_thread(book['title'], amazon_url)
    if not thread_result.get('tweets'):
        return jsonify({'success': False, 'error': 'スレッド生成失敗'})
    post_text = '\n\n'.join(thread_result['tweets'][:2])[:500]
    result = post_to_threads(post_text)
    return jsonify({'success': result.get('success'), 'book': book['title'], 'error': result.get('error', '')})

@app.route('/api/thread/books')
def api_thread_books():
    return jsonify({'books': STUDIO_KANOU_BOOKS})

@app.route('/api/generate-thread', methods=['POST'])
def api_generate_thread():
    try:
        data = request.get_json()
        book_title = data.get('book_title', '').strip()
        amazon_url = data.get('amazon_url', '').strip()
        if not book_title:
            return jsonify({'tweets': [], 'error': '書籍タイトルが未入力です'})
        return jsonify(generate_thread(book_title, amazon_url))
    except Exception as e:
        return jsonify({'tweets': [], 'error': str(e)[:100]})

@app.route('/api/post-thread', methods=['POST'])
def api_post_thread():
    try:
        data = request.get_json()
        tweets = data.get('tweets', [])
        credentials = data.get('credentials')
        if not tweets:
            return jsonify({'success': False, 'error': 'ツイートが空です'})
        return jsonify(post_thread_to_x(tweets, credentials))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:100]})

@app.route('/manual/free')
def manual_free():
    return render_template('manual_free.html')

@app.route('/manual/paid')
def manual_paid():
    return render_template('manual_paid.html')

def _keep_alive():
    self_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://bep-post-generator.onrender.com')
    while True:
        time.sleep(600)
        try:
            requests.get(f"{self_url}/api/auto-thread/status", timeout=10)
        except Exception:
            pass

_keep_alive_thread = threading.Thread(target=_keep_alive, daemon=True)
_keep_alive_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
