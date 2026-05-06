const shortText = document.getElementById('short-text');
const shortCount = document.getElementById('short-count');
const opinionText = document.getElementById('opinion-text');
const opinionCount = document.getElementById('opinion-count');
let selectedArticle = null;

shortText.addEventListener('input', () => {
    shortCount.textContent = shortText.value.length;
});

opinionText?.addEventListener('input', () => {
    opinionCount.textContent = opinionText.value.length;
});

function switchTab(tab) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

    if (tab === 'short') {
        document.getElementById('short-section').classList.add('active');
        document.querySelectorAll('.tab')[0].classList.add('active');
    } else {
        document.getElementById('news-section').classList.add('active');
        document.querySelectorAll('.tab')[1].classList.add('active');
    }
}

function loadNews() {
    const source = document.getElementById('news-source').value;
    const loadingMsg = document.getElementById('news-fetch-loading');
    loadingMsg.classList.add('show');

    fetch(`/api/news?source=${encodeURIComponent(source)}`)
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('article-list');
            list.innerHTML = '';
            data.articles.forEach((article, idx) => {
                const btn = document.createElement('button');
                btn.className = 'article-btn';
                btn.innerHTML = `
                    <div class="article-title">${idx + 1}. ${article.title}</div>
                    <div class="article-summary">${article.summary || '詳細なし'}</div>
                `;
                btn.onclick = () => selectArticle(article, idx, btn);
                list.appendChild(btn);
            });
            loadingMsg.classList.remove('show');
        });
}

function selectArticle(article, idx, element) {
    selectedArticle = article;
    document.querySelectorAll('.article-btn').forEach(btn => btn.classList.remove('selected'));
    element.classList.add('selected');
    document.getElementById('opinion-section').style.display = 'block';
    document.getElementById('opinion-label').textContent = `「${article.title}」についてのあなたの意見`;
}

function postShort() {
    const text = shortText.value.trim();
    if (!text) {
        showResult('short-result', 'テキストを入力してください', 'error');
        return;
    }
    fetch('/api/post', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: text})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showResult('short-result', `✓ 投稿完了! Tweet ID: ${data.tweet_id}`, 'success');
        } else {
            showResult('short-result', `✗ 投稿失敗: ${data.error}`, 'error');
        }
    });
}

let selectedShortPattern = null;

function generateShort() {
    const text = shortText.value.trim() || 'X投稿';
    const genBtn = event.target;
    genBtn.disabled = true;
    genBtn.textContent = '🤖 生成中...';

    const loadingMsg = document.getElementById('short-loading');
    loadingMsg.classList.add('show');

    fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({topic: text})
    })
    .then(r => r.json())
    .then(data => {
        if (data.posts && data.posts.length > 0) {
            shortText.value = data.posts[0];
            shortCount.textContent = data.posts[0].length;
            selectedShortPattern = 0;

            const patternsList = document.getElementById('short-patterns-list');
            patternsList.innerHTML = '';
            data.posts.forEach((post, idx) => {
                const patternDiv = document.createElement('div');
                const isSelected = idx === 0;
                const bgColor = isSelected ? '#667eea' : '#2a2a2a';
                const borderColor = isSelected ? '#667eea' : '#444';
                patternDiv.className = isSelected ? 'pattern-selected' : '';
                patternDiv.style.cssText = `padding: 15px; background: ${bgColor}; border: 2px solid ${borderColor}; border-radius: 6px; cursor: pointer; transition: all 0.3s;`;
                patternDiv.innerHTML = `
                    <div style="font-weight: 600; color: ${isSelected ? '#ffffff' : '#667eea'}; margin-bottom: 8px;">【パターン${idx + 1}】</div>
                    <div style="color: #ffffff; line-height: 1.5;">${post}</div>
                    <div style="font-size: 12px; color: #aaa; margin-top: 8px;">${post.length}文字</div>
                `;
                patternDiv.onmouseover = () => {
                    if (idx !== selectedShortPattern) patternDiv.style.background = '#333';
                };
                patternDiv.onmouseout = () => {
                    patternDiv.style.background = (idx === selectedShortPattern) ? '#667eea' : '#2a2a2a';
                };
                patternDiv.onclick = () => {
                    selectedShortPattern = idx;
                    document.querySelectorAll('#short-patterns-list > div').forEach((el, i) => {
                        const selected = i === idx;
                        el.style.background = selected ? '#667eea' : '#2a2a2a';
                        el.style.borderColor = selected ? '#667eea' : '#444';
                        el.querySelector('[style*="color"]').style.color = selected ? '#ffffff' : '#667eea';
                    });
                    shortText.value = post;
                    shortCount.textContent = post.length;
                    showResult('short-result', `✓ パターン${idx + 1}を選択しました`, 'success');
                };
                patternsList.appendChild(patternDiv);
            });

            document.getElementById('short-patterns').style.display = 'block';
            showResult('short-result', '✓ AI生成完了!', 'success');
        }
        genBtn.disabled = false;
        genBtn.textContent = '🤖 AI生成';
        loadingMsg.classList.remove('show');
    });
}

