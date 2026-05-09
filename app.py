from flask import Flask, render_template, request, jsonify
import os, requests
from api_handlers import post_to_x, generate_posts, generate_images, get_news_articles, health_check
from config import GEMINI_API_KEY

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
