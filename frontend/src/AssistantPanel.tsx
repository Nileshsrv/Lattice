import { useState } from "react";
import { api, ApiError } from "./api";
import { IconSpark } from "./icons";

interface Exchange {
  question: string;
  text: string;
  tool_plan: any;
  citations: any[];
}

export function AssistantPanel(props: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [busy, setBusy] = useState(false);

  const ask = async () => {
    if (!message.trim()) return;
    setBusy(true);
    try {
      const reply = await api.post(`/api/projects/${props.projectId}/assistant`, {
        message,
      });
      setExchanges([
        ...exchanges,
        {
          question: message,
          text: reply.text,
          tool_plan: reply.tool_plan,
          citations: reply.citations,
        },
      ]);
      setMessage("");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <div className="card assistant">
        <div className="assistant-bar">
          <span className="spark"><IconSpark /></span>
          <div style={{ flex: 1, minWidth: 220 }}>
            <b>AI research assistant</b>
            <div className="muted" style={{ fontSize: 12.5 }}>
              Suggests tools; every execution needs your approval. It computes nothing itself.
            </div>
          </div>
          <button className="secondary" onClick={() => setOpen(true)}>
            Open AI research assistant
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="card assistant">
      <div className="card-head">
        <h2>
          <span className="spark"><IconSpark /></span>
          AI research assistant <span className="chip">ai-suggested</span>
        </h2>
        <button className="secondary" onClick={() => setOpen(false)}>
          Close
        </button>
      </div>
      <p className="muted" style={{ fontSize: 12.5 }}>
        Rule-based tool dispatcher (no external LLM in this build). It never computes or
        asserts physics values; numbers only come from tool runs you approve.
      </p>
      {exchanges.map((exchange, i) => (
        <div key={i} style={{ marginBottom: 14 }}>
          <div className="bubble you">{exchange.question}</div>
          <div className="bubble">{exchange.text.replace(/\*\*|`/g, "")}</div>
          {exchange.tool_plan && (
            <ToolPlanCard projectId={props.projectId} plan={exchange.tool_plan} />
          )}
        </div>
      ))}
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={message}
          placeholder='e.g. "compute Compton scattering at 90 degrees" or "fit a blackbody"'
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
        />
        <button onClick={ask} disabled={busy}>
          {busy ? "…" : "Ask"}
        </button>
      </div>
    </div>
  );
}

function ToolPlanCard(props: { projectId: string; plan: any }) {
  const { plan } = props;
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const execute = async () => {
    setBusy(true);
    setError("");
    const params: Record<string, any> = {};
    for (const input of plan.inputs) {
      const raw = values[input.name];
      if (raw !== undefined && raw !== "") {
        params[input.name] = { value: Number(raw), unit: input.canonical_unit };
      }
    }
    try {
      const response = await api.post(`/api/projects/${props.projectId}/assistant/execute`, {
        tool_plan: { tool_name: plan.tool_name, params },
        approved: true,
      });
      setResult(response);
    } catch (e) {
      if (e instanceof ApiError && typeof e.detail === "object" && e.detail !== null) {
        const d = e.detail as any;
        setError(d.input_errors ? d.input_errors.join("; ") : JSON.stringify(d));
      } else {
        setError(e instanceof ApiError ? String(e.detail) : "execution failed");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="plan">
      <p>
        Tool plan: <b>{plan.tool_label}</b> <code>{plan.tool_name}</code>{" "}
        <span className="chip accent">{plan.maturity}</span>
      </p>
      {plan.guards?.map((g: string, i: number) => (
        <div className="guard" key={i}>
          {g}
        </div>
      ))}
      {plan.needs_dataset ? (
        <p className="muted">
          This tool takes a dataset, which the assistant cannot bind for you —{" "}
          <a href={`#/p/${props.projectId}/tool/${plan.tool_name}`}>
            open its tool page
          </a>{" "}
          to choose the data and run it.
        </p>
      ) : result ? (
        <p>
          <span className="chip ok">executed</span> Run saved with provenance{" "}
          <span className="chip">ai-suggested</span>:{" "}
          <a href={`#/run/${result.run_id}`}>open run</a>
          {result.result?.outputs &&
            Object.entries(result.result.outputs).map(([name, out]: [string, any]) => (
              <span className="num" key={name} style={{ marginLeft: 10 }}>
                {name} = {Number(out.value).toPrecision(6)} {out.unit}
              </span>
            ))}
        </p>
      ) : (
        <>
          {plan.inputs.map((input: any) => (
            <div key={input.name}>
              <label>
                {input.label} [{input.canonical_unit || "dimensionless"}]
                {input.required ? "" : " — optional"}
              </label>
              <input
                inputMode="decimal"
                value={values[input.name] ?? ""}
                placeholder={input.default != null ? String(input.default) : ""}
                onChange={(e) => setValues({ ...values, [input.name]: e.target.value })}
              />
            </div>
          ))}
          {error && <p className="error-text">{error}</p>}
          <div style={{ marginTop: 10 }}>
            <button onClick={execute} disabled={busy}>
              {busy ? "Running…" : "Approve & execute"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
