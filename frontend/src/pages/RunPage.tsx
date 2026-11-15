import { useEffect, useState } from "react";
import { api } from "../api";
import { Plot } from "../Plot";

export function RunPage(props: { id: string }) {
  const [run, setRun] = useState<any>(null);
  const [fit, setFit] = useState<any>(null);

  useEffect(() => {
    api.get(`/api/runs/${props.id}`).then(async (r) => {
      setRun(r);
      if (r.arrays?.fit) setFit(await api.get(`/api/runs/${props.id}/arrays/fit`));
    });
  }, [props.id]);

  if (!run) return null;

  return (
    <>
      <div className="card">
        <h2>
          {run.name} <span className={`chip ${run.status === "completed" ? "ok" : "error"}`}>{run.status}</span>
          <span className="chip">{run.provenance_label}</span>
        </h2>
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
