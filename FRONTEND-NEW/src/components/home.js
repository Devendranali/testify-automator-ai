import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Dashboard from "./dashboard";
import { toast, ToastContainer } from "react-toastify";
import styles from "./Home.module.css"; // Import the CSS module

const Home = () => {
  const navigate = useNavigate();

  const [showDialog, setShowDialog] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [framework, setFramework] = useState("Playwright");
  const [language, setLanguage] = useState("Python");
  const [userEmail, setUserEmail] = useState("");
  const [projects, setProjects] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      try {
        // This is a simple way to decode the JWT payload.
        // In a real-world application, you should use a library like 'jwt-decode'
        // and also verify the token's signature on the server-side.
        const payload = JSON.parse(atob(token.split(".")[1]));
        setUserEmail(payload.sub);
      } catch (e) {
        console.error("Invalid token:", e);
        handleLogout();
      }
    }

    // Load projects from backend
    const apiBase = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8001';
    fetch(`${apiBase}/projects`)
      .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`)))
      .then(data => Array.isArray(data?.projects) ? setProjects(data.projects) : setProjects([]))
      .catch(() => setProjects([]));
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login");
  };

  const handleStartProject = async () => {
    if (!projectName.trim()) {
      toast.error("Please enter a project name."); // Using toast for better UX
      return;
    }

    // Prevent duplicate project names (client-side)
    const exists = projects.some(
      (p) => (p?.project_name || "").trim().toLowerCase() === projectName.trim().toLowerCase()
    );
    if (exists) {
      toast.error(`Project '${projectName.trim()}' already exists.`);
      return;
    }

    console.log("Project Name:", projectName);
    console.log("Test Framework:", framework);
    console.log("Programming Language:", language);

    // Send details to backend
    try {
      const apiBase = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8001';
      const res = await fetch(`${apiBase}/projects/save-details`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_name: projectName.trim(), framework, language }),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      await res.json();
      toast.success('Project saved');
      // Optimistically add to local list
      setProjects([{ project_name: projectName.trim(), framework, language, created_at: new Date().toISOString() }, ...projects]);
    } catch (e) {
      console.error('Failed to save project:', e);
      toast.error(`Failed to save: ${e.message || e}`);
      return;
    }

    setShowDialog(false);
    navigate("/input", { state: { projectName: projectName } });
  };


  return (
    <div className={styles.homeContainer}>
      <ToastContainer/>
      <nav className={styles.navbar}>
        <div className={styles.navbarBrand}>
          <i
            className={`fa fa-code ${styles.navbarIcon}`}
          ></i>
          <div>
            <h4 className={styles.navbarTitle}>
              AutoTest Studio
            </h4>
            <p className={styles.navbarSubtitle}>
              Automation Development Platform
            </p>
          </div>
        </div>

        <div className={styles.navbarUser}>
          <span>{userEmail}</span>
          <button
            onClick={handleLogout}
            className={styles.logoutButton}
          >
            Logout
          </button>
        </div>

        <button
          onClick={() => setShowDialog(true)}
          className={styles.newProjectButton}
        >
          <i className="fa-solid fa-plus" style={{ fontSize: "18px" }}></i>
          New Project
        </button>
      </nav>

      <Dashboard
        projects={projects}
        onOpen={async (p) => {
          try {
            const apiBase = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8001';
            const res = await fetch(`${apiBase}/projects/activate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ project_name: p.project_name })
            });
            if (!res.ok) {
              const txt = await res.text().catch(() => null);
              throw new Error(txt || `Server returned ${res.status}`);
            }
            toast.success(`Activated project: ${p.project_name}`);
            navigate('/input', { state: { projectName: p.project_name } });
          } catch (e) {
            console.error('Failed to activate project:', e);
            toast.error(`Failed to open project: ${e.message || e}`);
          }
        }}
      />

      {/* Projects are now displayed inside Dashboard's Recent Projects */}

      {/* Project Setup Dialog */}
      {showDialog && (
        <div className={styles.dialogOverlay}>
          <div className={styles.dialogContent}>
            <h2 className={styles.dialogContentH2}>Create New Project</h2>

            <label className={styles.formLabel}>
              Project Name:
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Enter project name"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Select Framework:
              <select
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                className={styles.formSelect}
              >
                <option>Selenium </option>
                <option>Playwright</option>
                <option>Cypress </option>
                <option>Appium </option>
              </select>
            </label>

            <label className={styles.formLabel}>
              Programming Language:
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className={styles.formSelect}
              >
                <option>Python</option>
                <option>Java</option>
                <option>JavaScript</option>
                <option>C#</option>
              </select>
            </label>

            <div className={styles.dialogActions}>
              <button
                onClick={() => setShowDialog(false)}
                className={styles.cancelButton}
              >
                Cancel
              </button>
              <button
                onClick={handleStartProject}
                className={styles.startButton}
              >
                Start Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
