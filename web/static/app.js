// === State ===
let currentLessonId = null;

// === Upload Zone ===
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');

uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('dragover'); });
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });

async function handleFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['xlsx', 'json'].includes(ext)) {
    showStatus('uploadStatus', '❌ 仅支持 .xlsx 或 .json 文件', 'error');
    return;
  }
  showStatus('uploadStatus', '⏳ 上传中...', 'info');
  const form = new FormData();
  form.append('file', file);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '上传失败');
    currentLessonId = data.lesson_id;
    showStatus('uploadStatus', `✅ 上传成功：${data.title_zh || data.title_en}（${data.sentence_count} 句，${data.vocab_count} 词）`, 'success');
    showPreview(data);
    document.getElementById('generateSection').classList.remove('hidden');
  } catch (err) {
    showStatus('uploadStatus', `❌ ${err.message}`, 'error');
  }
}

function showPreview(data) {
  const card = document.getElementById('previewCard');
  const title = data.title_zh || data.title_en || '未命名课程';
  const level = data.hsk_level || '';
  card.innerHTML = `
    <h3>📋 ${title} ${level ? '<span style="color:#60a5fa;font-size:14px;margin-left:8px">' + level + '</span>' : ''}</h3>
    <div class="preview-stats">
      <span>📝 ${data.sentence_count} 句</span>
      <span>📚 ${data.vocab_count} 词</span>
      <span>📖 ${data.grammar_count} 语法点</span>
    </div>`;
  card.classList.remove('hidden');
}

async function generateVideo() {
  if (!currentLessonId) return;
  const btn = document.getElementById('generateBtn');
  btn.disabled = true;
  btn.textContent = '⏳ 生成中...';
  showStatus('generateStatus', '⏳ 正在生成视频，请稍候（约 1-3 分钟）...', 'info');
  const bar = document.getElementById('progressBar');
  const fill = document.getElementById('progressFill');
  bar.classList.remove('hidden');
  let pct = 0;
  const timer = setInterval(() => { pct = Math.min(pct + 2, 90); fill.style.width = pct + '%'; }, 1000);

  try {
    const voice = document.getElementById('voiceSelect').value;
    const video_format = document.getElementById('formatSelect').value;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 600000); // 10 min timeout
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lesson_id: currentLessonId, voice, video_format }),
      signal: controller.signal
    });
    clearTimeout(timeout);
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { throw new Error('服务器返回异常，可能生成超时，请重试'); }
    clearInterval(timer);
    if (!res.ok) throw new Error(data.error || '生成失败');
    fill.style.width = '100%';
    showStatus('generateStatus', '✅ 视频生成完成！', 'success');
    showDownloads(data.videos);
  } catch (err) {
    clearInterval(timer);
    const msg = err.name === 'AbortError' ? '请求超时（>10分钟），请稍后重试' : err.message;
    showStatus('generateStatus', `❌ ${msg}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '🎬 生成视频';
  }
}

function showDownloads(files) {
  const section = document.getElementById('downloadSection');
  const list = document.getElementById('downloadList');
  list.innerHTML = files.map(f => `
    <a href="${f.url}" class="download-item" download>
      <span class="download-icon">${f.name.includes('vertical') ? '📱' : '🖥️'}</span>
      <span class="download-name">${f.name}</span>
      <span class="download-btn">⬇️ 下载</span>
    </a>`).join('');
  section.classList.remove('hidden');
}

function showStatus(id, msg, type) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className = `status ${type}`;
  el.classList.remove('hidden');
}
