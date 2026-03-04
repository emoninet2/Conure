import { useEffect, useState } from "react";
import { useUiStore } from "../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function Landing() {
  const load = useUiStore((s) => s.load);
  const setValue = useUiStore((s) => s.setValue);

  const [projects, setProjects] = useState([]);
  const [activeProjectId, setActiveProjectId] = useState(null);

  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    const res = await fetch(`${API_BASE}/api/projects`);
    const data = await res.json();
    setProjects(data.projects || []);
    setActiveProjectId(data.activeProjectId || null);
  }

  useEffect(() => {
    refresh().catch((e) => setError(e?.message || String(e)));
  }, []);

  async function createProject() {
    const n = name.trim();
    if (!n) return;

    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: n }),
      });

      if (!res.ok) {
        const j = await res.json().catch(() => null);
        throw new Error(j?.detail || (await res.text()));
      }

      setName("");
      await refresh();
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function openProject(id, name) {

    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/projects/${id}/open`, { method: "POST" });
      if (!res.ok) {
        const j = await res.json().catch(() => null);
        throw new Error(j?.detail || (await res.text()));
      }

      // Now that a project is open, load project.json into zustand store
      await load();

      setValue(["project", "name"], name);

      // Go to Home
      setValue(["nav", "page"], "home");

      await refresh();
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function deleteProject(id) {
    if (!confirm("Delete this project? This cannot be undone.")) return;

    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/projects/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const j = await res.json().catch(() => null);
        throw new Error(j?.detail || (await res.text()));
      }
      await refresh();
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: 16, maxWidth: 900 }}>
      <h1>Conure</h1>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center", marginBottom: 16 }}>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New project name"
          style={{ minWidth: 280 }}
          onKeyDown={(e) => e.key === "Enter" && createProject()}
        />
        <button onClick={createProject} disabled={busy || !name.trim()}>
          Create Project
        </button>
        <button onClick={() => refresh()} disabled={busy}>
          Refresh
        </button>
      </div>

      {error && (
        <pre style={{ padding: 12, border: "1px solid #f2b8b5", background: "#fff5f5", color: "#8a1f17" }}>
          {error}
        </pre>
      )}

      <div style={{ border: "1px solid #ddd", borderRadius: 8, overflow: "hidden", marginTop: 12 }}>
        <div style={{ padding: 10, background: "#fafafa", borderBottom: "1px solid #eee" }}>
          <strong>Projects</strong>
        </div>

        {projects.length === 0 ? (
          <div style={{ padding: 12, opacity: 0.75 }}>No projects yet. Create one above.</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>Name</th>
                <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #eee" }}>Status</th>
                <th style={{ padding: 10, borderBottom: "1px solid #eee", width: 260 }} />
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td style={{ padding: 10, borderBottom: "1px solid #f2f2f2" }}>
                    <div style={{ fontWeight: 600 }}>{p.name}</div>
                    <div style={{ opacity: 0.7, fontSize: 12 }}>{p.id}</div>
                  </td>

                  <td style={{ padding: 10, borderBottom: "1px solid #f2f2f2" }}>
                    {p.id === activeProjectId ? (
                      <span style={{ color: "green", fontWeight: 600 }}>Open</span>
                    ) : (
                      <span style={{ opacity: 0.75 }}>—</span>
                    )}
                  </td>

                  <td style={{ padding: 10, borderBottom: "1px solid #f2f2f2", textAlign: "right" }}>
                    <button onClick={() => openProject(p.id, p.name)} disabled={busy} style={{ marginRight: 8 }}>
                      Open
                    </button>
                    <button onClick={() => deleteProject(p.id)} disabled={busy}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}