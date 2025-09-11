import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dashboard from "./dashboard";
import { toast, ToastContainer } from "react-toastify";
import styles from "../css/Home.module.css";

const Home = () => {
  const navigate = useNavigate();

  const [showDialog, setShowDialog] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [framework, setFramework] = useState("Playwright");
  const [language, setLanguage] = useState("python");

  const handleStartProject = () => {
    if (!projectName.trim()) {
      toast.error("Please enter a project name.");
      return;
    }
    setShowDialog(false);
    navigate("/input");
  };

  // Define styles directly in the component
  const formLabelStyle = {
    display: 'block',
    marginBottom: '1.5rem',
    color: '#6c757d',
    fontWeight: '500',
    fontSize: '0.8rem'
  };

  const formInputStyle = {
    width: '100%',
    padding: '0.75rem 0.25rem',
    fontSize: '0.95rem',
    marginTop: '0.5rem',
    border: 'none',
    borderBottom: '2px solid #dee2e6',
    backgroundColor: 'transparent',
    borderRadius: '0',
  };

  const dialogActionsStyle = {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '1rem',
    marginTop: '2.5rem'
  };

  const cancelButtonStyle = {
    padding: '0.63rem 1.26rem',
    backgroundColor: 'transparent',
    color: '#6c757d',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.95rem',
    cursor: 'pointer',
    fontWeight: '600'
  };

  const startButtonStyle = {
    padding: '0.63rem 1.26rem',
    background: 'linear-gradient(90deg, rgb(76, 62, 203), rgb(87, 72, 222), rgb(227, 83, 237))',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '0.95rem',
    cursor: 'pointer',
    fontWeight: '600',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
  };

  return (
    <div className={styles.homeContainer}>
      <ToastContainer/>
      <nav className={styles.navbar}>
        <div className={styles.navbarBrand}>
          <i className={`fa fa-code ${styles.navbarIcon}`}></i>
          <div>
            <h4 className={styles.navbarTitle}>AutoTest Studio</h4>
            <p className={styles.navbarSubtitle}>Automation Development Platform</p>
          </div>
        </div>
        <button onClick={() => setShowDialog(true)} className={styles.newProjectButton}>
          <i className="fa-solid fa-plus" style={{ fontSize: "18px" }}></i>
          New Project
        </button>
      </nav>

      <Dashboard />

      {showDialog && (
        <div className={styles.dialogOverlay}>
          <div className={styles.dialogContent}>
            <h2>Create New Project</h2>
            <button onClick={() => setShowDialog(false)} className={styles.closeDialogButton}>
              <i className="fa-solid fa-xmark"></i>
            </button>

            <label style={formLabelStyle}>
              Project Name:
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Enter project name"
                style={formInputStyle}
              />
            </label>

            <label style={formLabelStyle}>
              Select Framework:
              <select
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                style={formInputStyle}
              >
                <option>Selenium</option>
                <option>Playwright</option>
                <option>Cypress</option>
                <option>Appium</option>
              </select>
            </label>

            <label style={formLabelStyle}>
              Programming Language:
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                style={formInputStyle}
              >
                <option>Java</option>
                <option>Python</option>
                <option>JavaScript</option>
                <option>C#</option>
              </select>
            </label>

            <div style={dialogActionsStyle}>
              <button onClick={() => setShowDialog(false)} style={cancelButtonStyle}>
                Cancel
              </button>
              <button onClick={handleStartProject} style={startButtonStyle}>
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