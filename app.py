from flask import Flask, render_template, request, jsonify, redirect
import os, requests, uuid, threading
from datetime import datetime
import pytz
from api_handlers import post_to_x, generate_posts, generate_images, get_news_articles, health_check, surge_long_post, surge_buzz, surge_self_quote, surge_inspo, surge_profile_check
from config import GEMINI_API_KEY

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'xpost-secret-2024')
PREMIUM_CODE = os.environ.get('PREMIUM_CODE', 'XPOST-PRO-2024')
PREMIUM_CODE_BASIC = os.environ.get('PREMIUM_CODE_BASIC', 'XPOST-BASIC-2024')

_jst = pytz.timezone('Asia/Tokyo')
scheduled_posts = {}
_timers = {}

def _execute_scheduled_post(job_id, text, image='', credentials=None):
    result = post_to_x(text, image, credentials)
    if job_id in scheduled_posts:
        scheduled_posts[job_id]['status'] = '投稿済み ✅' if result.get('success') else '失敗 ❌'
    _timers.pop(job_id, None)

@app.route('/logout')
def logout():
    return redirect('https://www.ins-japan.com/')

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

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

@app.route('/api/generate-images', methods=['POST'])
def api_generate_images():
    try:
        prompt = request.get_json().get('prompt', '')
        result = generate_images(prompt)
        if not result.get('images'):
            return jsonify({'images': [], 'error': '画像生成に失敗しました。Gemini APIの制限か一時的なエラーです'})
        return jsonify(result)
    except Exception as e:
        return jsonify({'images': [], 'error': f'画像生成エラー: {str(e)[:100]}'})

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

@app.route('/manual/free')
def manual_free():
    return render_template('manual_free.html')

@app.route('/manual/paid')
def manual_paid():
    return render_template('manual_paid.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
