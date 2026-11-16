import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { AssistantPanel } from "../AssistantPanel";
import { usePresence } from "../presence";

export function ProjectPage(props: { id: string }) {
  const presentUsers = usePresence(props.id);
  const [project, setProject] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [notebooks, setNotebooks] = useState<any[]>([]);
  const [tools, setTools] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [comparisonRuns, setComparisonRuns] = useState<string[]>([]);

  const load = async () => {
    try {
      const [p, ds, rs, nbs, ts] = await Promise.all([
        api.get(`/api/projects/${props.id}`),
        api.get(`/api/projects/${props.id}/datasets`),
        api.get(`/api/projects/${props.id}/runs`),
        api.get(`/api/projects/${props.id}/notebooks`),
        api.get("/api/tools"),
      ]);
      setProject(p);
      setDatasets(ds);
      setRuns(rs);
      setNotebooks(nbs);
      setTools(ts);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "failed to load project");
    }
  };
  useEffect(() => {
    load();
  }, [props.id]);

  if (error) return <p className="error-text">{error}</p>;
  if (!project) return null;

  return (
    <>
      <div className="card">
        <h2>{project.name}</h2>
        {project.research_question && (
          <p className="muted">Research question: {project.research_question}</p>
        )}
        <p>
          {project.members.map((m: any) => (
            <span
              className={`chip ${presentUsers.includes(m.username) ? "ok" : ""}`}
              key={m.username}
              title={presentUsers.includes(m.username) ? "online now" : "offline"}
            >
              {presentUsers.includes(m.username) ? "● " : ""}
              {m.username} · {m.role}
            </span>
          ))}
        </p>
        <InviteForm projectId={props.id} myRole={project.my_role} onDone={load} />
      </div>

      <AssistantPanel projectId={props.id} />

      <div className="row">
        <div className="card">
          <h2>Datasets</h2>
          <UploadForm projectId={props.id} onDone={load} />
          {datasets.length === 0 ? (
            <div className="empty">No datasets. Upload a CSV (e.g. sample_data/sample-spectrum.csv).</div>
          ) : (
            <ul className="plain">
              {datasets.map((d) => (
                <li key={d.artifact_id}>
                  <a href={`#/ds/${d.artifact_id}`}>{d.name}</a>{" "}
                  <span className="chip">{d.provenance_label}</span>
                  <span className="muted mono"> {d.sha256.slice(0, 10)}</span>
                  {d.unknowns.length > 0 && (
                    <span className="chip warn">{d.unknowns.length} unknown(s)</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card">
          <h2>Workbench</h2>
          <ul className="plain">
            {tools.map((t) => (
              <li key={t.id}>
                <a href={`#/p/${props.id}/tool/${t.id}`}>{t.name}</a>{" "}
                <span className="chip accent">{t.maturity}</span>
                <span className="chip">{t.category}</span>
                <div className="muted" style={{ fontSize: 12.5 }}>
                  {t.model.name}
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="row">
        <div className="card">
          <h2>Runs</h2>
          {runs.length >= 2 && (
            <div className="field-unit">
              <select value={comparisonRuns[0] ?? ""} onChange={(event) => setComparisonRuns([event.target.value, comparisonRuns[1] ?? ""])}>
                <option value="">Select first completed run</option>
                {runs.filter((run: any) => run.status === "completed").map((run: any) => <option key={run.artifact_id} value={run.artifact_id}>{run.name}</option>)}
              </select>
              <select value={comparisonRuns[1] ?? ""} onChange={(event) => setComparisonRuns([comparisonRuns[0] ?? "", event.target.value])}>
                <option value="">Select second completed run</option>
                {runs.filter((run: any) => run.status === "completed" && run.artifact_id !== comparisonRuns[0]).map((run: any) => <option key={run.artifact_id} value={run.artifact_id}>{run.name}</option>)}
              </select>
              <button disabled={!comparisonRuns[0] || !comparisonRuns[1]} onClick={async () => {
                const comparison = await api.post(`/api/projects/${props.id}/comparisons`, { run_a: comparisonRuns[0], run_b: comparisonRuns[1] });
                window.location.hash = `/compare/${comparison.artifact_id}`;
              }}>Compare and save</button>
            </div>
          )}
          {runs.length === 0 ? (
            <div className="empty">No runs yet — open a Workbench tool.</div>
          ) : (
            <ul className="plain">
              {runs.map((r) => (
                <li key={r.artifact_id}>
                  <a href={`#/run/${r.artifact_id}`}>{r.name}</a>{" "}
                  <span className={`chip ${r.status === "completed" ? "ok" : "error"}`}>
                    {r.status}
                  </span>
                  {r.outputs?.T_eff && (
                    <span className="num muted">
                      T_eff = {r.outputs.T_eff.value.toFixed(1)} K
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card">
          <h2>Notebooks &amp; reports</h2>
          <NotebookForm projectId={props.id} onDone={load} />
          <ul className="plain">
            {notebooks.map((n) => (
              <li key={n.artifact_id}>
                <a href={`#/nb/${n.artifact_id}`}>{n.title}</a>{" "}
                <span className="chip">v{n.version}</span>
              </li>
            ))}
          </ul>
          <ReportList projectId={props.id} notebooks={notebooks} />
        </div>
      </div>

      <div className="card">
        <h2>Activity</h2>
        <ul className="plain">
          {project.recent_activity.map((a: any, i: number) => (
            <li key={i}>
              <span className="mono muted">{a.at.slice(0, 19)}</span> {a.kind}
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

function InviteForm(props: { projectId: string; myRole: string; onDone: () => void }) {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("collaborator");
  const [error, setError] = useState("");
  if (props.myRole !== "owner") return null;
  return (
    <div style={{ display: "flex", gap: 8, alignItems: "flex-end", maxWidth: 520 }}>
      <div style={{ flex: 2 }}>
        <label>Invite member</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="username" />
      </div>
      <div style={{ flex: 1 }}>
        <label>Role</label>
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          {["editor", "collaborator", "reviewer", "viewer"].map((r) => (
            <option key={r}>{r}</option>
          ))}
        </select>
      </div>
      <button
        disabled={!username.trim()}
        onClick={async () => {
          setError("");
          try {
            await api.post(`/api/projects/${props.projectId}/members`, { username, role });
            setUsername("");
            props.onDone();
          } catch (e) {
            setError(e instanceof ApiError ? e.message : "failed");
          }
        }}
      >
        Invite
      </button>
      {error && <span className="error-text">{error}</span>}
    </div>
  );
}

function UploadForm(props: { projectId: string; onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [license, setLicense] = useState("");
  const [label, setLabel] = useState("measured");
  const [error, setError] = useState("");
  return (
    <div style={{ marginBottom: 14 }}>
      <label>CSV file</label>
      <input
        type="file"
        accept=".csv"
        onChange={(e) => {
          const f = e.target.files?.[0] ?? null;
          setFile(f);
          if (f && !name) setName(f.name.replace(/\.csv$/i, ""));
        }}
      />
      <div style={{ display: "flex", gap: 8 }}>
        <div style={{ flex: 2 }}>
          <label>Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div style={{ flex: 1 }}>
          <label>License</label>
          <input value={license} onChange={(e) => setLicense(e.target.value)} placeholder="e.g. CC0-1.0" />
        </div>
        <div style={{ flex: 1 }}>
          <label>Provenance</label>
          <select value={label} onChange={(e) => setLabel(e.target.value)}>
            {["measured", "simulated", "calculated", "estimated"].map((l) => (
              <option key={l}>{l}</option>
            ))}
          </select>
        </div>
      </div>
      {error && <p className="error-text">{error}</p>}
      <div style={{ marginTop: 10 }}>
        <button
          disabled={!file || !name.trim()}
          onClick={async () => {
            setError("");
            const form = new FormData();
            form.append("file", file!);
            form.append("name", name);
            form.append("license", license);
            form.append("provenance_label", label);
            try {
              await api.post(`/api/projects/${props.projectId}/datasets`, form);
              setFile(null);
              setName("");
              props.onDone();
            } catch (e) {
              setError(e instanceof ApiError ? e.message : "upload failed");
            }
          }}
        >
          Upload dataset
        </button>
      </div>
    </div>
  );
}

function NotebookForm(props: { projectId: string; onDone: () => void }) {
  const [title, setTitle] = useState("");
  return (
    <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
      <input
        value={title}
        placeholder="New notebook title"
        onChange={(e) => setTitle(e.target.value)}
      />
      <button
        disabled={!title.trim()}
        onClick={async () => {
          await api.post(`/api/projects/${props.projectId}/notebooks`, { title });
          setTitle("");
          props.onDone();
        }}
      >
        Create
      </button>
    </div>
  );
}

function ReportList(props: { projectId: string; notebooks: any[] }) {
  const [reports, setReports] = useState<any[]>([]);
  const [title, setTitle] = useState("");
  const [notebookId, setNotebookId] = useState("");

  const load = () =>
    api.get(`/api/projects/${props.projectId}/reports`).then(setReports);
  useEffect(() => {
    load();
  }, [props.projectId]);

  const create = async () => {
    await api.post(`/api/projects/${props.projectId}/reports`, {
      title,
      notebook_id: notebookId || props.notebooks[0]?.artifact_id,
    });
    setTitle("");
    load();
  };

  return (
    <>
      <h3>Reports</h3>
      <div style={{ display: "flex", gap: 8 }}>
        <input value={title} placeholder="Report title" onChange={(e) => setTitle(e.target.value)} />
        <select value={notebookId} onChange={(e) => setNotebookId(e.target.value)}>
          {props.notebooks.map((n) => (
            <option key={n.artifact_id} value={n.artifact_id}>
              {n.title}
            </option>
          ))}
        </select>
        <button disabled={!title.trim() || props.notebooks.length === 0} onClick={create}>
          Create
        </button>
      </div>
      <ul className="plain">
        {reports.map((r) => (
          <li key={r.artifact_id}>
            <a href={`#/report/${r.artifact_id}`}>{r.title}</a>
          </li>
        ))}
      </ul>
    </>
  );
}
