import { create } from "zustand";

const API_BASE = import.meta.env.VITE_API_BASE;

const defaultState = {
  nav: { page: "landing", tab: "artgen" },
  ui: { home: { tabs: { artgen: {}, sim: {}, sweep: {}, model: {}, optimz: {} } } },
};

function getIn(obj, path, fallback) {
  let cur = obj;
  for (const k of path) {
    if (!cur || typeof cur !== "object") return fallback;
    cur = cur[k];
  }
  return cur === undefined ? fallback : cur;
}

function makePatch(path, value) {
  let out = value;
  for (let i = path.length - 1; i >= 0; i--) {
    out = { [path[i]]: out };
  }
  return out;
}

// Very simple deep copy (OK for JSON-like data)
function cloneJson(obj) {
  return JSON.parse(JSON.stringify(obj));
}

export const useUiStore = create((set, get) => ({
  state: defaultState,
  loaded: false,

  load: async () => {
    if (get().loaded) return;
    try {
      const res = await fetch(`${API_BASE}/api/state`);
      const data = await res.json();
      set({ state: data, loaded: true });
    } catch {
      set({ state: defaultState, loaded: true });
    }
  },

  getValue: (path, fallback) => getIn(get().state, path, fallback),

  setValue: async (path, value) => {
    // 1) PATCH backend
    const patch = makePatch(path, value);
    try {
      await fetch(`${API_BASE}/api/state`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
    } catch {
      // ignore for now
    }

    // 2) Update local state
    set((prev) => {
      const next = cloneJson(prev.state);
      let cur = next;
      for (let i = 0; i < path.length - 1; i++) {
        const k = path[i];
        if (!cur[k] || typeof cur[k] !== "object") cur[k] = {};
        cur = cur[k];
      }
      cur[path[path.length - 1]] = value;
      return { state: next };
    });
  },
}));