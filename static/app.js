// OAuth コールバック処理
(function() {
    const hash = window.location.hash;
    if (hash.startsWith('#oauth-done')) {
        const params = new URLSearchParams(hash.slice('#oauth-done?'.length));
        const at = params.get('at'), ats = params.get('ats'), sn = params.get('sn');
        if (at && ats) {
            const accounts = (() => { try { return JSON.parse(localStorage.getItem('xpost_accounts') || '[]'); } catch { return []; } })();
            if (!accounts.find(a => a.at === at)) {
                const plan = localStorage.getItem('xpost_plan') || 'free';
                const limit = plan === 'premium' ? 99 : 1;
                if (accounts.length < limit) {
                    accounts.push({ name: '@' + sn, at, ats, ck: '', cs: '', id: Date.now() });
                    localStorage.setItem('xpost_accounts', JSON.stringify(accounts));
                }
            }
        }
        history.replaceState(null, '', '/');
    }
})();

// 起動時API状態チェック
fetch('/api/health').then(r => r.json()).then(data => {
    const bar = document.getElementById('health-bar');
    if (data.overall === 'OK') {
        bar.style.cssText = 'display:block;background:#1a3a1a;color:#4caf50;padding:6px 12px;border-radius:6px;margin-bottom:10px;font-size:13px;text-align:center;';
        bar.textContent = '✅ 全システム正常稼働中';
        setTimeout(() => bar.style.display = 'none', 4000);
    } else {
        bar.style.cssText = 'display:block;background:#3a1a1a;color:#f44336;padding:6px 12px;border-radius:6px;margin-bottom:10px;font-size:13px;text-align:center;';
        bar.textContent = `⚠️ システム異常検知 — Gemini: ${data.gemini} / X API: ${data.x_api}`;
    }
}).catch(() => {});

const shortText = document.getElementById('short-text');
const shortCount = document.getElementById('short-count');
const opinionText = document.getElementById('opinion-text');
const opinionCount = document.getElementById('opinion-count');
let selectedArticle = null;
let selectedPrompt = {short: null, news: null};
let selectedImage = {short: null, news: null};

const UPGRADE_URL = 'https://www.ins-japan.com/upgrade/';

shortText.addEventListener('input', () => { shortCount.textContent = shortText.value.length; });
opinionText?.addEventListener('input', () => { opinionCount.textContent = opinionText.value.length; });

// ===== プラン管理 =====

function getPlan() {
    const plan = localStorage.getItem('xpost_plan');
    if (plan) return plan;
    // 後方互換：既存xpost_premiumをマイグレーション
    if (localStorage.getItem('xpost_premium') === 'true') {
        localStorage.setItem('xpost_plan', 'premium');
        return 'premium';
    }
    return 'free';
}

function checkPostLimit(section) {
    if (getPlan() !== 'free') return true;
    const today = new Date().toISOString().split('T')[0];
    const count = parseInt(localStorage.getItem(`xpost_post_${today}`) || '0');
    if (count >= 3) {
        showResult(`${section}-result`, `📊 本日の無料投稿回数（3回）に達しました。<a href="${UPGRADE_URL}" target="_blank" style="color:#f5a623;font-weight:700;">有料プランにアップグレード →</a>`, 'error');
        return false;
    }
    return true;
}

function checkGenLimit(section) {
    if (getPlan() !== 'free') return true;
    const today = new Date().toISOString().split('T')[0];
    const count = parseInt(localStorage.getItem(`xpost_gen_${today}`) || '0');
    if (count >= 5) {
        showResult(`${section}-result`, `🤖 本日のAI生成回数（5回）に達しました。<a href="${UPGRADE_URL}" target="_blank" style="color:#f5a623;font-weight:700;">有料プランにアップグレード →</a>`, 'error');
        return false;
    }
    return true;
}

function checkImageAccess(section) {
    if (getPlan() !== 'free') return true;
    showResult(`${section}-result`, `🖼️ 画像生成は有料プラン（¥1,980/月）以上でご利用いただけます。<a href="${UPGRADE_URL}" target="_blank" style="color:#f5a623;font-weight:700;">アップグレード →</a>`, 'error');
    return false;
}

