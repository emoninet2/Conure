import { useEffect, useState } from "react";
import { IconOpen, IconPencil, IconTrash } from "../icons/actionIcons";
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

      // IMPORTANT: fully load the newly opened project state
      //await load();
      await load({ force: true });

      // IMPORTANT: explicitly set project identity
      setValue(["project", "id"], id);
      setValue(["project", "name"], name);

      // optional: reset visible tab on project switch
      setValue(["nav", "tab"], "artgen");

      // go to home
      setValue(["nav", "page"], "home");

      await refresh();
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function renameProject(id, displayName) {
    const next = window.prompt(`Rename project "${displayName}" to:`, displayName);
    if (next == null) return;
    const trimmed = next.trim();
    if (!trimmed || trimmed === displayName) return;

    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/projects/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from_id: id, to_name: trimmed }),
      });
      if (!res.ok) {
        const j = await res.json().catch(() => null);
        throw new Error(j?.detail || (await res.text()));
      }

      const data = await res.json();
      const newId = data.id;
      const newName = data.name ?? trimmed;

      if (activeProjectId === id) {
        setValue(["project", "id"], newId);
        setValue(["project", "name"], newName);
        await load({ force: true });
      }

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

  const iconBtn = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: 36,
    height: 36,
    padding: 0,
    borderRadius: 8,
    border: "1px solid #e2e8f0",
    background: "#fff",
    flexShrink: 0,
    cursor: "pointer",
  };

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
                <th style={{ padding: 10, borderBottom: "1px solid #eee", width: 148 }} />
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
                    <div style={{ display: "inline-flex", gap: 6, alignItems: "center", justifyContent: "flex-end" }}>
                      <button
                        type="button"
                        onClick={() => openProject(p.id, p.name)}
                        disabled={busy}
                        aria-label={`Open project ${p.name}`}
                        title="Open this project"
                        style={{ ...iconBtn, color: "#1e40af" }}
                      >
                        <IconOpen />
                      </button>
                      <button
                        type="button"
                        onClick={() => renameProject(p.id, p.name)}
                        disabled={busy}
                        aria-label={`Rename project ${p.name}`}
                        title="Rename this project"
                        style={{ ...iconBtn, color: "#334155" }}
                      >
                        <IconPencil />
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteProject(p.id)}
                        disabled={busy}
                        aria-label={`Delete project ${p.name}`}
                        title="Delete this project"
                        style={{ ...iconBtn, color: "#7f1d1d" }}
                      >
                        <IconTrash />
                      </button>
                    </div>
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