// App — Phase 2

// ── State ──────────────────────────────────────────────────────────────────
let currentTea = null;
let currentSteepIndex = 0;
let timer = null;
let audioCtx = null;

// ── Constants ──────────────────────────────────────────────────────────────
const CIRCUMFERENCE = 2 * Math.PI * 90; // ≈ 565.49

// ── Utilities ──────────────────────────────────────────────────────────────
function formatTime(ms) {
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function updateProgress(remainingMs, totalMs) {
  const progressBar = document.getElementById('progress-bar');
  const fraction = totalMs > 0 ? remainingMs / totalMs : 0;
  progressBar.style.strokeDashoffset = CIRCUMFERENCE * (1 - fraction);
  document.getElementById('timer-display').textContent = formatTime(remainingMs);
}

// ── View management ────────────────────────────────────────────────────────
function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(`view-${name}`);
  if (target) target.classList.add('active');
}

function openTimerSheet() {
  document.getElementById('timer-sheet').classList.add('open');
  document.getElementById('sheet-overlay').classList.add('open');
}

function closeTimerSheet() {
  document.getElementById('timer-sheet').classList.remove('open');
  document.getElementById('sheet-overlay').classList.remove('open');
  if (timer) { timer.pause(); timer = null; }
  clearCompletionState();
  renderHome();
}

// ── Timer wiring ───────────────────────────────────────────────────────────
function handleTimerComplete() {
  // 1. Vibration
  if ('vibrate' in navigator) {
    navigator.vibrate([200, 100, 200, 100, 400]);
  }

  // 2. Audio — Web Audio API beep (no external file needed)
  if (audioCtx) {
    try {
      audioCtx.resume().then(() => {
        const playBeep = (freq, start, duration) => {
          const osc = audioCtx.createOscillator();
          const gain = audioCtx.createGain();
          osc.connect(gain);
          gain.connect(audioCtx.destination);
          osc.frequency.value = freq;
          osc.type = 'sine';
          gain.gain.setValueAtTime(0.4, audioCtx.currentTime + start);
          gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + start + duration);
          osc.start(audioCtx.currentTime + start);
          osc.stop(audioCtx.currentTime + start + duration + 0.05);
        };
        playBeep(880, 0, 0.3);
        playBeep(880, 0.4, 0.3);
        playBeep(1100, 0.8, 0.6);
      });
    } catch (e) { /* silent fallback */ }
  }

  // 3. Browser Notification
  const sendNotification = () => {
    const teaName = currentTea ? currentTea.name : '차';
    new Notification('차 우림 완료! ☕', {
      body: `${teaName} ${currentSteepIndex + 1}회차 우림이 완료되었습니다.`,
      icon: 'assets/icon-192.svg'
    });
  };

  if ('Notification' in window) {
    if (Notification.permission === 'granted') {
      sendNotification();
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') sendNotification();
      });
    }
  }

  // 4. Highlight the "다음 우림" button
  const btnNext = document.getElementById('btn-next');
  if (btnNext) {
    btnNext.classList.add('btn-next-pulse');
  }

  // 5. Timer done visual state
  document.getElementById('view-timer').classList.add('timer-done');

  document.getElementById('btn-start-pause').textContent = '시작';
}

function clearCompletionState() {
  document.getElementById('view-timer').classList.remove('timer-done');
  const btnNext = document.getElementById('btn-next');
  if (btnNext) btnNext.classList.remove('btn-next-pulse');
}

function startTimer(tea, steepIndex) {
  // Remove completion state
  clearCompletionState();

  // Cancel any existing timer
  if (timer) {
    timer.pause();
    timer = null;
  }

  currentTea = tea;
  currentSteepIndex = steepIndex;

  const durationSeconds = tea.steeps[steepIndex];

  timer = new Timer(
    durationSeconds,
    (remainingMs, totalMs) => {
      document.getElementById('timer-display').textContent = formatTime(remainingMs);
      updateProgress(remainingMs, totalMs);
    },
    handleTimerComplete
  );

  // Update header
  document.getElementById('timer-tea-name').textContent = tea.name;
  document.getElementById('timer-steep-label').textContent = `${steepIndex + 1}회차`;

  // Update steep info
  document.getElementById('steep-info').textContent =
    `${steepIndex + 1} / ${tea.steeps.length} 회차`;

  // Reset display to full duration
  document.getElementById('timer-display').textContent = formatTime(durationSeconds * 1000);
  updateProgress(durationSeconds * 1000, durationSeconds * 1000);
  document.getElementById('btn-start-pause').textContent = '시작';
}

