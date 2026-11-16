import { useEffect, useState } from "react";
import { api } from "../api";
import { Plot } from "../Plot";

export function DatasetPage(props: { id: string }) {
  const [dataset, setDataset] = useState<any>(null);
  const [preview, setPreview] = useState<any>(null);
  const [windowColumn, setWindowColumn] = useState("");
  const [minimum, setMinimum] = useState("");
  const [maximum, setMaximum] = useState("");
  const [windowError, setWindowError] = useState("");
  const [windowBusy, setWindowBusy] = useState(false);

  useEffect(() => {
    api.get(`/api/datasets/${props.id}`).then(setDataset);
    api.get(`/api/datasets/${props.id}/preview`).then(setPreview);
  }, [props.id]);

  if (!dataset) return null;
  const cols = preview ? Object.keys(preview.data) : [];
  const xCol = cols.includes("wavelength") ? "wavelength" : cols[0];

  const createWindow = async () => {
    setWindowBusy(true);
    setWindowError("");
    try {
      const derived = await api.post(`/api/datasets/${props.id}/window`, {
        column: windowColumn,
        minimum: Number(minimum),
        maximum: Number(maximum),
      });
      window.location.hash = `/ds/${derived.artifact_id}`;
    } catch (error) {
      setWindowError(error instanceof Error ? error.message : "Could not create derived dataset");
    } finally {
      setWindowBusy(false);
    }
  };

  return (
    <>
      <div className="card">
        <h2>
          {dataset.name} <span className="chip">{dataset.provenance_label}</span>
          <span className="chip">v{dataset.version}</span>
        </h2>
        <p className="mono muted" style={{ fontSize: 12 }}>
          sha256 {dataset.sha256} · {dataset.size} bytes · {dataset.source.n_rows} rows
        </p>
        <p className="muted">
          License: {dataset.source.license || "— not provided —"} · file: {dataset.source.filename}
        </p>
        {dataset.unknowns.length > 0 && (
          <div className="guard">
            Unknowns (will appear in report limitations):
            <ul className="plain">
              {dataset.unknowns.map((u: string, i: number) => <li key={i}>{u}</li>)}
            </ul>
          </div>
        )}
        {preview && cols.length >= 2 && (
          <Plot
            series={cols
              .filter((c) => c !== xCol)
              .map((c) => ({ x: preview.data[xCol], y: preview.data[c], name: c }))}
            xLabel={`${xCol} [${dataset.columns.find((c: any) => c.name === xCol)?.unit ?? "?"}]`}
            yLabel="value"
          />
        )}
        <h3>Columns</h3>
        <table>
          <thead>
            <tr><th>Name</th><th>Unit</th><th>Header</th></tr>
          </thead>
          <tbody>
            {dataset.columns.map((c: any) => (
              <tr key={c.name}>
                <td>{c.name}</td>
                <td>{c.unit ?? <span className="chip warn">unknown</span>}</td>
                <td className="mono">{c.header}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Create derived window</h3>
        <p className="muted">Creates a new dataset artifact; the original raw upload remains unchanged. Bounds use the selected column's recorded units.</p>
        <div className="field-unit">
          <select value={windowColumn} onChange={(event) => setWindowColumn(event.target.value)}>
            <option value="">Select column</option>
            {dataset.columns.map((column: any) => (
              <option key={column.name} value={column.name}>{column.name}{column.unit ? ` [${column.unit}]` : " [unit unknown]"}</option>
            ))}
          </select>
          <input inputMode="decimal" value={minimum} placeholder="Inclusive minimum" onChange={(event) => setMinimum(event.target.value)} />
          <input inputMode="decimal" value={maximum} placeholder="Inclusive maximum" onChange={(event) => setMaximum(event.target.value)} />
          <button onClick={createWindow} disabled={windowBusy || !windowColumn || minimum === "" || maximum === ""}>
            {windowBusy ? "Creating…" : "Create derived dataset"}
          </button>
        </div>
        {windowError && <p className="error-text">{windowError}</p>}
      </div>
    </>
  );
}
