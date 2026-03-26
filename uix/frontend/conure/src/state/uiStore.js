import { create } from "zustand";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const defaultState = {
  project: { id: null, name: null },
  nav: { page: "landing", tab: "artgen" },
  ui: {
    home: {
      tabs: {
        artgen: {},
        sim: {},
        sweep: {},
        model: {},
        optimz: {},
      },
    },
  },
  artwork: {},
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

function cloneJson(obj) {
  return JSON.parse(JSON.stringify(obj));
}

export const useUiStore = create((set, get) => ({
  state: defaultState,
  loaded: false,

  load: async ({ force = false } = {}) => {
    if (get().loaded && !force) return;

    try {
      const res = await fetch(`${API_BASE}/api/state`);
      if (!res.ok) {
        throw new Error(await res.text());
      }

      const data = await res.json();

      set({
        state: {
          ...cloneJson(defaultState),
          ...(data || {}),
        },
        loaded: true,
      });
    } catch {
      set({
        state: cloneJson(defaultState),
        loaded: true,
      });
    }
  },

  reload: async () => {
    return get().load({ force: true });
  },

  resetLoaded: () => set({ loaded: false }),

  getValue: (path, fallback) => getIn(get().state, path, fallback),

  setValue: async (path, value) => {
    const patch = makePatch(path, value);

    const res = await fetch(`${API_BASE}/api/state`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

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

  replaceState: (nextState) =>
    set({
      state: {
        ...cloneJson(defaultState),
        ...(nextState || {}),
      },
      loaded: true,
    }),
}));