// ── Button handlers ────────────────────────────────────────────────────────
function unlockAudio() {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) { return; }
  }
  // iOS requires playing a silent buffer during a user gesture to fully unlock audio
  if (audioCtx.state === 'suspended') audioCtx.resume();
  const buf = audioCtx.createBuffer(1, 1, 22050);
  const src = audioCtx.createBufferSource();
  src.buffer = buf;
  src.connect(audioCtx.destination);
  src.start(0);
}

// Re-unlock audio when app comes back to foreground (iOS suspends context on background)
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
});

document.getElementById('btn-start-pause').addEventListener('click', () => {
  unlockAudio();
  if (!timer) return;
  if (timer.state === 'done') {
    timer.reset();
    clearCompletionState();
    document.getElementById('btn-start-pause').textContent = '시작';
    return;
  }
  if (timer.state === 'running') {
    timer.pause();
    document.getElementById('btn-start-pause').textContent = '시작';
  } else if (timer.state === 'idle' || timer.state === 'paused') {
    timer.start();
    document.getElementById('btn-start-pause').textContent = '일시정지';
  }
});

document.getElementById('btn-reset').addEventListener('click', () => {
  if (!timer) return;
  timer.reset();
  clearCompletionState();
  document.getElementById('btn-start-pause').textContent = '시작';
});

document.getElementById('btn-back').addEventListener('click', closeTimerSheet);
document.getElementById('sheet-overlay').addEventListener('click', closeTimerSheet);

document.getElementById('btn-next').addEventListener('click', () => {
  if (!currentTea) return;
  clearCompletionState();
  const nextIndex = currentSteepIndex + 1;
  if (nextIndex >= currentTea.steeps.length) {
    // All steeps done — reset and close sheet
    Storage.clearState(currentTea.id);
    timer = null;
    closeTimerSheet();
    return;
  }
  // Advance to next steep
  Storage.saveState(currentTea.id, nextIndex);
  startTimer(currentTea, nextIndex);
});

// ── Home screen ────────────────────────────────────────────────────────────
function renderHome() {
  const grid = document.getElementById('tea-grid');
  grid.innerHTML = '';
  getActivePresets().forEach(tea => {
    const steepIndex = Storage.loadState(tea.id);
    const card = document.createElement('div');
    card.className = 'tea-card';
    card.innerHTML = `
      <div class="tea-icon">${tea.icon}</div>
      <div class="tea-name">${tea.name}</div>
      <div class="tea-steep">${steepIndex + 1} / ${tea.steeps.length} 회차</div>
      <div class="tea-temp">${tea.temp}</div>
    `;
    card.addEventListener('click', () => {
      selectTea(tea.id);
    });
    grid.appendChild(card);
  });
}

function selectTea(teaId) {
  const tea = getActivePresets().find(t => t.id === teaId);
  if (!tea) return;
  const rawIndex = Storage.loadState(tea.id);
  const steepIndex = Math.min(rawIndex, tea.steeps.length - 1);
  startTimer(tea, steepIndex);
  openTimerSheet();
}

// ── Settings screen ─────────────────────────────────────────────────────────
function renderSettings() {
  const list = document.getElementById('presets-list');
  list.innerHTML = '';
  getActivePresets().forEach(tea => {
    const item = document.createElement('div');
    item.className = 'preset-item';
    const isCustom = !DEFAULT_PRESETS.find(p => p.id === tea.id);
    item.innerHTML = `
      <span class="preset-icon">${tea.icon}</span>
      <div class="preset-info">
        <span class="preset-name">${tea.name}</span>
        <span class="preset-steeps">${tea.steeps.length}회차 · ${tea.temp}</span>
      </div>
      <div class="preset-actions">
        <button class="btn-edit-preset" data-id="${tea.id}">편집</button>
        ${isCustom ? `<button class="btn-delete-preset" data-id="${tea.id}">삭제</button>` : ''}
      </div>
    `;
    list.appendChild(item);
  });
}

// ── Modal logic ─────────────────────────────────────────────────────────────
let modalTeaId = null; // null = adding new preset

function renderSteepsEditor(steeps) {
  const editor = document.getElementById('steeps-editor');
  editor.innerHTML = '';
  steeps.forEach((sec, idx) => {
    const row = document.createElement('div');
    row.className = 'steep-row';
    row.innerHTML = `
      <label>${idx + 1}회차</label>
      <input type="number" min="1" value="${sec}" data-idx="${idx}">
      <button class="btn-remove-steep" data-idx="${idx}">✕</button>
    `;
    editor.appendChild(row);
  });
}

