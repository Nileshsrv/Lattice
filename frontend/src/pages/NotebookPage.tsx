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

      <CommentThread
        artifactId={props.id}
        blocks={notebook.blocks}
      />

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
          series={arraySeries(fit)}
          xLabel={arrayAxisLabel(fit, Object.keys(fit.columns)[0])}
          yLabel={arrayAxisLabel(fit, Object.keys(fit.columns).find((key: string) => key !== Object.keys(fit.columns)[0]) ?? "")}
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

function CommentThread(props: { artifactId: string; blocks: any[] }) {
  const [comments, setComments] = useState<any[]>([]);
  const [text, setText] = useState("");
  const [anchorBlock, setAnchorBlock] = useState("");

  const load = () =>
    api
      .get(`/api/artifacts/${props.artifactId}/comments?include_resolved=true`)
      .then(setComments);
  useEffect(() => {
    load();
  }, [props.artifactId]);

  const blockLabel = (blockId: string) => {
    const index = props.blocks.findIndex((b) => b.id === blockId);
    if (index < 0) return "removed block";
    const block = props.blocks[index];
    const snippet =
      block.type === "figure" ? block.content.caption : block.content.text;
    return `block ${index + 1}: ${(snippet ?? "").slice(0, 40)}`;
  };

  return (
    <div className="card">
      <h2>Comments</h2>
      {comments.length === 0 && (
        <div className="empty">No comments on this notebook yet.</div>
      )}
      <ul className="plain">
        {comments.map((c) => (
          <li key={c.id} style={{ opacity: c.resolved ? 0.55 : 1 }}>
            <span className="chip">v{c.artifact_version}</span>
            {c.anchor?.block_id && (
              <span className="chip accent">{blockLabel(c.anchor.block_id)}</span>
            )}
            {c.text}
            <button
              className="secondary"
              style={{ marginLeft: 8, padding: "1px 8px", minHeight: 22 }}
              onClick={async () => {
                await api.patch(`/api/comments/${c.id}`, { resolved: !c.resolved });
                load();
              }}
            >
              {c.resolved ? "Reopen" : "Resolve"}
            </button>
          </li>
        ))}
      </ul>
      <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
        <select value={anchorBlock} onChange={(e) => setAnchorBlock(e.target.value)}>
          <option value="">whole notebook</option>
          {props.blocks.map((b, i) => (
            <option key={b.id} value={b.id}>
              {`block ${i + 1} (${b.type})`}
            </option>
          ))}
        </select>
        <input
          value={text}
          placeholder="Comment, anchored to the selection"
          onChange={(e) => setText(e.target.value)}
        />
        <button
          disabled={!text.trim()}
          onClick={async () => {
            await api.post(`/api/artifacts/${props.artifactId}/comments`, {
              text,
              anchor: anchorBlock ? { block_id: anchorBlock } : null,
            });
            setText("");
            load();
          }}
        >
          Comment
        </button>
      </div>
    </div>
  );
}

function arrayAxisLabel(array: any, key: string) {
  const unit = array.units?.[key];
  return unit ? `${key} [${unit}]` : key;
}

function arraySeries(array: any) {
  const columns = array.columns ?? {};
  const xKey = "wavelength" in columns ? "wavelength" : "position" in columns ? "position" : "angle" in columns ? "angle" : "x" in columns ? "x" : Object.keys(columns)[0];
  return Object.keys(columns)
    .filter((key) => key !== xKey && key !== "residual")
    .map((key) => ({
      x: columns[xKey].map((value: number) => xKey === "wavelength" ? value * 1e9 : xKey === "angle" ? value * 180 / Math.PI : value),
      y: columns[key],
      name: key,
      mode: ["fitted", "potential", "probability_density", "differential_cross_section"].includes(key) ? "lines" : "markers",
    }));
}
