from flask import Flask, render_template, request, jsonify
import os, requests
from api_handlers import post_to_x, generate_posts, generate_images, get_news_articles
from config import GEMINI_API_KEY

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/news')
def api_news():
    source = request.args.get('source', '🌍 Axios')
    return jsonify({'articles': get_news_articles(source)})

@app.route('/api/post', methods=['POST'])
def api_post():
    data = request.get_json()
    return jsonify(post_to_x(data.get('text', ''), data.get('image', '')))

@app.route('/api/generate', methods=['POST'])
def api_generate():
    result = generate_posts(request.get_json().get('topic', 'X投稿'))
    return jsonify(result)

@app.route('/api/generate-images', methods=['POST'])
def api_generate_images():
    return jsonify({'images': generate_images(request.get_json().get('prompt', ''))})

@app.route('/api/list-models')
def list_models():
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}", timeout=15)
    names = [m['name'] for m in r.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
    return jsonify({"models": names})

@app.route('/api/debug-image')
def debug_image():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": "a beautiful sunset over mountains"}]}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}
    try:
        r = requests.post(url, json=payload, timeout=60)
        return jsonify({"status": r.status_code, "response": r.text[:1000]})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
