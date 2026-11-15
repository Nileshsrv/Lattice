import { useState } from "react";
import { api, ApiError } from "../api";

export function LoginPage(props: { onAuth: (u: any) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");

  const submit = async () => {
    setError("");
    try {
      const user = await api.post(`/api/auth/${mode}`, { username, password });
      props.onAuth(user);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "request failed");
    }
  };

  return (
    <main className="layout" style={{ maxWidth: 420, paddingTop: 80 }}>
      <div className="card">
        <h2>Lattice — sign {mode === "login" ? "in" : "up"}</h2>
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} />
        <label>Password (min 8 characters)</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        {error && <p className="error-text">{error}</p>}
        <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
          <button onClick={submit}>{mode === "login" ? "Sign in" : "Create account"}</button>
          <button
            className="secondary"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Need an account?" : "Have an account?"}
          </button>
        </div>
      </div>
    </main>
  );
}
