import { useState } from "react";
import { api, ApiError } from "../api";
import { IconLink, IconShield, IconUsers, LogoMark } from "../icons";

export function LoginPage(props: { onAuth: (u: any) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      const user = await api.post(`/api/auth/${mode}`, { username, password });
      props.onAuth(user);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "request failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth">
      <section className="auth-pitch">
        <span className="brand" style={{ fontSize: 19 }}>
          <LogoMark size={32} /> Lattice
        </span>
        <h1>
          Research that stays <em>connected</em>, from data to report.
        </h1>
        <p>
          Simulate, analyse, discuss and document in one workspace — where every figure
          and value is traceable to the computation and data that produced it.
        </p>
        <ul className="pitch-list">
          <li>
            <span className="ico"><IconLink /></span>
            <div>
              <b>Connected workflows</b>
              <span>Tool outputs flow into the next analysis by reference, never by re-upload.</span>
            </div>
          </li>
          <li>
            <span className="ico"><IconShield /></span>
            <div>
              <b>Reproducible by construction</b>
              <span>Inputs, units, data hashes, methods and versions are saved with every run.</span>
            </div>
          </li>
          <li>
            <span className="ico"><IconUsers /></span>
            <div>
              <b>Collaboration on the science</b>
              <span>Comment on results, compare variants, and review before a report is final.</span>
            </div>
          </li>
        </ul>
      </section>

      <section className="auth-card" aria-label={mode === "login" ? "Sign in" : "Create account"}>
        <h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2>
        <p className="sub">
          {mode === "login"
            ? "Sign in to continue to your projects."
            : "Accounts are local to this workspace."}
        </p>
        <label htmlFor="auth-username">Username</label>
        <input
          id="auth-username"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <label htmlFor="auth-password">Password (min 8 characters)</label>
        <input
          id="auth-password"
          type="password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        {error && <p className="error-text">{error}</p>}
        <button className="primary" onClick={submit} disabled={busy}>
          {busy ? "One moment…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
        <p className="switch">
          {mode === "login" ? "New here? " : "Already registered? "}
          <button
            className="link-btn"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Create an account" : "Sign in instead"}
          </button>
        </p>
      </section>
    </main>
  );
}
