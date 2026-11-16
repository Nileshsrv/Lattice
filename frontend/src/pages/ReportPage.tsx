import { useEffect, useState } from "react";
import { api } from "../api";

export function ReportPage(props: { id: string }) {
  const [report, setReport] = useState<any>(null);
  const [staleness, setStaleness] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = () => {
    api.get(`/api/reports/${props.id}`).then(setReport);
    api.get(`/api/reports/${props.id}/staleness`).then(setStaleness).catch(() => {});
  };
  useEffect(() => {
    load();
  }, [props.id]);

  if (!report) return null;

  const printVersion = (version: number) => {
    const printWindow = window.open(`/api/reports/${props.id}/versions/${version}/html`, "_blank");
    if (!printWindow) return;
    printWindow.addEventListener("load", () => {
      printWindow.setTimeout(() => printWindow.print(), 500);
    }, { once: true });
  };

  return (
    <div className="card">
      <h2>
        {report.title}{" "}
        <span className="chip">{report.report_type || "lab-report"}</span>
        {staleness?.stale && (
          <span className="chip warn">Sources changed since last export</span>
        )}
      </h2>
      <p className="muted">
        Assembled from saved artifacts in notebook{" "}
        <a href={`#/nb/${report.notebook_id}`} className="mono">
          {report.notebook_id.slice(0, 10)}
        </a>
        . Each export freezes the artifact versions it used.
      </p>
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await api.post(`/api/reports/${props.id}/export`);
            await load();
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Exporting…" : "Export new version (HTML)"}
      </button>

      <h3>Versions</h3>
      {report.versions.length === 0 ? (
        <div className="empty">No exports yet.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Version</th>
              <th>Exported</th>
              <th>Frozen artifacts</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {report.versions.map((v: any) => (
              <tr key={v.number}>
                <td>v{v.number}</td>
                <td>{v.created_at.slice(0, 19)}</td>
                <td className="num">{v.n_artifacts}</td>
                <td>
                  <a href={`/api/reports/${props.id}/versions/${v.number}/html`} target="_blank" rel="noreferrer">
                    HTML
                  </a>{" "}
                  ·{" "}
                  <button className="secondary" onClick={() => printVersion(v.number)}>
                    Print / Save as PDF
                  </button>{" "}
                  ·{" "}
                  <a href={`/api/reports/${props.id}/versions/${v.number}/manifest`} target="_blank" rel="noreferrer">
                    manifest
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
