import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { Plot } from "../Plot";

const UNIT_CHOICES: Record<string, string[]> = {
  m: ["nm", "Angstrom", "um", "m"],
  K: ["K"],
  J: ["eV", "keV", "MeV", "J"],
  rad: ["deg", "rad"],
  kg: ["kg"],
  "": [""],
};

export function ToolPage(props: { projectId: string; toolId: string }) {
  const hash = window.location.hash;
  const searchIndex = hash.indexOf("?");
  const searchParams = searchIndex !== -1 ? new URLSearchParams(hash.slice(searchIndex)) : new URLSearchParams();
  const parentRunId = searchParams.get("parent_run");

  const [contract, setContract] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [notebooks, setNotebooks] = useState<any[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [units, setUnits] = useState<Record<string, string>>({});
  const [bindings, setBindings] = useState<Record<string, string>>({});
  const [parentRun, setParentRun] = useState<any>(null);
  const [run, setRun] = useState<any>(null);
  const [fitArray, setFitArray] = useState<any>(null);
  const [geometryArray, setGeometryArray] = useState<any>(null);
  const [tunnelingArrays, setTunnelingArrays] = useState<Record<string, any>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [addedTo, setAddedTo] = useState("");

  useEffect(() => {
    api.get(`/api/tools/${props.toolId}`).then((c) => {
      setContract(c);
      const u: Record<string, string> = {};
      for (const input of c.inputs) u[input.name] = UNIT_CHOICES[input.canonical_unit]?.[0] ?? input.canonical_unit;
      setUnits(u);
    });
    api.get(`/api/projects/${props.projectId}/datasets`).then(setDatasets);
    api.get(`/api/projects/${props.projectId}/notebooks`).then(setNotebooks);
    if (parentRunId) {
      api.get(`/api/runs/${parentRunId}`).then((r) => {
        setParentRun(r);
        const v: Record<string, string> = {};
        for (const [k, spec] of Object.entries(r.inputs || {})) {
          v[k] = String((spec as any).value);
        }
        setValues((prev) => ({ ...v, ...prev }));
      }).catch(() => {});
    }
  }, [props.toolId, props.projectId, parentRunId]);

  if (!contract) return null;

  const execute = async () => {
    setBusy(true);
    setError("");
    setRun(null);
    setFitArray(null);
    setGeometryArray(null);
    setTunnelingArrays({});
    setAddedTo("");
    const inputs: Record<string, any> = {};
    for (const input of contract.inputs) {
      const raw = values[input.name];
      if (raw !== undefined && raw !== "") {
        inputs[input.name] = { value: Number(raw), unit: units[input.name] };
      }
    }
    try {
      const result = await api.post(`/api/projects/${props.projectId}/runs`, {
        tool_id: props.toolId,
        inputs,
        datasets: bindings,
        parent_run: parentRunId || undefined,
      });
      setRun(result);
      if (result.arrays?.fit) {
        setFitArray(await api.get(`/api/runs/${result.artifact_id}/arrays/fit`));
      }
      if (result.arrays?.geometry) {
        setGeometryArray(await api.get(`/api/runs/${result.artifact_id}/arrays/geometry`));
      }
      const plottedArrays: Record<string, any> = {};
      for (const name of ["barrier_profile", "wavefunction", "residuals", "energy_sweep"]) {
        if (result.arrays?.[name]) plottedArrays[name] = await api.get(`/api/runs/${result.artifact_id}/arrays/${name}`);
      }
      setTunnelingArrays(plottedArrays);
    } catch (e) {
      if (e instanceof ApiError && typeof e.detail === "object" && e.detail !== null) {
        const d = e.detail as any;
        setError(d.input_errors ? d.input_errors.join("; ") : JSON.stringify(d));
      } else {
        setError(e instanceof ApiError ? String(e.detail) : "run failed");
      }
    } finally {
      setBusy(false);
    }
  };

  const addToNotebook = async (notebookId: string) => {
    await api.post(`/api/notebooks/${notebookId}/blocks`, {
      type: "figure",
      content: {
        run_artifact_id: run.artifact_id,
        array: Object.keys(run.arrays)[0],
        caption: `${contract.name} — ${run.name}`,
      },
    });
    setAddedTo(notebookId);
  };

  return (
    <>
      <div className="card">
        {parentRunId && (
          <div style={{ padding: "8px 12px", marginBottom: 12, borderRadius: 4, background: "rgba(59, 130, 246, 0.15)", border: "1px solid rgba(59, 130, 246, 0.3)" }}>
            <strong>Creating Variant:</strong> Branching from parent run{" "}
            <a href={`#/runs/${parentRunId}`}>{parentRun?.name || parentRunId}</a>
          </div>
        )}
        <h2>
          {contract.name}{" "}
          <span className="chip accent">{contract.maturity}</span>
          <span className="chip">{contract.category}</span>
          <span className="chip">{contract.domain}</span>
        </h2>
        <p className="muted">{contract.model.name} · v{contract.version}</p>
        <a href={`#/p/${props.projectId}`}>← back to project</a>
      </div>

      <div className="row">
        <div className="card">
          <h2>Inputs</h2>
          {contract.dataset_inputs.map((spec: any) => (
            <div key={spec.name}>
              <label>
                {spec.label} (columns: {spec.required_columns.map((c: any) => c.name).join(", ")})
              </label>
              <select
                value={bindings[spec.name] ?? ""}
                onChange={(e) => setBindings({ ...bindings, [spec.name]: e.target.value })}
              >
                <option value="">— select dataset —</option>
                {datasets.map((d) => (
                  <option key={d.artifact_id} value={d.artifact_id}>
                    {d.name} ({d.provenance_label})
                  </option>
                ))}
              </select>
            </div>
          ))}
          {contract.inputs.map((input: any) => (
            <div key={input.name}>
              <label>
                {input.label} ({input.quantity}){input.required ? "" : " — optional"}
              </label>
              <div className="field-unit">
                <input
                  inputMode="decimal"
                  value={values[input.name] ?? ""}
                  onChange={(e) => setValues({ ...values, [input.name]: e.target.value })}
                />
                <select
                  value={units[input.name]}
                  onChange={(e) => setUnits({ ...units, [input.name]: e.target.value })}
                >
                  {(UNIT_CHOICES[input.canonical_unit] ?? [input.canonical_unit]).map((u) => (
                    <option key={u}>{u || "dimensionless"}</option>
                  ))}
                </select>
              </div>
            </div>
          ))}
          {contract.outputs.map((output: any) => (
            <div key={output.name} className="muted">{output.label} · {output.unit || "dimensionless"}</div>
          ))}
          {error && <p className="error-text">{error}</p>}
          <div style={{ marginTop: 14 }}>
            <button onClick={execute} disabled={busy}>
              {busy ? "Running…" : "Run"}
            </button>
          </div>
          <h3>Assumptions</h3>
          <ul className="plain muted">
            {contract.model.assumptions.map((a: string, i: number) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
          <h3>Validity</h3>
          <ul className="plain muted">
            {contract.model.validity.map((v: string, i: number) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h2>Result</h2>
          {!run && <div className="empty">Run the tool to see results. Nothing is computed in the browser.</div>}
          {run && (
            <>
              <span className={`chip ${run.status === "completed" ? "ok" : "error"}`}>
                {run.status}
              </span>
              <span className="chip">{run.provenance_label}</span>
              <a className="mono" href={`#/run/${run.artifact_id}`} style={{ fontSize: 12 }}>
                run {run.artifact_id.slice(0, 10)}
              </a>
              <table style={{ marginTop: 10 }}>
                <tbody>
                  {Object.entries(run.outputs).map(([name, out]: [string, any]) => (
                    <tr key={name}>
                      <th>{name}</th>
                      <td className="num">
                        {Number(out.value).toPrecision(6)}
                        {out.sigma != null && ` ± ${Number(out.sigma).toPrecision(3)}`}
                      </td>
                      <td>{out.unit || "dimensionless"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {run.guards.map((g: string, i: number) => (
                <div className="guard" key={i}>
                  {g}
                </div>
              ))}
              {run.warnings.map((w: string, i: number) => (
                <p className="muted" key={i}>
                  ⚠ {w}
                </p>
              ))}
              <p className="muted" style={{ fontSize: 12.5 }}>
                Checks:{" "}
                {run.checks.map((c: any) => `${c.name}: ${c.passed ? "pass" : "FAIL"}`).join(" · ")}
              </p>
              {fitArray && (
                <Plot
                  series={[
                    {
                      x: fitArray.columns.wavelength.map((w: number) => w * 1e9),
                      y: fitArray.columns.flux,
                      name: "data",
                    },
                    {
                      x: fitArray.columns.wavelength.map((w: number) => w * 1e9),
                      y: fitArray.columns.fitted,
                      name: "fitted",
                      mode: "lines",
                    },
                  ]}
                  xLabel="wavelength [nm]"
                  yLabel="flux [arb]"
                />
              )}
              {geometryArray && (
                <Plot
                  series={[{
                    x: geometryArray.columns.angle.map((angle: number) => angle * 180 / Math.PI),
                    y: geometryArray.columns.differential_cross_section,
                    name: "Klein–Nishina",
                    mode: "lines",
                  }]}
                  xLabel="scattering angle [deg]"
                  yLabel="dσ/dΩ [m²/sr]"
                />
              )}
              {tunnelingArrays.barrier_profile && (
                <Plot series={[{ x: tunnelingArrays.barrier_profile.columns.position.map((x: number) => x * 1e9), y: tunnelingArrays.barrier_profile.columns.potential.map((v: number) => v / 1.602176634e-19), name: "potential", mode: "lines" }]} xLabel="position [nm]" yLabel="potential [eV]" />
              )}
              {tunnelingArrays.wavefunction && (
                <Plot series={[{ x: tunnelingArrays.wavefunction.columns.position.map((x: number) => x * 1e9), y: tunnelingArrays.wavefunction.columns.probability_density, name: "relative probability density", mode: "lines" }]} xLabel="position [nm]" yLabel="relative probability density" />
              )}
              {tunnelingArrays.residuals && (
                <Plot series={[{ x: tunnelingArrays.residuals.columns.x, y: tunnelingArrays.residuals.columns.observed, name: "observed" }, { x: tunnelingArrays.residuals.columns.x, y: tunnelingArrays.residuals.columns.fitted, name: "linear fit", mode: "lines" }, { x: tunnelingArrays.residuals.columns.x, y: tunnelingArrays.residuals.columns.residual, name: "residual" }]} xLabel="x [input units]" yLabel="y [input units]" />
              )}
              {tunnelingArrays.energy_sweep && (
                <Plot series={[{
                  x: tunnelingArrays.energy_sweep.columns.energy,
                  y: tunnelingArrays.energy_sweep.columns.transmission,
                  name: "transmission",
                  mode: "lines",
                }, {
                  x: tunnelingArrays.energy_sweep.columns.energy,
                  y: tunnelingArrays.energy_sweep.columns.reflection,
                  name: "reflection",
                  mode: "lines",
                }]} xLabel="particle energy [J]" yLabel="probability" />
              )}
              {notebooks.length > 0 && (
                <div style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center" }}>
                  <span className="muted">Insert into notebook:</span>
                  {notebooks.map((n) => (
                    <button className="secondary" key={n.artifact_id} onClick={() => addToNotebook(n.artifact_id)}>
                      {n.title}
                      {addedTo === n.artifact_id ? " ✓" : ""}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}
