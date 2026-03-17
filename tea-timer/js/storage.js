const Storage = {
  saveState(teaId, steepIndex) {
    try { localStorage.setItem(`tea_state_${teaId}`, String(steepIndex)); } catch (e) { /* ignore */ }
  },

  loadState(teaId) {
    try {
      const v = localStorage.getItem(`tea_state_${teaId}`);
      const n = parseInt(v, 10);
      return Number.isNaN(n) ? 0 : n;
    } catch (e) { return 0; }
  },

  clearState(teaId) {
    try { localStorage.removeItem(`tea_state_${teaId}`); } catch (e) { /* ignore */ }
  }
};
