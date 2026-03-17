// Timer — Phase 2
class Timer {
  constructor(durationSeconds, onTick, onComplete) {
    this.duration = durationSeconds * 1000; // ms
    this.remaining = this.duration;
    this.onTick = onTick;       // called with (remainingMs, totalMs)
    this.onComplete = onComplete;
    this._rafId = null;
    this._startTime = null;
    this.state = 'idle'; // 'idle' | 'running' | 'paused' | 'done'
  }

  start() {
    if (this.state === 'done') return;
    if (this.state === 'running') return;
    this.state = 'running';
    this._startTime = Date.now() - (this.duration - this.remaining);
    this._tick();
  }

  pause() {
    if (this.state !== 'running') return;
    this.state = 'paused';
    cancelAnimationFrame(this._rafId);
  }

  reset() {
    cancelAnimationFrame(this._rafId);
    this.state = 'idle';
    this.remaining = this.duration;
    this._startTime = null;
    this.onTick && this.onTick(this.remaining, this.duration);
  }

  _tick() {
    const elapsed = Date.now() - this._startTime;
    this.remaining = Math.max(0, this.duration - elapsed);
    this.onTick && this.onTick(this.remaining, this.duration);
    if (this.remaining <= 0) {
      this.state = 'done';
      this.onComplete && this.onComplete();
      return;
    }
    this._rafId = requestAnimationFrame(() => this._tick());
  }
}
