const DEFAULT_PRESETS = [
  { id: "green", name: "녹차", icon: "🍵", temp: "70-80°C", steeps: [120, 90, 120, 150, 180] },
  { id: "black", name: "홍차", icon: "🫖", temp: "90-100°C", steeps: [180, 180, 240] },
  { id: "oolong", name: "우롱차", icon: "🍃", temp: "85-95°C", steeps: [60, 45, 60, 75, 90, 120] },
  { id: "puerh", name: "보이차", icon: "🏔️", temp: "95-100°C", steeps: [10, 15, 20, 25, 30, 35, 40, 45] },
  { id: "white", name: "백차", icon: "🤍", temp: "75-85°C", steeps: [120, 90, 120, 150] }
];

Object.freeze(DEFAULT_PRESETS);
DEFAULT_PRESETS.forEach(Object.freeze);
