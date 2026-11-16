import { useEffect, useState } from "react";
import { api } from "../api";
import { Plot } from "../Plot";

export function RunPage(props: { id: string }) {
  const [run, setRun] = useState<any>(null);
  const [fit, setFit] = useState<any>(null);
  const [geometry, setGeometry] = useState<any>(null);
  const [lineage, setLineage] = useState<any[]>([]);
  const [comments, setComments] = useState<any[]>([]);
  const [commentText, setCommentText] = useState("");
  const [reviewMsg, setReviewMsg] = useState("");

  const loadData = async () => {
    const r = await api.get(`/api/runs/${props.id}`);
    setRun(r);
    if (r.arrays?.fit) setFit(await api.get(`/api/runs/${props.id}/arrays/fit`));
    if (r.arrays?.geometry) setGeometry(await api.get(`/api/runs/${props.id}/arrays/geometry`));
    try {
      const l = await api.get(`/api/runs/${props.id}/lineage`);
      setLineage(l);
    } catch {}
    try {
      const c = await api.get(`/api/artifacts/${props.id}/comments?include_resolved=true`);
      setComments(c);
    } catch {}
  };

  useEffect(() => {
    loadData();
  }, [props.id]);

  if (!run) return null;

  const updateReview = async (state: string) => {
    try {
      const res = await api.patch(`/api/artifacts/${props.id}/review`, { state });
      setReviewMsg(res.message || `State updated to ${state}`);
      setRun({ ...run, review_state: state });
    } catch (e: any) {
      setReviewMsg(e?.detail || "Review update failed");
    }
  };

  const addComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    try {
      await api.post(`/api/artifacts/${props.id}/comments`, { text: commentText });
      setCommentText("");
      const c = await api.get(`/api/artifacts/${props.id}/comments?include_resolved=true`);
      setComments(c);
    } catch {}
  };

  const resolveComment = async (commentId: string, resolved: boolean) => {
    try {
      await api.patch(`/api/comments/${commentId}`, { resolved });
      const c = await api.get(`/api/artifacts/${props.id}/comments?include_resolved=true`);
      setComments(c);
    } catch {}
  };

  return (
    <>
      {lineage.length > 1 && (
        <div className="card" style={{ padding: "8px 16px", marginBottom: 12 }}>
          <span className="muted" style={{ marginRight: 8 }}>Lineage:</span>
          {lineage.slice().reverse().map((item, idx) => (
            <span key={item.artifact_id}>
              {idx > 0 && " → "}
              {item.artifact_id === props.id ? (
                <strong>{item.name} (this run)</strong>
              ) : (
                <a href={`#/runs/${item.artifact_id}`}>{item.name}</a>
              )}
            </span>
          ))}
        </div>
      )}

      <div className="card">
        <h2>
          {run.name} <span className={`chip ${run.status === "completed" ? "ok" : "error"}`}>{run.status}</span>
          <span className="chip">{run.provenance_label}</span>
          <span className={`chip ${run.review_state === "approved" ? "ok" : run.review_state === "needs-review" ? "warn" : ""}`}>
            Review: {run.review_state || "draft"}
          </span>
        </h2>
        <div style={{ display: "flex", gap: 8, alignItems: "center", margin: "8px 0" }}>
          {run.project_id && (
            <a
              href={`#/p/${run.project_id}/tool/${run.tool_id}?parent_run=${run.artifact_id}`}
              className="chip accent"
              style={{ textDecoration: "none" }}
            >
              + Create Variant
            </a>
          )}
          <button className="chip" onClick={() => updateReview("needs-review")}>Request Review</button>
          <button className="chip ok" onClick={() => updateReview("approved")}>Approve</button>
          {reviewMsg && <span className="muted" style={{ fontSize: 13 }}>{reviewMsg}</span>}
        </div>
        <p className="muted">
          <code>
            {run.tool_id}@{run.tool_version}
          </code>{" "}
          · {run.model_name} · {run.method.name}
        </p>
        {run.error && <p className="error-text">{run.error}</p>}
        {fit && (
          <Plot
            series={[
              { x: fit.columns.wavelength.map((w: number) => w * 1e9), y: fit.columns.flux, name: "data" },
              { x: fit.columns.wavelength.map((w: number) => w * 1e9), y: fit.columns.fitted, name: "fitted", mode: "lines" },
              { x: fit.columns.wavelength.map((w: number) => w * 1e9), y: fit.columns.residual, name: "residual" },
            ]}
            xLabel="wavelength [nm]"
            yLabel="flux [arb]"
          />
        )}
        {geometry && (
          <Plot
            series={[{
              x: geometry.columns.angle.map((angle: number) => angle * 180 / Math.PI),
              y: geometry.columns.differential_cross_section,
              name: "Klein–Nishina",
              mode: "lines",
            }]}
            xLabel="scattering angle [deg]"
            yLabel="dσ/dΩ [m²/sr]"
          />
        )}
        {Object.keys(run.arrays ?? {}).filter((name: string) => !["fit", "geometry"].includes(name)).map((name: string) => (
          <SavedArray key={name} runId={props.id} name={name} />
        ))}
      </div>

      <div className="row">
        <div className="card">
          <h2>Outputs</h2>
          <table>
            <tbody>
              {Object.entries(run.outputs).map(([name, out]: [string, any]) => (
                <tr key={name}>
                  <th>{name}</th>
                  <td className="num">
                    {Number(out.value).toPrecision(8)}
                    {out.sigma != null && ` ± ${Number(out.sigma).toPrecision(3)}`}
                  </td>
                  <td>{out.unit || "dimensionless"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {run.guards.map((g: string, i: number) => (
            <div className="guard" key={i}>{g}</div>
          ))}
          <h3>Checks</h3>
          <ul className="plain">
            {run.checks.map((c: any, i: number) => (
              <li key={i}>
                <span className={`chip ${c.passed ? "ok" : "error"}`}>{c.passed ? "pass" : "FAIL"}</span>
                {c.name}: {c.detail}
              </li>
            ))}
          </ul>
          {run.warnings.length > 0 && (
            <>
              <h3>Warnings</h3>
              <ul className="plain">{run.warnings.map((w: string, i: number) => <li key={i}>{w}</li>)}</ul>
            </>
          )}

          <h3 style={{ marginTop: 24 }}>Artifact Comments</h3>
          <ul className="plain">
            {comments.map((c) => (
              <li key={c.id} style={{ opacity: c.resolved ? 0.6 : 1, marginBottom: 8 }}>
                <span className={`chip ${c.resolved ? "" : "accent"}`}>{c.resolved ? "resolved" : "open"}</span>{" "}
                <span>{c.text}</span>
                <span className="muted" style={{ fontSize: 11, marginLeft: 8 }}>{c.created_at.slice(0, 19)}</span>
                <button
                  style={{ marginLeft: 8, padding: "2px 6px", fontSize: 11 }}
                  onClick={() => resolveComment(c.id, !c.resolved)}
                >
                  {c.resolved ? "Reopen" : "Resolve"}
                </button>
              </li>
            ))}
          </ul>
          <form onSubmit={addComment} style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <input
              type="text"
              placeholder="Add comment on this artifact…"
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit">Post</button>
          </form>
        </div>

        <div className="card">
          <h2>Provenance</h2>
          <h3>Inputs (canonical units)</h3>
          <table>
            <tbody>
              {Object.entries(run.inputs).map(([name, spec]: [string, any]) => (
                <tr key={name}>
                  <th>{name}</th>
                  <td className="num">{Number(spec.value).toPrecision(8)}</td>
                  <td>{spec.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {Object.keys(run.input_artifacts).length > 0 && (
            <>
              <h3>Input artifacts</h3>
              <ul className="plain">
                {Object.entries(run.input_artifacts).map(([name, b]: [string, any]) => (
                  <li key={name}>
                    {name}: <a href={`#/ds/${b.artifact_id}`} className="mono">{b.artifact_id.slice(0, 10)}</a>
                    @v{b.version} <span className="chip">{b.provenance_label}</span>
                    <div className="mono muted" style={{ fontSize: 11.5 }}>sha256 {b.sha256.slice(0, 20)}…</div>
                  </li>
                ))}
              </ul>
            </>
          )}
          <h3>Assumptions</h3>
          <ul className="plain muted">
            {run.assumptions.map((a: string, i: number) => <li key={i}>{a}</li>)}
          </ul>
          <h3>Environment</h3>
          <ul className="plain mono" style={{ fontSize: 12 }}>
            {Object.entries(run.environment).map(([k, v]) => (
              <li key={k}>
                {k}: {String(v)}
              </li>
            ))}
          </ul>
          <p className="muted">
            Started {run.started_at?.slice(0, 19)} · finished {run.finished_at?.slice(0, 19)}
          </p>
        </div>
      </div>
    </>
  );
}

function SavedArray(props: { runId: string; name: string }) {
  const [array, setArray] = useState<any>(null);
  const [promoted, setPromoted] = useState<string>("");

  useEffect(() => {
    api.get(`/api/runs/${props.runId}/arrays/${props.name}`).then(setArray);
  }, [props.runId, props.name]);

  if (!array) return null;
  const columns = array.columns ?? {};
  const xKey = "position" in columns ? "position" : "angle" in columns ? "angle" : "x" in columns ? "x" : Object.keys(columns)[0];
  const yKeys = Object.keys(columns).filter((key) => key !== xKey && key !== "residual");

  const promote = async () => {
    try {
      const res = await api.post(`/api/runs/${props.runId}/arrays/${props.name}/promote`, {});
      setPromoted(res.artifact_id);
    } catch {}
  };

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h4 style={{ margin: 0 }}>Array: {props.name}</h4>
        {promoted ? (
          <span className="chip ok">Promoted to Dataset: <a href={`#/ds/${promoted}`}>{promoted.slice(0, 8)}…</a></span>
        ) : (
          <button className="chip" onClick={promote}>Promote to Dataset</button>
        )}
      </div>
      <Plot series={yKeys.map((key) => ({
        x: columns[xKey].map((value: number) => xKey === "position" ? value * 1e9 : xKey === "angle" ? value * 180 / Math.PI : value),
        y: columns[key],
        name: key,
        mode: ["fitted", "potential", "probability_density", "differential_cross_section"].includes(key) ? "lines" : "markers",
      }))} xLabel={`${xKey}${xKey === "position" ? " [nm]" : xKey === "angle" ? " [deg]" : ""}`} yLabel={yKeys.join(", ")} />
    </div>
  );
}