function checkScheduleAccess(section) {
    if (getPlan() !== 'free') return true;
    showResult(`${section}-result`, `⏰ 予約投稿は有料プラン（¥1,980/月）から利用いただけます。<a href="${UPGRADE_URL}" target="_blank" style="color:#f5a623;font-weight:700;">アップグレード →</a>`, 'error');
    return false;
}

function incrementPostCount() {
    if (getPlan() !== 'free') return;
    const today = new Date().toISOString().split('T')[0];
    const count = parseInt(localStorage.getItem(`xpost_post_${today}`) || '0');
    localStorage.setItem(`xpost_post_${today}`, count + 1);
}

function incrementGenCount() {
    if (getPlan() !== 'free') return;
    const today = new Date().toISOString().split('T')[0];
    const count = parseInt(localStorage.getItem(`xpost_gen_${today}`) || '0');
    localStorage.setItem(`xpost_gen_${today}`, count + 1);
}

// ===== タブ切り替え =====

function switchTab(tab, btn) {
    if (tab === 'surge' && getPlan() !== 'premium') {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById('surge-section').classList.add('active');
        btn.classList.add('active');
        document.getElementById('surge-lock-banner').style.display = 'block';
        document.getElementById('surge-content').style.display = 'none';
        return;
    }
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`${tab}-section`).classList.add('active');
    btn.classList.add('active');
    if (tab === 'surge') {
        document.getElementById('surge-lock-banner').style.display = 'none';
        document.getElementById('surge-content').style.display = 'block';
        renderCalendar();
        loadContextInputs();
    }
}

// ===== ニュース取得 =====

function loadNews() {
    const source = document.getElementById('news-source').value;
    const loading = document.getElementById('news-fetch-loading');
    loading.classList.add('show');
    fetch(`/api/news?source=${encodeURIComponent(source)}`)
        .then(r => r.json())
        .then(data => {
            loading.classList.remove('show');
            if (data.error) { showResult('news-result', `✗ ${data.error}`, 'error'); return; }
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
        })
        .catch(() => {
            loading.classList.remove('show');
            showResult('news-result', '✗ ネットワークエラー：ニュース取得に失敗しました', 'error');
        });
}

// ===== 投稿 =====

function getScheduleTime(section) {
    const y = document.getElementById(`${section}-sched-year`)?.value;
    const mo = document.getElementById(`${section}-sched-month`)?.value;
    const d = document.getElementById(`${section}-sched-day`)?.value;
    const h = document.getElementById(`${section}-sched-hour`)?.value;
    const mi = document.getElementById(`${section}-sched-min`)?.value;
    if (y && mo && d && h && mi) return `${y}-${mo}-${d}T${h}:${mi}`;
    return '';
}

function postText(section) {
    const text = section === 'short' ? shortText.value.trim() : opinionText.value.trim();
    if (!text) { showResult(`${section}-result`, 'テキストを入力してください', 'error'); return; }
    if (section === 'news' && !selectedArticle) { showResult('news-result', '記事を選択してください', 'error'); return; }

    const scheduleTime = getScheduleTime(section);

    if (scheduleTime && !checkScheduleAccess(section)) return;
    if (!scheduleTime && !checkPostLimit(section)) return;

    const credentials = getSelectedCredentials(section);

    if (scheduleTime) {
        fetch('/api/schedule', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, scheduled_time: scheduleTime, credentials})})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showResult(`${section}-result`, `✅ 予約完了！ ${scheduleTime.replace('T',' ')} に自動投稿されます (ID: ${data.job_id})`, 'success');
                    scheduleEl.value = '';
                } else {
                    showResult(`${section}-result`, `✗ 予約失敗: ${data.error}`, 'error');
                }
            });
    } else {
        fetch('/api/post', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, credentials})})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    recordPost();
                    incrementPostCount();
                    showResult(`${section}-result`, `✓ 投稿完了！ <a href="${data.tweet_url}" target="_blank" style="color:#1da1f2;">Xで確認する →</a>`, 'success');
                } else {
                    showResult(`${section}-result`, `✗ 投稿失敗: ${data.error}`, 'error');
                }
            });
    }
}

// ===== AI生成 =====

