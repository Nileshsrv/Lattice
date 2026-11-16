import { useEffect, useState } from "react";
import { api } from "./api";
import { DatasetPage } from "./pages/DatasetPage";
import { ComparisonPage } from "./pages/ComparisonPage";
import { LoginPage } from "./pages/LoginPage";
import { NotebookPage } from "./pages/NotebookPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ReportPage } from "./pages/ReportPage";
import { RunPage } from "./pages/RunPage";
import { ToolPage } from "./pages/ToolPage";

function useHashRoute(): string[] {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash.replace(/^#\/?/, "").split("/").filter(Boolean);
}

export function navigate(path: string) {
  window.location.hash = path;
}

export function App() {
  const route = useHashRoute();
  const [user, setUser] = useState<{ id: string; username: string } | null | undefined>(
    undefined
  );

  useEffect(() => {
    api
      .get("/api/auth/me")
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  if (user === undefined) return null;
  if (user === null) return <LoginPage onAuth={setUser} />;

  let page = <ProjectsPage />;
  if (route[0] === "p" && route[1]) {
    if (route[2] === "tool" && route[3]) {
      page = <ToolPage projectId={route[1]} toolId={route[3]} />;
    } else {
      page = <ProjectPage id={route[1]} />;
    }
  } else if (route[0] === "run" && route[1]) {
    page = <RunPage id={route[1]} />;
  } else if (route[0] === "nb" && route[1]) {
    page = <NotebookPage id={route[1]} />;
  } else if (route[0] === "ds" && route[1]) {
    page = <DatasetPage id={route[1]} />;
  } else if (route[0] === "report" && route[1]) {
    page = <ReportPage id={route[1]} />;
  } else if (route[0] === "compare" && route[1]) {
    page = <ComparisonPage id={route[1]} />;
  }

  return (
    <>
      <header className="topbar">
        <span className="brand">
          <a href="#/">Lattice</a>
        </span>
        <span className="muted">research workspace · vertical slice</span>
        <span className="spacer" />
        <span className="muted">{user.username}</span>
        <button
          className="secondary"
          onClick={async () => {
            await api.post("/api/auth/logout");
            setUser(null);
          }}
        >
          Sign out
        </button>
      </header>
      <main className="layout">{page}</main>
    </>
  );
}
