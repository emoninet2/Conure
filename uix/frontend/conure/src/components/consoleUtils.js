/** Shared helpers for Simulate / Sweep / Model process consoles (backend-persisted logs). */

const ANSI_REGEX = /\x1B\[[0-?]*[ -/]*[@-~]/g;

export function stripAnsi(s) {
  return typeof s === "string" ? s.replace(ANSI_REGEX, "") : s;
}

export const CONSOLE_UI = {
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontSize: 12,
  lineHeight: 1.35,
  height: 280,
  border: "1px solid #d0d7de",
  background: "#f6f8fa",
};

export function maxLineTime(lines) {
  let m = 0;
  for (const x of lines || []) {
    const t = typeof x?.t === "number" ? x.t : 0;
    if (t > m) m = t;
  }
  return m;
}

export function appendCapped(prev, msg, cap = 8000) {
  const next = [...prev, msg];
  if (next.length > cap) next.splice(0, next.length - cap);
  return next;
}
