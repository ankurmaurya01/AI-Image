let currentImage = null;

// Connect to Backend and Database
fetch('/api/stats')
  .then(res => res.json())
  .then(data => {
    document.getElementById('srvStatus').textContent = 'Online';
    document.getElementById('dbStatus').textContent = `📁 Database: ${data.database.total_images.toLocaleString()} images`;
  })
  .catch(() => {
    document.getElementById('srvStatus').textContent = 'Offline';
    document.getElementById('dbStatus').textContent = '📁 Database: Disconnected';
  });

function loadFile(file) {
  if (!file) return;
  currentImage = file;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('imgElem').src = e.target.result;
    showPreview();
  };
  reader.readAsDataURL(file);
}

function loadSample(type) {
  fetch(`/api/sample?type=${type}`)
    .then(res => res.json())
    .then(data => {
      document.getElementById('imgElem').src = data.image_b64;
      currentImage = data.image_b64;
      showPreview();
    })
    .catch(err => alert('Failed to fetch database sample: ' + err));
}

function showPreview() {
  document.getElementById('dz').style.display = 'none';
  document.getElementById('prevBox').style.display = 'flex';
  document.getElementById('resBox').style.display = 'none';
}

function resetUI() {
  currentImage = null;
  document.getElementById('fileInput').value = '';
  document.getElementById('dz').style.display = 'block';
  document.getElementById('prevBox').style.display = 'none';
  document.getElementById('resBox').style.display = 'none';
}

async function predict() {
  if (!currentImage) return;
  const runBtn = document.getElementById('runBtn');
  runBtn.textContent = 'Analyzing...';
  runBtn.disabled = true;

  const formData = new FormData();
  if (typeof currentImage === 'string') {
    formData.append('image_b64', currentImage);
  } else {
    formData.append('image', currentImage);
  }

  try {
    const res = await fetch('/api/predict', { method: 'POST', body: formData });
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const isReal = data.label === 'Real';
    const badge = document.getElementById('vBadge');
    badge.textContent = isReal ? '✔ Authentic Real Photo' : '⚠ AI-Generated Image';
    badge.className = 'badge ' + (isReal ? 'badge-real' : 'badge-fake');
    document.getElementById('confText').textContent = data.confidence.toFixed(1) + '%';

    const rP = data.probabilities['Real'] || 0;
    const fP = data.probabilities['AI-generated'] || 0;
    document.getElementById('rProb').textContent = rP.toFixed(1) + '%';
    document.getElementById('fProb').textContent = fP.toFixed(1) + '%';

    const bar = document.getElementById('probBar');
    bar.style.width = (isReal ? rP : fP) + '%';
    bar.className = 'bar-fill ' + (isReal ? 'real-fill' : 'fake-fill');

    document.getElementById('resBox').style.display = 'block';
  } catch (err) {
    alert('Prediction error: ' + err.message);
  } finally {
    runBtn.textContent = '⚡ Analyze Image';
    runBtn.disabled = false;
  }
}

// Event Listeners
document.getElementById('dz').addEventListener('click', () => document.getElementById('fileInput').click());
document.getElementById('fileInput').addEventListener('change', e => loadFile(e.target.files[0]));
document.getElementById('btnSampleReal').addEventListener('click', () => loadSample('real'));
document.getElementById('btnSampleFake').addEventListener('click', () => loadSample('fake'));
document.getElementById('runBtn').addEventListener('click', predict);
document.getElementById('resetBtn').addEventListener('click', resetUI);

// Drag-and-drop
const dropzone = document.getElementById('dz');
['dragenter', 'dragover'].forEach(name => dropzone.addEventListener(name, e => {
  e.preventDefault();
  dropzone.style.borderColor = '#6366f1';
}));
['dragleave', 'drop'].forEach(name => dropzone.addEventListener(name, e => {
  e.preventDefault();
  dropzone.style.borderColor = '#334155';
}));
dropzone.addEventListener('drop', e => {
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    loadFile(e.dataTransfer.files[0]);
  }
});
