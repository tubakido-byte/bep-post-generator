from flask import Flask, render_template, request, jsonify
import os
from api_handlers import post_to_x, generate_posts, get_news_articles

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/news')
def api_news():
    source = request.args.get('source', '🌍 Axios')
    articles = get_news_articles(source)
    return jsonify({'articles': articles})

@app.route('/api/post', methods=['POST'])
def api_post():
    data = request.get_json()
    text = data.get('text', '')
    result = post_to_x(text)
    return jsonify(result)

@app.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json()
    topic = data.get('topic', 'X投稿')
    posts = generate_posts(topic)
    return jsonify({'posts': posts})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