function generatePatterns(section) {
    if (!checkGenLimit(section)) return;

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

            if (data.error) { showResult(`${section}-result`, `✗ ${data.error}`, 'error'); return; }
            const prompts = data.prompts || [];
            const labels = data.labels || prompts;
            if (!prompts.length) { showResult(`${section}-result`, '✗ パターンを生成できませんでした。再度お試しください', 'error'); return; }

            incrementGenCount();

            const list = document.getElementById(`${section}-patterns-list`);
            list.innerHTML = '';
            prompts.forEach((prompt, idx) => {
                const div = document.createElement('div');
                div.style.cssText = `padding: 15px; background: ${idx === 0 ? '#667eea' : '#2a2a2a'}; border: 2px solid ${idx === 0 ? '#667eea' : '#444'}; border-radius: 6px; cursor: pointer;`;
                const charCount = prompt.length;
                const countColor = charCount > 280 ? '#f44336' : charCount > 250 ? '#ff9800' : '#4caf50';
                div.innerHTML = `<div style="font-weight:600;color:#fff;margin-bottom:8px;">【パターン${idx + 1}】<span style="font-size:11px;color:${countColor};margin-left:8px;">${charCount}/280文字</span></div><div style="color:#fff;line-height:1.5;white-space:pre-wrap;">${labels[idx]}</div>`;
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
            textarea.value = prompts[0];
            counter.textContent = prompts[0].length;
            document.getElementById(`${section}-patterns`).style.display = 'block';
            document.getElementById(`${section}-image-btn`).style.display = 'inline-block';
            showResult(`${section}-result`, '✓ AI生成完了!', 'success');
        })
        .catch(() => {
            btn.disabled = false;
            btn.textContent = '🤖 AI生成';
            document.getElementById(`${section}-loading`).classList.remove('show');
            showResult(`${section}-result`, '✗ 通信エラー：しばらく待ってから再度お試しください', 'error');
        });
}

// ===== 画像生成 =====

