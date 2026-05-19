from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os, requests, uuid, atexit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from api_handlers import post_to_x, generate_posts, generate_images, get_news_articles, health_check
from config import GEMINI_API_KEY

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'xpost-secret-2024')

scheduler = BackgroundScheduler(timezone='Asia/Tokyo')
scheduler.start()
atexit.register(lambda: scheduler.shutdown())
scheduled_posts = {}

APP_USERNAME = os.environ.get('APP_USERNAME', 'admin')
APP_PASSWORD = os.environ.get('APP_PASSWORD', 'xpost2024')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == APP_USERNAME and password == APP_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        error = 'メールアドレスまたはパスワードが違います'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('https://www.ins-japan.com/')

@app.route('/')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
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
    return jsonify(post_to_x(data.get('text', ''), data.get('image', '')))

@app.route('/api/generate', methods=['POST'])
def api_generate():
    try:
        topic = request.get_json().get('topic', 'X投稿')
        result = generate_posts(topic)
        if not result.get('prompts'):
            return jsonify({'prompts': [], 'error': 'AI生成に失敗しました。しばらく待ってから再試行してください'})
        return jsonify(result)
    except Exception as e:
        return jsonify({'prompts': [], 'error': f'生成エラー: {str(e)[:100]}'})

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
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': '未ログイン'})
    data = request.get_json()
    text = data.get('text', '').strip()
    scheduled_time_str = data.get('scheduled_time', '')
    if not text or not scheduled_time_str:
        return jsonify({'success': False, 'error': '投稿テキストまたは日時が未入力です'})
    try:
        dt = datetime.fromisoformat(scheduled_time_str)
    except ValueError:
        return jsonify({'success': False, 'error': '日時フォーマットエラー'})
    job_id = str(uuid.uuid4())[:8]
    def run_post():
        result = post_to_x(text, '')
        if job_id in scheduled_posts:
            scheduled_posts[job_id]['status'] = '投稿済み ✅' if result.get('success') else '失敗 ❌'
    scheduler.add_job(run_post, 'date', run_date=dt, id=job_id)
    scheduled_posts[job_id] = {
        'text': text[:50] + '…' if len(text) > 50 else text,
        'full_text': text,
        'scheduled_time': scheduled_time_str,
        'status': '待機中 ⏳'
    }
    return jsonify({'success': True, 'job_id': job_id})

@app.route('/api/scheduled-posts')
def api_scheduled_posts():
    if not session.get('logged_in'):
        return jsonify({'posts': []})
    return jsonify({'posts': [{'id': k, **v} for k, v in scheduled_posts.items()]})

@app.route('/api/cancel-schedule/<job_id>', methods=['POST'])
def api_cancel_schedule(job_id):
    if not session.get('logged_in'):
        return jsonify({'success': False})
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    if job_id in scheduled_posts:
        scheduled_posts[job_id]['status'] = 'キャンセル ❌'
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
