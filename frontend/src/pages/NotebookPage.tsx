import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { Plot } from "../Plot";

export function NotebookPage(props: { id: string }) {
  const [notebook, setNotebook] = useState<any>(null);
  const [newText, setNewText] = useState("");
  const [newType, setNewType] = useState<"text" | "heading">("text");

  const load = () => api.get(`/api/notebooks/${props.id}`).then(setNotebook);
  useEffect(() => {
    load();
  }, [props.id]);

  if (!notebook) return null;

  return (
    <>
      <div className="card">
        <h2>
          {notebook.title} <span className="chip">v{notebook.version}</span>
        </h2>
        <a href={`#/p/${notebook.project_id}`}>← back to project</a>
      </div>

      {notebook.blocks.length === 0 && (
        <div className="empty">
          Empty notebook. Add prose below, or insert a figure from a tool's result panel.
        </div>
      )}
      {notebook.blocks.map((block: any) => (
        <BlockView key={block.id} block={block} onChange={load} />
      ))}

      <div className="card">
        <h2>Add block</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <select value={newType} onChange={(e) => setNewType(e.target.value as any)}>
            <option value="text">text</option>
            <option value="heading">heading</option>
          </select>
          <input
            value={newText}
            placeholder={newType === "heading" ? "Heading text" : "Paragraph text"}
            onChange={(e) => setNewText(e.target.value)}
          />
          <button
            disabled={!newText.trim()}
            onClick={async () => {
              await api.post(`/api/notebooks/${props.id}/blocks`, {
                type: newType,
                content: { text: newText },
              });
              setNewText("");
              load();
            }}
          >
            Add
          </button>
        </div>
      </div>
    </>
  );
}

function BlockView(props: { block: any; onChange: () => void }) {
  const { block } = props;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [conflict, setConflict] = useState<any>(null);

  if (block.type === "figure") return <FigureBlock block={block} />;

  const save = async (revision: number) => {
    try {
      await api.patch(`/api/blocks/${block.id}`, {
        content: { text: draft },
        revision,
      });
      setEditing(false);
      setConflict(null);
      props.onChange();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(e.detail);
      }
    }
  };

  return (
    <div className="card">
      {editing ? (
        <>
          <textarea rows={3} value={draft} onChange={(e) => setDraft(e.target.value)} />
          {conflict && (
            <div className="guard">
              Someone else edited this block (now revision {conflict.server_revision}):
              <p className="muted">"{conflict.server_content.text}"</p>
              Your edit was NOT applied. Keep yours (overwrites theirs) or take theirs.
              <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                <button onClick={() => save(conflict.server_revision)}>Keep mine</button>
                <button
                  className="secondary"
                  onClick={() => {
                    setEditing(false);
                    setConflict(null);
                    props.onChange();
                  }}
                >
                  Take theirs
                </button>
              </div>
            </div>
          )}
          {!conflict && (
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button onClick={() => save(block.revision)}>Save</button>
              <button className="secondary" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          )}
        </>
      ) : (
        <div
          onDoubleClick={() => {
            setDraft(block.content.text ?? "");
            setEditing(true);
          }}
          title="Double-click to edit"
        >
          {block.type === "heading" ? <h2>{block.content.text}</h2> : <p>{block.content.text}</p>}
        </div>
      )}
    </div>
  );
}

function FigureBlock(props: { block: any }) {
  const { block } = props;
  const [run, setRun] = useState<any>(null);
  const [fit, setFit] = useState<any>(null);

  useEffect(() => {
    api.get(`/api/runs/${block.content.run_artifact_id}`).then(async (r) => {
      setRun(r);
      if (block.content.array && r.arrays?.[block.content.array]) {
        setFit(await api.get(`/api/runs/${r.artifact_id}/arrays/${block.content.array}`));
      }
    });
  }, [block.id]);

  return (
    <div className="card">
      {fit && (
        <Plot
          series={[
            { x: fit.columns.wavelength.map((w: number) => w * 1e9), y: fit.columns.flux, name: "data" },
            { x: fit.columns.wavelength.map((w: number) => w * 1e9), y: fit.columns.fitted, name: "fitted", mode: "lines" },
          ]}
          xLabel="wavelength [nm]"
          yLabel="flux [arb]"
        />
      )}
      <p className="muted">
        {block.content.caption}
        {run && (
          <>
            {" — "}
            <a href={`#/run/${run.artifact_id}`} className="mono" style={{ fontSize: 12 }}>
              run {run.artifact_id.slice(0, 10)}@v{block.content.run_version}
            </a>{" "}
            {run.outputs?.T_eff && (
              <span className="num">
                (T_eff = {Number(run.outputs.T_eff.value).toFixed(1)}
                {run.outputs.T_eff.sigma != null &&
                  ` ± ${Number(run.outputs.T_eff.sigma).toFixed(1)}`}{" "}
                K)
              </span>
            )}
          </>
        )}
      </p>
    </div>
  );
}
