import { useEffect, useState } from "react";
import { api } from "./api";
import {
  IconActivity,
  IconBack,
  IconData,
  IconLibrary,
  IconMoon,
  IconNotebook,
  IconOverview,
  IconProjects,
  IconRuns,
  IconSun,
  IconTools,
  LogoMark,
  initials,
} from "./icons";
import { ComparisonPage } from "./pages/ComparisonPage";
import { DatasetPage } from "./pages/DatasetPage";
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
  return hash.replace(/^#\/?/, "").split("?")[0].split("/").filter(Boolean);
}

export function navigate(path: string) {
  window.location.hash = path;
}

function useTheme(): [string, () => void] {
  const [theme, setTheme] = useState(
    document.documentElement.getAttribute("data-theme") ?? "dark"
  );
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("lattice-theme", next);
    } catch {
      // storage unavailable: the choice simply lasts for this page view
    }
    setTheme(next);
  };
  return [theme, toggle];
}

const PROJECT_SECTIONS = [
  { id: "sec-overview", label: "Overview", icon: <IconOverview /> },
  { id: "sec-datasets", label: "Datasets", icon: <IconData /> },
  { id: "sec-workbench", label: "Workbench", icon: <IconTools /> },
  { id: "sec-runs", label: "Runs", icon: <IconRuns /> },
  { id: "sec-notebooks", label: "Notebooks & reports", icon: <IconNotebook /> },
  { id: "sec-activity", label: "Activity", icon: <IconActivity /> },
];

let lastProjectId: string | null = null;

function Sidebar(props: { route: string[] }) {
  const { route } = props;
  const onProjectHome = route[0] === "p" && route[1] && !route[2];
  if (route[0] === "p" && route[1]) lastProjectId = route[1];

  return (
    <nav className="sidebar" aria-label="Primary">
      <div className="nav-label">Workspace</div>
      <a className={`nav-item ${route.length === 0 ? "active" : ""}`} href="#/">
        <IconProjects /> Projects
      </a>
      <button className="nav-item" disabled title="Planned for a later phase">
        <IconLibrary /> Research library <span className="soon">later</span>
      </button>

      {onProjectHome && (
        <>
          <div className="nav-label">This project</div>
          {PROJECT_SECTIONS.map((section) => (
            <button
              key={section.id}
              className="nav-item"
              onClick={() =>
                document.getElementById(section.id)?.scrollIntoView({ block: "start" })
              }
            >
              {section.icon} {section.label}
            </button>
          ))}
        </>
      )}

      {!onProjectHome && lastProjectId && route.length > 0 && (
        <>
          <div className="nav-label">Navigation</div>
          <a className="nav-item" href={`#/p/${lastProjectId}`}>
            <IconBack /> Back to project
          </a>
        </>
      )}

      <div className="sidebar-foot">
        Numbers come from tool runs and data — never from generated text.
      </div>
    </nav>
  );
}

export function App() {
  const route = useHashRoute();
  const [theme, toggleTheme] = useTheme();
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
  } else if ((route[0] === "run" || route[0] === "runs") && route[1]) {
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
        <a className="brand" href="#/">
          <LogoMark /> Lattice
        </a>
        <span className="brand-tag">Research workspace</span>
        <span className="spacer" />
        <button
          className="icon-btn"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? <IconSun /> : <IconMoon />}
        </button>
        <span className="user-pill">
          <span className="avatar">{initials(user.username)}</span>
          {user.username}
        </span>
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
      <Sidebar route={route} />
      <div className="app-main">
        <main className="layout">{page}</main>
      </div>
    </>
  );
}