function _displayImages(section, data, loadingId, btn) {
    if (loadingId) document.getElementById(loadingId).classList.remove('show');
    if (btn) btn.disabled = false;
    if (data.error || !data.images || !data.images.length) {
        showResult(`${section}-result`, '✗ 画像を生成できませんでした。再度お試しください', 'error'); return;
    }
    const list = document.getElementById(`${section}-image-list`);
    list.innerHTML = '';
    const postBtn = document.getElementById(`${section}-post-with-image-btn`);
    postBtn.style.display = 'none';
    selectedImage[section] = null;
    const title = data.title || '';
    (data.images || []).forEach(b64 => {
        addTitleToImage(b64, title, composited => {
            const wrapper = document.createElement('div');
            wrapper.style.cssText = 'cursor:pointer;border:3px solid #444;border-radius:8px;overflow:hidden;';
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${composited}`;
            img.style.cssText = 'width:100%;display:block;';
            wrapper.appendChild(img);
            wrapper.onclick = () => {
                list.querySelectorAll('div').forEach(el => el.style.borderColor = '#444');
                wrapper.style.borderColor = '#667eea';
                selectedImage[section] = composited;
                postBtn.style.display = 'block';
            };
            list.appendChild(wrapper);
        });
    });
    document.getElementById(`${section}-image-section`).style.display = 'block';
}

function _pollImageJob(jobId, section, loadingId, btn, attempt) {
    if (attempt > 40) {
        if (loadingId) document.getElementById(loadingId).classList.remove('show');
        if (btn) btn.disabled = false;
        showResult(`${section}-result`, '✗ 画像生成がタイムアウトしました。再度お試しください', 'error');
        return;
    }
    fetch(`/api/image-status/${jobId}`)
        .then(r => r.json())
        .then(data => {
            if (data.status === 'done') {
                _displayImages(section, data, loadingId, btn);
            } else if (data.status === 'error') {
                if (loadingId) document.getElementById(loadingId).classList.remove('show');
                if (btn) btn.disabled = false;
                showResult(`${section}-result`, `✗ ${data.error || '画像生成に失敗しました'}`, 'error');
            } else {
                setTimeout(() => _pollImageJob(jobId, section, loadingId, btn, attempt + 1), 3000);
            }
        })
        .catch(() => setTimeout(() => _pollImageJob(jobId, section, loadingId, btn, attempt + 1), 3000));
}

function _startImageJob(prompt, section, loadingId, btn) {
    fetch('/api/generate-images', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({prompt})})
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                if (loadingId) document.getElementById(loadingId).classList.remove('show');
                if (btn) btn.disabled = false;
                showResult(`${section}-result`, `✗ ${data.error}`, 'error'); return;
            }
            _pollImageJob(data.job_id, section, loadingId, btn, 0);
        })
        .catch(() => {
            if (loadingId) document.getElementById(loadingId).classList.remove('show');
            if (btn) btn.disabled = false;
            showResult(`${section}-result`, '✗ 画像生成を開始できませんでした。再度お試しください', 'error');
        });
}

function generateImages(section) {
    if (!checkImageAccess(section)) return;
    const prompt = selectedPrompt[section];
    if (!prompt) return;
    const btn = document.getElementById(`${section}-image-btn`);
    btn.disabled = true;
    const loadingId = `${section}-image-loading`;
    document.getElementById(loadingId).classList.add('show');
    _startImageJob(prompt, section, loadingId, btn);
}

function generateImagesFromText(section) {
    if (!checkImageAccess(section)) return;
    const textarea = section === 'short' ? shortText : opinionText;
    const prompt = textarea.value.trim();
    if (!prompt) { showResult(`${section}-result`, 'テキストを入力してください', 'error'); return; }
    selectedPrompt[section] = prompt;
    const loadingId = `${section}-direct-image-loading`;
    document.getElementById(loadingId).classList.add('show');
    _startImageJob(prompt, section, loadingId, null);
}

function addTitleToImage(b64, text, callback) {
    const canvas = document.createElement('canvas');
    const img = new Image();
    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        if (text) {
            const barH = Math.round(img.height * 0.11);
            ctx.fillStyle = 'rgba(0,0,0,0.68)';
            ctx.fillRect(0, img.height - barH, img.width, barH);
            ctx.fillStyle = '#fff';
            ctx.font = `bold ${Math.round(barH * 0.55)}px "Yu Gothic","Hiragino Sans","Meiryo",sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(text, img.width / 2, img.height - barH / 2);
        }
        callback(canvas.toDataURL('image/png').split(',')[1]);
    };
    img.src = `data:image/png;base64,${b64}`;
}

// ===== 画像付き投稿 =====

function postWithImage(section) {
    const text = section === 'short' ? shortText.value.trim() : opinionText.value.trim();
    const image = selectedImage[section];
    if (!image) return;
    const scheduleTime = getScheduleTime(section);

    if (scheduleTime && !checkScheduleAccess(section)) return;
    if (!scheduleTime && !checkPostLimit(section)) return;

    const credentials = getSelectedCredentials(section);
    if (scheduleTime) {
        fetch('/api/schedule', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, image, scheduled_time: scheduleTime, credentials})})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showResult(`${section}-image-result`, `✅ 予約完了！ ${scheduleTime.replace('T',' ')} に画像付きで自動投稿されます (ID: ${data.job_id})`, 'success');
                    scheduleEl.value = '';
                } else {
                    showResult(`${section}-image-result`, `✗ 予約失敗: ${data.error}`, 'error');
                }
            });
    } else {
        fetch('/api/post', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text, image, credentials})})
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    recordPost();
                    incrementPostCount();
                    showResult(`${section}-image-result`, `✓ 投稿完了！ <a href="${data.tweet_url}" target="_blank" style="color:#1da1f2;">Xで確認する →</a>`, 'success');
                } else {
                    showResult(`${section}-image-result`, `✗ 投稿失敗: ${data.error}`, 'error');
                }
            });
    }
}

function showResult(id, msg, type) {
    const el = document.getElementById(id);
    el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;"><span>${msg}</span><button onclick="this.parentElement.parentElement.style.display='none'" style="background:none;border:none;color:#aaa;cursor:pointer;font-size:18px;padding:0 10px;">×</button></div>`;
    el.className = `result ${type}`;
}

// ===== プレミアム＆マルチアカウント管理 =====

function initSettings() {
    const plan = getPlan();
    updatePlanUI(plan);
    if (plan === 'premium') renderAccountList();
    updateAccountSelectors();
}

