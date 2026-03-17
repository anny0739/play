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
document.getElementById('btn-start-pause').addEventListener('click', () => {
  if (!audioCtx) {
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) { audioCtx = null; }
  }
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

document.getElementById('btn-back').addEventListener('click', () => {
  if (timer) { timer.pause(); timer = null; }
  clearCompletionState();
  renderHome();
  showView('home');
});

document.getElementById('btn-next').addEventListener('click', () => {
  if (!currentTea) return;
  clearCompletionState();
  const nextIndex = currentSteepIndex + 1;
  if (nextIndex >= currentTea.steeps.length) {
    // All steeps done — reset to 0 and go back home
    Storage.clearState(currentTea.id);
    timer = null;
    showView('home');
    renderHome();
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
  DEFAULT_PRESETS.forEach(tea => {
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
  const tea = DEFAULT_PRESETS.find(t => t.id === teaId);
  if (!tea) return;
  const rawIndex = Storage.loadState(tea.id);
  const steepIndex = Math.min(rawIndex, tea.steeps.length - 1);
  startTimer(tea, steepIndex);
  showView('timer');
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  showView('home');
  renderHome();
});
