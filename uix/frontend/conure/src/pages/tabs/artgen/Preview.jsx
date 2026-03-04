import { useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE;


export default function Preview({ draftArtwork }) {
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState(null);
  const [svgText, setSvgText] = useState("");
  const [svgName, setSvgName] = useState(null);
  const [gdsName, setGdsName] = useState(null);
  const [error, setError] = useState("");

  async function generate() {
    setLoading(true);
    setError("");
    setSvgText("");
    setToken(null);
    setSvgName(null);
    setGdsName(null);

    try {
      const res = await fetch(`${API_BASE}/api/preview/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ artwork: draftArtwork }),
      });

      if (!res.ok) {
        let detail = "";
        try {
          const j = await res.json();
          detail = j?.detail
            ? JSON.stringify(j.detail, null, 2)
            : JSON.stringify(j, null, 2);
        } catch {
          detail = await res.text();
        }
        throw new Error(detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setToken(data.token);
      setSvgText(data.svgText || "");
      setSvgName(data.svgName || "artwork.svg");
      setGdsName(data.gdsName || null);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  function download(url) {
    window.open(url, "_blank", "noopener,noreferrer");
  }

  const svgUrl = token ? `${API_BASE}/api/preview/${token}/svg` : null;
  const gdsUrl = token ? `${API_BASE}/api/preview/${token}/gds` : null;

  const svgDataUrl = useMemo(() => {
    if (!svgText) return "";
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgText)}`;
  }, [svgText]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h4>Preview</h4>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={generate} disabled={loading}>
          {loading ? "Generating..." : "Generate Preview"}
        </button>

        <button onClick={() => download(svgUrl)} disabled={!token || !svgUrl}>
          Download SVG
        </button>

        <button
          onClick={() => download(gdsUrl)}
          disabled={!token || !gdsUrl || !gdsName}
          title={!gdsName ? "GDS not generated/found" : ""}
        >
          Download GDS
        </button>
      </div>

      {error && (
        <pre
          style={{
            padding: 12,
            border: "1px solid #f2b8b5",
            background: "#fff5f5",
            color: "#8a1f17",
            whiteSpace: "pre-wrap",
          }}
        >
          {error}
        </pre>
      )}

      {!svgText && !loading && (
        <div style={{ opacity: 0.75 }}>
          Click “Generate Preview” to render the current artwork into an SVG.
        </div>
      )}

      {svgText && (
        <div
          style={{
            border: "1px solid #ccc",
            borderRadius: 8,
            background: "#fafafa",
            padding: 12,
            height: "70vh",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <img
            src={svgDataUrl}
            alt="preview"
            style={{
              maxWidth: "100%",
              maxHeight: "100%",
              width: "auto",
              height: "auto",
              objectFit: "contain",
              display: "block",
            }}
            draggable={false}
          />
        </div>
      )}
    </div>
  );
}