function verifyPremium() {
    const code = document.getElementById('premium-code-input').value.trim();
    if (!code) return;
    fetch('/api/verify-premium', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({code})
    })
    .then(r => r.json())
    .then(data => {
        if (data.valid) {
            localStorage.setItem('xpost_plan', data.plan);
            localStorage.setItem('xpost_premium', data.plan === 'premium' ? 'true' : 'false');
            updatePlanUI(data.plan);
            if (data.plan === 'premium') renderAccountList();
            updateAccountSelectors();
            const msg = data.plan === 'premium'
                ? '✅ プレミアムプラン認証完了！SURGE全機能＋複数アカウントが使えます'
                : '✅ 有料プラン認証完了！画像生成・予約投稿・全基本機能が使えます';
            showResult('premium-result', msg, 'success');
        } else {
            showResult('premium-result', '❌ コードが正しくありません。登録メールをご確認ください', 'error');
        }
    });
}

function resetPremium() {
    localStorage.removeItem('xpost_plan');
    localStorage.removeItem('xpost_premium');
    localStorage.removeItem('xpost_accounts');
    updatePlanUI('free');
    updateAccountSelectors();
}

function updatePlanUI(plan) {
    const status = document.getElementById('premium-status');
    const mgmt = document.getElementById('account-management');
    const resetBtn = document.getElementById('reset-premium-btn');
    const inputArea = document.getElementById('premium-input-area');
    if (!status) return;

    const configs = {
        free:    { text: '🔒 無料プラン（1日3回まで）',                   bg: '#2a1a1a', color: '#ff6b6b', showReset: false, showInput: true  },
        basic:   { text: '✅ 有料プラン（¥1,980/月）— 全基本機能',        bg: '#1a2a0d', color: '#8bc34a', showReset: true,  showInput: false },
        premium: { text: '⚡ プレミアムプラン（¥2,980/月）— SURGE対応',   bg: '#0d1a2a', color: '#1da1f2', showReset: true,  showInput: false }
    };
    const c = configs[plan] || configs.free;
    status.textContent = c.text;
    status.style.cssText = `padding:8px 14px;border-radius:20px;display:inline-block;font-size:13px;font-weight:600;background:${c.bg};color:${c.color};margin-bottom:14px;`;
    mgmt.style.display = 'block';
    resetBtn.style.display = c.showReset ? 'inline-block' : 'none';
    inputArea.style.display = c.showInput ? 'block' : 'none';
    const manualApi = document.getElementById('manual-api-section');
    if (manualApi) manualApi.style.display = plan === 'premium' ? 'block' : 'none';
    const isFree = plan === 'free';
    ['short-schedule-notice','news-schedule-notice'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = isFree ? 'block' : 'none';
    });
}

function getAccounts() {
    try { return JSON.parse(localStorage.getItem('xpost_accounts') || '[]'); } catch { return []; }
}

function addAccount() {
    const name = document.getElementById('account-name').value.trim();
    const ck = document.getElementById('account-ck').value.trim();
    const cs = document.getElementById('account-cs').value.trim();
    const at = document.getElementById('account-at').value.trim();
    const ats = document.getElementById('account-ats').value.trim();
    if (!name || !ck || !cs || !at || !ats) {
        showResult('account-add-result', '❌ すべての項目を入力してください', 'error'); return;
    }
    const accounts = getAccounts();
    const plan = localStorage.getItem('xpost_plan') || 'free';
    if (plan === 'basic' && accounts.length >= 1) {
        showResult('account-add-result', '❌ 有料プランは1アカウントまでです。複数登録はプレミアムにアップグレードしてください', 'error'); return;
    }
    accounts.push({name, ck, cs, at, ats, id: Date.now()});
    localStorage.setItem('xpost_accounts', JSON.stringify(accounts));
    ['account-name','account-ck','account-cs','account-at','account-ats'].forEach(id => document.getElementById(id).value = '');
    showResult('account-add-result', `✅ 「${name}」を登録しました`, 'success');
    renderAccountList();
    updateAccountSelectors();
}

function removeAccount(id) {
    const accounts = getAccounts().filter(a => a.id !== id);
    localStorage.setItem('xpost_accounts', JSON.stringify(accounts));
    renderAccountList();
    updateAccountSelectors();
}

