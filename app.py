from flask import Flask, render_template, request, jsonify
import os
from api_handlers import post_to_x, generate_posts, generate_images, get_news_articles

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