function getSteepsFromEditor() {
  const inputs = document.querySelectorAll('#steeps-editor input[type="number"]');
  const steeps = [];
  inputs.forEach(input => {
    const val = parseInt(input.value, 10);
    if (val > 0) steeps.push(val);
  });
  return steeps;
}

function openEditModal(teaId) {
  const tea = getActivePresets().find(t => t.id === teaId);
  if (!tea) return;
  modalTeaId = teaId;
  const isCustom = !DEFAULT_PRESETS.find(p => p.id === teaId);

  document.getElementById('modal-title').textContent = '차 편집';
  document.getElementById('edit-icon').value = tea.icon;
  document.getElementById('edit-icon').disabled = !isCustom;
  document.getElementById('edit-name').value = tea.name;
  document.getElementById('edit-name').disabled = !isCustom;
  document.getElementById('edit-temp').value = tea.temp;
  document.getElementById('edit-temp').disabled = !isCustom;
  renderSteepsEditor(tea.steeps);
  document.getElementById('modal-overlay').style.display = 'flex';
}

function openAddModal() {
  modalTeaId = null;
  document.getElementById('modal-title').textContent = '새 차 추가';
  document.getElementById('edit-icon').value = '';
  document.getElementById('edit-icon').disabled = false;
  document.getElementById('edit-name').value = '';
  document.getElementById('edit-name').disabled = false;
  document.getElementById('edit-temp').value = '';
  document.getElementById('edit-temp').disabled = false;
  renderSteepsEditor([60]);
  document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
  modalTeaId = null;
}

function saveModal() {
  const steeps = getSteepsFromEditor();
  if (steeps.length === 0) return;

  if (modalTeaId === null) {
    // New custom preset
    const icon = document.getElementById('edit-icon').value.trim() || '🍵';
    const name = document.getElementById('edit-name').value.trim();
    const temp = document.getElementById('edit-temp').value.trim() || '';
    if (!name) return;
    addCustomPreset({
      id: `custom_${Date.now()}`,
      icon,
      name,
      temp,
      steeps
    });
  } else {
    const isCustom = !DEFAULT_PRESETS.find(p => p.id === modalTeaId);
    if (isCustom) {
      // Update custom preset fully
      const customs = Storage.loadCustomPresets();
      const idx = customs.findIndex(p => p.id === modalTeaId);
      if (idx !== -1) {
        customs[idx] = {
          ...customs[idx],
          icon: document.getElementById('edit-icon').value.trim() || customs[idx].icon,
          name: document.getElementById('edit-name').value.trim() || customs[idx].name,
          temp: document.getElementById('edit-temp').value.trim(),
          steeps
        };
        Storage.saveCustomPresets(customs);
      }
    } else {
      // Default preset — only update steeps via override
      updateDefaultSteeps(modalTeaId, steeps);
    }
  }

  closeModal();
  renderSettings();
}

// Settings event listeners
document.getElementById('btn-settings').addEventListener('click', () => {
  renderSettings();
  showView('settings');
});

document.getElementById('btn-settings-back').addEventListener('click', () => {
  showView('home');
  renderHome();
});

document.getElementById('btn-add-preset').addEventListener('click', () => {
  openAddModal();
});

document.getElementById('presets-list').addEventListener('click', e => {
  const editBtn = e.target.closest('.btn-edit-preset');
  const deleteBtn = e.target.closest('.btn-delete-preset');
  if (editBtn) {
    openEditModal(editBtn.dataset.id);
  } else if (deleteBtn) {
    removeCustomPreset(deleteBtn.dataset.id);
    renderSettings();
  }
});

document.getElementById('btn-add-steep').addEventListener('click', () => {
  const inputs = document.querySelectorAll('#steeps-editor input[type="number"]');
  const lastVal = inputs.length > 0 ? parseInt(inputs[inputs.length - 1].value, 10) || 60 : 60;
  const currentSteeps = getSteepsFromEditor();
  currentSteeps.push(lastVal);
  renderSteepsEditor(currentSteeps);
});

document.getElementById('steeps-editor').addEventListener('click', e => {
  const removeBtn = e.target.closest('.btn-remove-steep');
  if (!removeBtn) return;
  const idx = parseInt(removeBtn.dataset.idx, 10);
  const currentSteeps = getSteepsFromEditor();
  currentSteeps.splice(idx, 1);
  renderSteepsEditor(currentSteeps);
});

document.getElementById('btn-modal-cancel').addEventListener('click', closeModal);
document.getElementById('btn-modal-save').addEventListener('click', saveModal);

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  showView('home');
  renderHome();
});