function renderAccountList() {
    const accounts = getAccounts();
    const el = document.getElementById('account-list');
    if (!el) return;
    if (!accounts.length) {
        el.innerHTML = '<p style="color:#aaa;font-size:13px;">まだアカウントが登録されていません</p>'; return;
    }
    el.innerHTML = accounts.map(a => `
        <div style="background:#0d0d1a;border:1px solid #333;border-radius:8px;padding:10px 14px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div style="font-weight:600;">📱 ${a.name}</div>
                <div style="font-size:11px;color:#888;margin-top:2px;">CK: ${a.ck.substring(0,10)}...</div>
            </div>
            <button class="secondary" onclick="removeAccount(${a.id})" style="font-size:12px;padding:4px 10px;">削除</button>
        </div>
    `).join('');
}

function updateAccountSelectors() {
    const accounts = getAccounts();
    const isPremium = getPlan() === 'premium';
    ['short','news','thread'].forEach(section => {
        const row = document.getElementById(`${section}-account-row`);
        const select = document.getElementById(`${section}-account-select`);
        if (!row || !select) return;
        if (isPremium && accounts.length > 1) {
            row.style.display = 'block';
            select.innerHTML = '<option value="">デフォルトアカウント（サービス設定）</option>' +
                accounts.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
        } else {
            row.style.display = 'none';
        }
    });
}

function getSelectedCredentials(section) {
    if (getPlan() !== 'premium') return null;
    const select = document.getElementById(`${section}-account-select`);
    if (!select || !select.value) return null;
    const id = parseInt(select.value);
    const account = getAccounts().find(a => a.id === id);
    return account ? {ck: account.ck, cs: account.cs, at: account.at, ats: account.ats} : null;
}

// ページ読み込み時に設定を初期化
initSettings();

// ===== SURGE機能 =====

function getContext() {
  const style = localStorage.getItem('xpost_ctx_style') || '';
  const product = localStorage.getItem('xpost_ctx_product') || '';
  const target = localStorage.getItem('xpost_ctx_target') || '';
  return [style, product, target].filter(Boolean).join('\n');
}

function saveContext() {
  const style = document.getElementById('sg-ctx-style').value.trim();
  const product = document.getElementById('sg-ctx-product').value.trim();
  const target = document.getElementById('sg-ctx-target').value.trim();
  localStorage.setItem('xpost_ctx_style', style);
  localStorage.setItem('xpost_ctx_product', product);
  localStorage.setItem('xpost_ctx_target', target);
  const r = document.getElementById('sg-ctx-result');
  r.textContent = '✅ 魂を保存しました。全機能に反映されます。';
  r.style.display = 'block';
  setTimeout(() => r.style.display = 'none', 3000);
}

function loadContextInputs() {
  const s = document.getElementById('sg-ctx-style');
  const p = document.getElementById('sg-ctx-product');
  const t = document.getElementById('sg-ctx-target');
  if (s) s.value = localStorage.getItem('xpost_ctx_style') || '';
  if (p) p.value = localStorage.getItem('xpost_ctx_product') || '';
  if (t) t.value = localStorage.getItem('xpost_ctx_target') || '';
}

function copyResult(id) {
  const el = document.getElementById(id);
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    const btn = el.nextElementSibling;
    if (btn) { btn.textContent = '✅ コピーしました'; setTimeout(() => btn.textContent = '📋 コピー', 2000); }
  });
}

function surgeLongPost() {
  const topic = document.getElementById('sg-long-topic').value.trim();
  if (!topic) { alert('ネタを入力してください'); return; }
  const loading = document.getElementById('sg-long-loading');
  const result = document.getElementById('sg-long-result');
  const copyBtn = document.getElementById('sg-long-copy-btn');
  loading.style.display = 'block';
  result.style.display = 'none';
  copyBtn.style.display = 'none';
  fetch('/api/surge/long-post', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({topic, context: getContext()})
  }).then(r => r.json()).then(data => {
    loading.style.display = 'none';
    result.textContent = data.post || data.error || 'エラーが発生しました';
    result.style.display = 'block';
    if (data.post) copyBtn.style.display = 'inline-block';
  }).catch(e => {
    loading.style.display = 'none';
    result.textContent = 'エラー: ' + e.message;
    result.style.display = 'block';
  });
}

