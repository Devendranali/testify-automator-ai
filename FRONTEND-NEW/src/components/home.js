import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dashboard from "./dashboard";
import { toast, ToastContainer } from "react-toastify";
import styles from "./Home.module.css"; // Import the CSS module

const Home = () => {
  const navigate = useNavigate();

  const [showDialog, setShowDialog] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [framework, setFramework] = useState("Playwright");
  const [language, setLanguage] = useState("python");

  const handleStartProject = () => {
    if (!projectName.trim()) {
      toast.error("Please enter a project name."); // Using toast for better UX
      return;
    }

    console.log("Project Name:", projectName);
    console.log("Test Framework:", framework);
    console.log("Programming Language:", language);

    setShowDialog(false);
    navigate("/input");
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

        <button
          onClick={() => setShowDialog(true)}
          className={styles.newProjectButton}
        >
          <i className="fa-solid fa-plus" style={{ fontSize: "18px" }}></i>
          New Project
        </button>
      </nav>

      <Dashboard />

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
                <option>Java</option>
                <option>Python</option>
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

