import { useEffect, useState } from "react";
import { api } from "../api";
import { Plot } from "../Plot";

export function ComparisonPage(props: { id: string }) {
  const [comparison, setComparison] = useState<any>(null);
  const [overlay, setOverlay] = useState<any>(null);
  useEffect(() => {
    api.get(`/api/comparisons/${props.id}`).then(async (value) => {
      setComparison(value);
      const [first, second] = value.runs;
      const commonArray = Object.keys(first.arrays ?? {}).find((name) => Boolean(second.arrays?.[name]));
      if (commonArray) {
        const [arrayA, arrayB] = await Promise.all([
          api.get(`/api/runs/${first.artifact_id}/arrays/${commonArray}`),
          api.get(`/api/runs/${second.artifact_id}/arrays/${commonArray}`),
        ]);
        setOverlay({ name: commonArray, a: arrayA, b: arrayB });
      }
    });
  }, [props.id]);
  if (!comparison) return null;
  const [first, second] = comparison.runs;
  return (
    <div className="card">
      <h2>{comparison.name} <span className="chip">saved comparison v{comparison.version}</span></h2>
      <p className="muted">Run values remain linked to their source artifacts and versions.</p>
      <a href={`#/p/${comparison.project_id}`}>← back to project</a>
      <table>
        <thead><tr><th>Parameter</th><th>{first.name}</th><th>{second.name}</th><th>Changed</th></tr></thead>
        <tbody>
          {Object.entries(comparison.parameter_diff).map(([key, diff]: [string, any]) => (
            <tr key={key}><th>{key}</th><td>{diff.a ? `${diff.a.value} ${diff.a.unit}` : "—"}</td><td>{diff.b ? `${diff.b.value} ${diff.b.unit}` : "—"}</td><td>{diff.different ? "yes" : "no"}</td></tr>
          ))}
        </tbody>
      </table>
      {overlay && <>
        <h3>Shared output overlay: {overlay.name}</h3>
        <Plot series={[
          { ...arraySeries(overlay.a), name: first.name },
          { ...arraySeries(overlay.b), name: second.name },
        ]} xLabel="shared array x" yLabel="shared array y" />
      </>}
      <h3>Outputs</h3>
      <table>
        <thead><tr><th>Quantity</th><th>{first.name}</th><th>{second.name}</th></tr></thead>
        <tbody>
          {Object.entries(comparison.output_diff).map(([key, diff]: [string, any]) => (
            <tr key={key}><th>{key}</th><td>{diff.a ? `${Number(diff.a.value).toPrecision(8)} ${diff.a.unit}` : "—"}</td><td>{diff.b ? `${Number(diff.b.value).toPrecision(8)} ${diff.b.unit}` : "—"}</td></tr>
          ))}
        </tbody>
      </table>
      <p><a href={`#/run/${first.artifact_id}`}>Open first run</a> · <a href={`#/run/${second.artifact_id}`}>Open second run</a></p>
    </div>
  );
}

function arraySeries(array: any) {
  const keys = Object.keys(array.columns);
  const xKey = keys[0];
  const yKey = keys.find((key) => key !== xKey) ?? xKey;
  return { x: array.columns[xKey], y: array.columns[yKey], mode: "lines" };
}