function surgeBuzz() {
  const topic = document.getElementById('sg-buzz-topic').value.trim();
  if (!topic) { alert('ネタを入力してください'); return; }
  const style = document.querySelector('input[name="buzz-style"]:checked')?.value || 'list';
  const loading = document.getElementById('sg-buzz-loading');
  const result = document.getElementById('sg-buzz-result');
  const copyBtn = document.getElementById('sg-buzz-copy-btn');
  loading.style.display = 'block';
  result.style.display = 'none';
  copyBtn.style.display = 'none';
  fetch('/api/surge/buzz', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({topic, style, context: getContext()})
  }).then(r => r.json()).then(data => {
    loading.style.display = 'none';
    result.textContent = data.post || data.error || 'エラーが発生しました';
    result.style.display = 'block';
    if (data.post) copyBtn.style.display = 'inline-block';
  }).catch(e => {
    loading.style.display = 'none';
    result.textContent = 'エラー: ' + e.message;
    result.style.display = 'block';
  });
}

function surgeSelfQuote() {
  const past_post = document.getElementById('sg-qr-past').value.trim();
  if (!past_post) { alert('過去の投稿を入力してください'); return; }
  const loading = document.getElementById('sg-qr-loading');
  const result = document.getElementById('sg-qr-result');
  const copyBtn = document.getElementById('sg-qr-copy-btn');
  loading.style.display = 'block';
  result.style.display = 'none';
  copyBtn.style.display = 'none';
  fetch('/api/surge/self-quote', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({past_post, context: getContext()})
  }).then(r => r.json()).then(data => {
    loading.style.display = 'none';
    result.textContent = data.post || data.error || 'エラーが発生しました';
    result.style.display = 'block';
    if (data.post) copyBtn.style.display = 'inline-block';
  }).catch(e => {
    loading.style.display = 'none';
    result.textContent = 'エラー: ' + e.message;
    result.style.display = 'block';
  });
}

function surgeInspo() {
  const theme = document.getElementById('sg-inspo-theme').value.trim();
  const loading = document.getElementById('sg-inspo-loading');
  const result = document.getElementById('sg-inspo-result');
  loading.style.display = 'block';
  result.style.display = 'none';
  fetch('/api/surge/inspo', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({theme})
  }).then(r => r.json()).then(data => {
    loading.style.display = 'none';
    result.textContent = data.topics || data.error || 'エラーが発生しました';
    result.style.display = 'block';
  }).catch(e => {
    loading.style.display = 'none';
    result.textContent = 'エラー: ' + e.message;
    result.style.display = 'block';
  });
}

function surgeProfileCheck() {
  const profile = document.getElementById('sg-prof-text').value.trim();
  const pinned_post = document.getElementById('sg-prof-pinned').value.trim();
  if (!profile) { alert('プロフィールを入力してください'); return; }
  const loading = document.getElementById('sg-prof-loading');
  const result = document.getElementById('sg-prof-result');
  loading.style.display = 'block';
  result.style.display = 'none';
  fetch('/api/surge/profile-check', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({profile, pinned_post, context: getContext()})
  }).then(r => r.json()).then(data => {
    loading.style.display = 'none';
    result.textContent = data.diagnosis || data.error || 'エラーが発生しました';
    result.style.display = 'block';
  }).catch(e => {
    loading.style.display = 'none';
    result.textContent = 'エラー: ' + e.message;
    result.style.display = 'block';
  });
}

function recordPost() {
  const today = new Date().toISOString().split('T')[0];
  const cal = JSON.parse(localStorage.getItem('xpost_calendar') || '{}');
  cal[today] = (cal[today] || 0) + 1;
  localStorage.setItem('xpost_calendar', JSON.stringify(cal));
}

// ===== スレッド投稿 =====

(function loadThreadBooks() {
    fetch('/api/thread/books')
        .then(r => r.json())
        .then(data => {
            const select = document.getElementById('thread-book-select');
            if (!select) return;
            data.books.forEach(book => {
                const opt = document.createElement('option');
                opt.value = book.asin;
                opt.textContent = book.title;
                select.appendChild(opt);
            });
        })
        .catch(() => {});
})();

