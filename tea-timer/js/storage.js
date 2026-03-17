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
  },

  saveCustomPresets(presets) {
    try { localStorage.setItem('custom_presets', JSON.stringify(presets)); } catch (e) { /* ignore */ }
  },

  loadCustomPresets() {
    try {
      const v = localStorage.getItem('custom_presets');
      const parsed = JSON.parse(v);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) { return []; }
  },

  saveSteepOverride(teaId, steeps) {
    try { localStorage.setItem(`steep_override_${teaId}`, JSON.stringify(steeps)); } catch (e) { /* ignore */ }
  },

  loadSteepOverride(teaId) {
    try {
      const v = localStorage.getItem(`steep_override_${teaId}`);
      if (v === null) return null;
      const parsed = JSON.parse(v);
      return Array.isArray(parsed) ? parsed : null;
    } catch (e) { return null; }
  },

  clearSteepOverride(teaId) {
    try { localStorage.removeItem(`steep_override_${teaId}`); } catch (e) { /* ignore */ }
  }
};