function postNews() {
    if (!selectedArticle) {
        showResult('news-result', '記事を選択してください', 'error');
        return;
    }
    const opinion = opinionText.value.trim();
    if (!opinion) {
        showResult('news-result', '意見を入力してください', 'error');
        return;
    }
    fetch('/api/post', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: opinion})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showResult('news-result', `✓ 投稿完了! Tweet ID: ${data.tweet_id}`, 'success');
        } else {
            showResult('news-result', `✗ 投稿失敗: ${data.error}`, 'error');
        }
    });
}

let selectedNewsPattern = null;

function generateNews() {
    if (!selectedArticle) {
        showResult('news-result', '記事を選択してください', 'error');
        return;
    }
    const opinion = opinionText.value.trim() || '記事に同意';
    const title = selectedArticle.title;

    const genBtn = event.target;
    genBtn.disabled = true;
    genBtn.textContent = '🤖 生成中...';

    const loadingMsg = document.getElementById('news-loading');
    loadingMsg.classList.add('show');

    fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({topic: `${title}: ${opinion}`})
    })
    .then(r => r.json())
    .then(data => {
        if (data.posts && data.posts.length > 0) {
            opinionText.value = data.posts[0];
            opinionCount.textContent = data.posts[0].length;
            selectedNewsPattern = 0;

            const patternsList = document.getElementById('news-patterns-list');
            patternsList.innerHTML = '';
            data.posts.forEach((post, idx) => {
                const patternDiv = document.createElement('div');
                const isSelected = idx === 0;
                const bgColor = isSelected ? '#667eea' : '#2a2a2a';
                const borderColor = isSelected ? '#667eea' : '#444';
                patternDiv.style.cssText = `padding: 15px; background: ${bgColor}; border: 2px solid ${borderColor}; border-radius: 6px; cursor: pointer; transition: all 0.3s;`;
                patternDiv.innerHTML = `
                    <div style="font-weight: 600; color: ${isSelected ? '#ffffff' : '#667eea'}; margin-bottom: 8px;">【パターン${idx + 1}】</div>
                    <div style="color: #ffffff; line-height: 1.5;">${post}</div>
                    <div style="font-size: 12px; color: #aaa; margin-top: 8px;">${post.length}文字</div>
                `;
                patternDiv.onmouseover = () => {
                    if (idx !== selectedNewsPattern) patternDiv.style.background = '#333';
                };
                patternDiv.onmouseout = () => {
                    patternDiv.style.background = (idx === selectedNewsPattern) ? '#667eea' : '#2a2a2a';
                };
                patternDiv.onclick = () => {
                    selectedNewsPattern = idx;
                    document.querySelectorAll('#news-patterns-list > div').forEach((el, i) => {
                        const selected = i === idx;
                        el.style.background = selected ? '#667eea' : '#2a2a2a';
                        el.style.borderColor = selected ? '#667eea' : '#444';
                        el.querySelector('[style*="color"]').style.color = selected ? '#ffffff' : '#667eea';
                    });
                    opinionText.value = post;
                    opinionCount.textContent = post.length;
                    showResult('news-result', `✓ パターン${idx + 1}を選択しました`, 'success');
                };
                patternsList.appendChild(patternDiv);
            });

            document.getElementById('news-patterns').style.display = 'block';
            showResult('news-result', '✓ AI生成完了!', 'success');
        }
        genBtn.disabled = false;
        genBtn.textContent = '🤖 AI生成';
        loadingMsg.classList.remove('show');
    });
}

function showResult(id, msg, type) {
    const el = document.getElementById(id);
    el.innerHTML = `<div style="display: flex; justify-content: space-between; align-items: center;">
        <span>${msg}</span>
        <button onclick="this.parentElement.parentElement.style.display='none'" style="background: none; border: none; color: #aaa; cursor: pointer; font-size: 18px; padding: 0 10px;">×</button>
    </div>`;
    el.className = `result ${type}`;
}