function generateThread() {
    const select = document.getElementById('thread-book-select');
    const asin = select.value;
    const title = select.options[select.selectedIndex]?.text;
    if (!asin) { showResult('thread-result', '書籍を選択してください', 'error'); return; }

    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '🤖 生成中...';
    document.getElementById('thread-loading').classList.add('show');
    document.getElementById('thread-preview').style.display = 'none';

    const amazonUrl = `https://www.amazon.co.jp/dp/${asin}`;

    fetch('/api/generate-thread', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({book_title: title, amazon_url: amazonUrl})
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.textContent = '🤖 スレッドを生成';
        document.getElementById('thread-loading').classList.remove('show');

        if (data.error || !data.tweets || !data.tweets.length) {
            showResult('thread-result', `✗ ${data.error || '生成失敗'}`, 'error');
            return;
        }

        const list = document.getElementById('thread-tweets-list');
        list.innerHTML = '';
        data.tweets.forEach((tweet, idx) => {
            const div = document.createElement('div');
            div.style.cssText = 'margin-bottom:16px;';
            div.innerHTML = `
                <div style="font-size:12px;color:#888;margin-bottom:4px;">投稿 ${idx + 1} / ${data.tweets.length}</div>
                <textarea id="thread-tweet-${idx}" rows="4" style="width:100%;padding:10px;border-radius:8px;border:1px solid #444;background:#0d0d1a;color:#e0e0e0;font-size:14px;resize:vertical;box-sizing:border-box;">${tweet}</textarea>
                <div style="font-size:11px;color:#888;text-align:right;margin-top:2px;"><span id="thread-count-${idx}">${tweet.length}</span> / 280文字</div>
            `;
            div.querySelector(`#thread-tweet-${idx}`).addEventListener('input', function() {
                document.getElementById(`thread-count-${idx}`).textContent = this.value.length;
            });
            list.appendChild(div);
        });

        document.getElementById('thread-preview').style.display = 'block';
        showResult('thread-result', `✓ ${data.tweets.length}投稿のスレッドを生成しました。内容を確認・編集してから投稿してください。`, 'success');
    })
    .catch(() => {
        btn.disabled = false;
        btn.textContent = '🤖 スレッドを生成';
        document.getElementById('thread-loading').classList.remove('show');
        showResult('thread-result', '✗ 通信エラー', 'error');
    });
}

function postThread() {
    const list = document.getElementById('thread-tweets-list');
    const textareas = list.querySelectorAll('textarea');
    const tweets = Array.from(textareas).map(ta => ta.value.trim()).filter(t => t);
    if (!tweets.length) { showResult('thread-result', '投稿するテキストがありません', 'error'); return; }

    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '📤 投稿中...';

    const credentials = getSelectedCredentials('thread');

    fetch('/api/post-thread', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({tweets, credentials})
    })
    .then(r => r.json())
    .then(data => {
        btn.disabled = false;
        btn.textContent = '📤 スレッドを投稿する';
        if (data.success || data.posted > 0) {
            recordPost();
            const url = data.thread_url ? ` <a href="${data.thread_url}" target="_blank" style="color:#1da1f2;">Xで確認する →</a>` : '';
            showResult('thread-result', `✓ ${data.posted}/${data.total}投稿完了！${url}`, 'success');
        } else {
            const errMsg = data.results?.[0]?.error || data.error || '投稿失敗';
            showResult('thread-result', `✗ 投稿失敗: ${errMsg}`, 'error');
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.textContent = '📤 スレッドを投稿する';
        showResult('thread-result', '✗ 通信エラー', 'error');
    });
}

function renderCalendar() {
  const container = document.getElementById('sg-calendar');
  if (!container) return;
  const cal = JSON.parse(localStorage.getItem('xpost_calendar') || '{}');
  const today = new Date();
  const weeks = 26;
  let html = '<div class="cal-grid">';
  for (let w = weeks - 1; w >= 0; w--) {
    html += '<div class="cal-week">';
    for (let d = 6; d >= 0; d--) {
      const date = new Date(today);
      date.setDate(today.getDate() - (w * 7 + d));
      const key = date.toISOString().split('T')[0];
      const count = cal[key] || 0;
      const level = count === 0 ? 0 : count === 1 ? 1 : count === 2 ? 2 : 3;
      html += `<div class="cal-day cal-level-${level}" title="${key}: ${count}件"></div>`;
    }
    html += '</div>';
  }
  html += '</div>';
  container.innerHTML = html;
}
