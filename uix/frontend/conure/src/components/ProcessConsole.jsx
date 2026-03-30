/**
 * Shared process output panel: monospace log, auto-scroll toggle, optional clear.
 * Log lines are loaded from the API; live updates come from EventSource elsewhere.
 */

import { CONSOLE_UI, stripAnsi } from "./consoleUtils";

export default function ProcessConsole({
  title = "Output",
  lines,
  running,
  emptyIdle,
  emptyRunning,
  autoScroll,
  onAutoScrollChange,
  onScrollContainer,
  scrollerRef,
  onClear,
  clearDisabled,
  clearLabel = "Clear console",
  extraControls = null,
}) {
  return (
    <div style={{ marginTop: 12 }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 10,
          marginBottom: 6,
        }}
      >
        <div style={{ fontSize: 12, opacity: 0.75, fontWeight: 600 }}>{title}</div>
        <label
          style={{
            display: "inline-flex",
            gap: 6,
            alignItems: "center",
            fontSize: 12,
            cursor: "pointer",
            userSelect: "none",
          }}
        >
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => onAutoScrollChange(!!e.target.checked)}
          />
          Auto-scroll
        </label>
        <button
          type="button"
          onClick={onClear}
          disabled={clearDisabled}
          style={{
            fontSize: 12,
            padding: "4px 10px",
            borderRadius: 6,
            border: "1px solid #cfd6e4",
            background: "#fff",
          }}
        >
          {clearLabel}
        </button>
        {extraControls}
      </div>

      <div
        ref={scrollerRef}
        onScroll={onScrollContainer}
        style={{
          height: CONSOLE_UI.height,
          overflow: "auto",
          padding: 12,
          border: CONSOLE_UI.border,
          borderRadius: 8,
          background: CONSOLE_UI.background,
          whiteSpace: "pre-wrap",
          fontFamily: CONSOLE_UI.fontFamily,
          fontSize: CONSOLE_UI.fontSize,
          lineHeight: CONSOLE_UI.lineHeight,
          marginBottom: 0,
        }}
      >
        {lines.length === 0 ? (
          <span style={{ opacity: 0.62 }}>{running ? emptyRunning : emptyIdle}</span>
        ) : (
          lines.map((x, i) => (
            <div key={i} style={{ wordBreak: "break-word" }}>
              {typeof x?.line === "string" ? stripAnsi(x.line) : JSON.stringify(x)}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
