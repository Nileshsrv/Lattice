import { useEffect, useState } from "react";
import { api } from "../api";

export function ProjectsPage() {
  const [projects, setProjects] = useState<any[] | null>(null);
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("");

  const load = () => api.get("/api/projects").then(setProjects);
  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <div className="page-head">
        <h1>Projects</h1>
        <p>Each project keeps its data, runs, notebooks, discussion and reports in one context.</p>
      </div>

      {projects !== null && projects.length === 0 && (
        <div className="empty" style={{ marginBottom: 18 }}>
          No projects yet — name one below and state its research question to begin.
        </div>
      )}

      {projects !== null && projects.length > 0 && (
        <div className="project-grid" style={{ marginBottom: 22 }}>
          {projects.map((p) => (
            <a className="project-card" key={p.id} href={`#/p/${p.id}`}>
              <span className="title">{p.name}</span>
              <span className="question">
                {p.research_question || "No research question recorded yet."}
              </span>
              <span className="foot">
                <span className="chip accent">{p.role}</span>
                <span className="mono">{p.created_at.slice(0, 10)}</span>
              </span>
            </a>
          ))}
        </div>
      )}

      <div className="card" style={{ maxWidth: 640 }}>
        <h2>New project</h2>
        <label htmlFor="project-name">Name</label>
        <input
          id="project-name"
          value={name}
          placeholder="e.g. Stellar spectrum analysis"
          onChange={(e) => setName(e.target.value)}
        />
        <label htmlFor="project-question">Research question</label>
        <input
          id="project-question"
          value={question}
          placeholder="What are you trying to find out?"
          onChange={(e) => setQuestion(e.target.value)}
        />
        <div style={{ marginTop: 16 }}>
          <button
            disabled={!name.trim()}
            onClick={async () => {
              await api.post("/api/projects", { name, research_question: question });
              setName("");
              setQuestion("");
              load();
            }}
          >
            Create project
          </button>
        </div>
      </div>
    </>
  );
}
