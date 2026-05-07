const shortText = document.getElementById('short-text');
const shortCount = document.getElementById('short-count');
const opinionText = document.getElementById('opinion-text');
const opinionCount = document.getElementById('opinion-count');
let selectedArticle = null;
let selectedPrompt = {short: null, news: null};
let selectedImage = {short: null, news: null};

shortText.addEventListener('input', () => { shortCount.textContent = shortText.value.length; });
opinionText?.addEventListener('input', () => { opinionCount.textContent = opinionText.value.length; });

function switchTab(tab) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`${tab}-section`).classList.add('active');
    document.querySelectorAll('.tab')[tab === 'short' ? 0 : 1].classList.add('active');
}

function loadNews() {
    const source = document.getElementById('news-source').value;
    const loading = document.getElementById('news-fetch-loading');
    loading.classList.add('show');
    fetch(`/api/news?source=${encodeURIComponent(source)}`)
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('article-list');
            list.innerHTML = '';
            data.articles.forEach((article, idx) => {
                const btn = document.createElement('button');
                btn.className = 'article-btn';
                btn.innerHTML = `<div class="article-title">${idx + 1}. ${article.title}</div><div class="article-summary">${article.summary || '詳細なし'}</div>`;
                btn.onclick = () => {
                    selectedArticle = article;
                    document.querySelectorAll('.article-btn').forEach(b => b.classList.remove('selected'));
                    btn.classList.add('selected');
                    document.getElementById('opinion-section').style.display = 'block';
                    document.getElementById('opinion-label').textContent = `「${article.title}」についてのあなたの意見`;
                };
                list.appendChild(btn);
            });
            loading.classList.remove('show');
        });
}

function postText(section) {
    const text = section === 'short' ? shortText.value.trim() : opinionText.value.trim();
    if (!text) { showResult(`${section}-result`, 'テキストを入力してください', 'error'); return; }
    if (section === 'news' && !selectedArticle) { showResult('news-result', '記事を選択してください', 'error'); return; }
    fetch('/api/post', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text})})
        .then(r => r.json())
        .then(data => showResult(`${section}-result`, data.success ? `✓ 投稿完了! Tweet ID: ${data.tweet_id}` : `✗ 投稿失敗: ${data.error}`, data.success ? 'success' : 'error'));
}

function generatePatterns(section) {
    const textarea = section === 'short' ? shortText : opinionText;
    const counter = section === 'short' ? shortCount : opinionCount;
    const topic = section === 'short' ? (textarea.value.trim() || 'X投稿') : `${selectedArticle?.title || ''}: ${textarea.value.trim() || '記事に同意'}`;
    if (section === 'news' && !selectedArticle) { showResult('news-result', '記事を選択してください', 'error'); return; }

    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '🤖 生成中...';
    document.getElementById(`${section}-loading`).classList.add('show');

    fetch('/api/generate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({topic})})
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            btn.textContent = '🤖 AI生成';
            document.getElementById(`${section}-loading`).classList.remove('show');

            const prompts = data.prompts || [];
            const labels = data.labels || prompts;
            if (!prompts.length) return;

            const list = document.getElementById(`${section}-patterns-list`);
            list.innerHTML = '';
            prompts.forEach((prompt, idx) => {
                const div = document.createElement('div');
                div.style.cssText = `padding: 15px; background: ${idx === 0 ? '#667eea' : '#2a2a2a'}; border: 2px solid ${idx === 0 ? '#667eea' : '#444'}; border-radius: 6px; cursor: pointer;`;
                div.innerHTML = `<div style="font-weight:600;color:#fff;margin-bottom:8px;">【パターン${idx + 1}】</div><div style="color:#fff;line-height:1.5;">${labels[idx]}</div>`;
                div.onclick = () => {
                    Array.from(list.children).forEach((el, i) => {
                        el.style.background = i === idx ? '#667eea' : '#2a2a2a';
                        el.style.borderColor = i === idx ? '#667eea' : '#444';
                    });
                    textarea.value = prompt;
                    counter.textContent = prompt.length;
                    selectedPrompt[section] = prompt;
                    document.getElementById(`${section}-image-btn`).style.display = 'inline-block';
                    document.getElementById(`${section}-image-section`).style.display = 'none';
                    showResult(`${section}-result`, `✓ パターン${idx + 1}を選択しました`, 'success');
                };
                list.appendChild(div);
            });

            selectedPrompt[section] = prompts[0];
            document.getElementById(`${section}-patterns`).style.display = 'block';
            document.getElementById(`${section}-image-btn`).style.display = 'inline-block';
            showResult(`${section}-result`, '✓ AI生成完了!', 'success');
        });
}

function generateImages(section) {
    const prompt = selectedPrompt[section];
    if (!prompt) return;
    const btn = document.getElementById(`${section}-image-btn`);
    btn.disabled = true;
    document.getElementById(`${section}-image-loading`).classList.add('show');

    fetch('/api/generate-images', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({prompt})})
        .then(r => r.json())
        .then(data => {
            btn.disabled = false;
            document.getElementById(`${section}-image-loading`).classList.remove('show');

            const list = document.getElementById(`${section}-image-list`);
            list.innerHTML = '';
            const postBtn = document.getElementById(`${section}-post-with-image-btn`);
            postBtn.style.display = 'none';
            selectedImage[section] = null;

            data.images.forEach(b64 => {
                const wrapper = document.createElement('div');
                wrapper.style.cssText = 'cursor:pointer;border:3px solid #444;border-radius:8px;overflow:hidden;';
                const img = document.createElement('img');
                img.src = `data:image/png;base64,${b64}`;
                img.style.cssText = 'width:100%;display:block;';
                wrapper.appendChild(img);
                wrapper.onclick = () => {
                    list.querySelectorAll('div').forEach(el => el.style.borderColor = '#444');
                    wrapper.style.borderColor = '#667eea';
                    selectedImage[section] = b64;
                    postBtn.style.display = 'block';
                };
                list.appendChild(wrapper);
            });

            document.getElementById(`${section}-image-section`).style.display = 'block';
        });
}

function postWithImage(section) {
    const text = section === 'short' ? shortText.value.trim() : opinionText.value.trim();
    const image = selectedImage[section];
    if (!image) return;
    fetch('/api/post', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, image})})
        .then(r => r.json())
        .then(data => showResult(`${section}-result`, data.success ? `✓ 投稿完了! Tweet ID: ${data.tweet_id}` : `✗ 投稿失敗: ${data.error}`, data.success ? 'success' : 'error'));
}

function showResult(id, msg, type) {
    const el = document.getElementById(id);
    el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;"><span>${msg}</span><button onclick="this.parentElement.parentElement.style.display='none'" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:18px;padding:0 10px;">×</button></div>`;
    el.className = `result ${type}`;
}
