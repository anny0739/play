// App — Phase 2

// ── State ──────────────────────────────────────────────────────────────────
let currentTea = null;
let currentSteepIndex = 0;
let timer = null;

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
  // Phase 4: audio/vibration will be added here
  console.log('Timer complete!');
  document.getElementById('btn-start-pause').textContent = '시작';
}

function startTimer(tea, steepIndex) {
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
  if (!timer) return;
  if (timer.state === 'done') {
    timer.reset();
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
  document.getElementById('btn-start-pause').textContent = '시작';
});

document.getElementById('btn-back').addEventListener('click', () => {
  if (timer) {
    timer.pause();
  }
  showView('home');
});

// Phase 3: btn-next and home view will be wired here
document.getElementById('btn-next').addEventListener('click', () => {
  // stub — Phase 3
  console.log('btn-next: Phase 3');
});

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  showView('home');
});
