import { useEffect, useState } from "react";
import { api } from "../api";

export function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [name, setName] = useState("");
  const [question, setQuestion] = useState("");

  const load = () => api.get("/api/projects").then(setProjects);
  useEffect(() => {
    load();
  }, []);

  return (
    <>
      <div className="card">
        <h2>New project</h2>
        <label>Name</label>
        <input value={name} onChange={(e) => setName(e.target.value)} />
        <label>Research question</label>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} />
        <div style={{ marginTop: 12 }}>
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
      <div className="card">
        <h2>Projects</h2>
        {projects.length === 0 ? (
          <div className="empty">No projects yet — create one above to begin.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Research question</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td>
                    <a href={`#/p/${p.id}`}>{p.name}</a>
                  </td>
                  <td>{p.research_question}</td>
                  <td>
                    <span className="chip">{p.role}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
