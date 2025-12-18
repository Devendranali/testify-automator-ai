import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Dashboard from "./dashboard";
import { toast } from "react-toastify";
import Editor from "@monaco-editor/react";
import styles from "../css/Home.module.css";

const formatLabel = (label = "") =>
  label
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());

const Home = () => {
  const navigate = useNavigate();

  const [showDialog, setShowDialog] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [framework, setFramework] = useState("Playwright");
  const [language, setLanguage] = useState("Python");
  const [userEmail, setUserEmail] = useState("");
  const [userOrganization, setUserOrganization] = useState("");
  const [projects, setProjects] = useState([]);
  const [expandedProjectKey, setExpandedProjectKey] = useState(null);
  const [projectDetails, setProjectDetails] = useState({});
  const [loadingProjectKey, setLoadingProjectKey] = useState(null);
  const [projectFiles, setProjectFiles] = useState({});
  const [openDirectories, setOpenDirectories] = useState({});
  const [selectedFilePaths, setSelectedFilePaths] = useState({});
  const [loadingFileKey, setLoadingFileKey] = useState(null);
  const [activeFile, setActiveFile] = useState(null);
  const [editorValue, setEditorValue] = useState("");
  const [isSavingFile, setIsSavingFile] = useState(false);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [openFiles, setOpenFiles] = useState({});

  const clearEditorState = () => {
    setActiveFile(null);
    setEditorValue("");
  };

  const apiBase = process.env.REACT_APP_API_URL || "http://127.0.0.1:8001";

  const resolveLanguage = (ext = "") => {
    const map = {
      js: "javascript",
      jsx: "javascript",
      ts: "typescript",
      tsx: "typescript",
      py: "python",
      json: "json",
      html: "html",
      css: "css",
      md: "markdown",
      yml: "yaml",
      yaml: "yaml",
      sh: "shell",
    };
    const normalized = (ext || "").toLowerCase();
    return map[normalized] || normalized || "plaintext";
  };

  const getProjectKey = (project) => {
    if (!project) {
      return "";
    }
    if (project.id !== undefined && project.id !== null) {
      return `id-${project.id}`;
    }
    const slug = (project.project_name || "").trim().toLowerCase();
    return `slug-${slug}`;
  };

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return;
    }

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      setUserEmail(payload.sub);
      if (payload.org) {
        setUserOrganization(payload.org);
      } else {
        setUserOrganization("");
      }
    } catch (e) {
      console.error("Invalid token:", e);
      handleLogout();
      return;
    }

    const loadProjects = async () => {
      try {
        const res = await fetch(`${apiBase}/projects`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (res.status === 401) {
          handleLogout();
          return;
        }
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        setProjects(Array.isArray(data?.projects) ? data.projects : []);
      } catch (err) {
        console.error("Failed to load projects:", err);
        setProjects([]);
      }
    };

    loadProjects();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUserEmail("");
    setUserOrganization("");
    navigate("/login");
  };

  const fetchProjectDirectory = async (project, projectKey, path = "") => {
    if (!project?.id) {
      return;
    }
    const normalizedPath = path || "";
    const existing = projectFiles?.[projectKey]?.[normalizedPath];
    if (existing) {
      return existing;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return;
    }

    try {
      setLoadingFileKey(`dir:${projectKey}:${normalizedPath}`);
      const url = new URL(`${apiBase}/projects/${project.id}/files`);
      if (normalizedPath) {
        url.searchParams.set("path", normalizedPath);
      }
      const res = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      const data = await res.json();
      const pathKey = data?.path || "";
      setProjectFiles((prev) => ({
        ...prev,
        [projectKey]: {
          ...(prev[projectKey] || {}),
          [pathKey]: Array.isArray(data?.entries) ? data.entries : [],
        },
      }));
      return data;
    } catch (e) {
      console.error("Failed to load project files:", e);
      toast.error(`Failed to load files: ${e.message || e}`);
  } finally {
    setLoadingFileKey(null);
  }
  return null;
  };

  const activeProjectKey = expandedProjectKey;
  const activeProjectDetails = activeProjectKey ? projectDetails[activeProjectKey] : null;
  const activeProject =
    activeProjectDetails?.project ||
    projects.find((proj) => getProjectKey(proj) === activeProjectKey) ||
    null;
  const activePaths = activeProjectDetails?.paths || null;
  const activeFileMap = activeProjectKey ? projectFiles[activeProjectKey] || {} : {};
  const selectedProjectFile = activeProjectKey ? selectedFilePaths[activeProjectKey] || "" : "";
  const isEditorDirty = Boolean(
    activeFile && editorValue !== (activeFile.content ?? "")
  );
  const canSaveFile = Boolean(activeFile?.projectId && selectedProjectFile);

  const renderDirectoryTree = (currentPath = "", depth = 0) => {
    if (!activeProjectKey) {
      return null;
    }

    const pathKey = currentPath || "";
    const entries = activeFileMap[pathKey];

    if (!entries || entries.length === 0) {
      if (pathKey === "" && activeProject?.id) {
        const isRootLoading = loadingFileKey === `dir:${activeProjectKey}:${pathKey}`;
        return (
          <button
            type="button"
            className={styles.projectFileLoadButton}
            onClick={() => fetchProjectDirectory(activeProject, activeProjectKey, "")}
          >
            {isRootLoading ? "Loading files..." : "Load Project Files"}
          </button>
        );
      }

      if (pathKey === "") {
        return (
          <p className={styles.projectFileHint}>
            {activeProject
              ? "No generated files yet. Run an extraction or generation workflow to populate this project."
              : "Select a project to explore its generated files."}
          </p>
        );
      }
      return null;
    }

    return (
      <ul className={styles.projectFilesList}>
        {entries.map((entry) => {
          const entryPath = entry.path;
          const isDirectory = entry.type === "directory";
          const entryKey = `${activeProjectKey}::${entryPath || ""}`;

          if (isDirectory) {
            const isOpen = !!openDirectories[entryKey];
            const isDirLoading = loadingFileKey === `dir:${activeProjectKey}:${entryPath}`;
            const handleToggle = () => {
              setOpenDirectories((prev) => ({
                ...prev,
                [entryKey]: !isOpen,
              }));
              if (!isOpen && activeProject?.id) {
                fetchProjectDirectory(activeProject, activeProjectKey, entryPath);
              }
            };

            return (
              <li
                key={entryKey || entry.name}
                className={styles.projectFileItem}
                style={{ marginLeft: depth * 12 }}
              >
                <button
                  type="button"
                  className={styles.projectFileButton}
                  onClick={handleToggle}
                >
                  <span className={styles.projectFileIcon}>{isOpen ? "▾" : "▸"}</span>
                  {entry.name}
                  {isDirLoading && (
                    <span className={styles.projectFileLoading}>Loading...</span>
                  )}
                </button>
                {isOpen && renderDirectoryTree(entryPath, depth + 1)}
              </li>
            );
          }

          const isFileLoading = loadingFileKey === `file:${activeProjectKey}:${entryPath}`;
          const isSelected = selectedProjectFile === entryPath;

          return (
            <li
              key={entryPath}
              className={styles.projectFileItem}
              style={{ marginLeft: depth * 12 }}
            >
              <button
                type="button"
                className={`${styles.projectFileButton} ${
                  isSelected ? styles.projectFileButtonActive : ""
                }`}
                onClick={() =>
                  activeProject?.id &&
                  fetchProjectFileContent(activeProject, activeProjectKey, entryPath)
                }
              >
                <span className={styles.projectFileIcon}>•</span>
                {entry.name}
                {isFileLoading && (
                  <span className={styles.projectFileLoading}>Loading...</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    );
  };

  const fetchProjectFileContent = async (project, projectKey, path) => {
    if (!project?.id || !path) {
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return;
    }

    try {
      setLoadingFileKey(`file:${projectKey}:${path}`);
      const url = new URL(`${apiBase}/projects/${project.id}/files/content`);
      url.searchParams.set("path", path);
      const res = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      const fetched = await res.json();
      const language = resolveLanguage(fetched?.language);
      const data = { ...fetched, language };
      const filePayload = {
        projectKey,
        projectId: project.id,
        projectName: project.project_name,
        ...data,
        originalContent: data.content || "",
      };
      setSelectedFilePaths((prev) => ({
        ...prev,
        [projectKey]: data?.path || path,
      }));
      setActiveFile(filePayload);
      setOpenFiles((prev) => {
        const projectEntries = prev[projectKey] || [];
        const existingIdx = projectEntries.findIndex((entry) => entry.path === filePayload.path);
        const nextEntries = [...projectEntries];
        if (existingIdx >= 0) {
          nextEntries[existingIdx] = filePayload;
        } else {
          nextEntries.push(filePayload);
        }
        return {
          ...prev,
          [projectKey]: nextEntries,
        };
      });
      setEditorValue(filePayload.content || "");
      return data;
    } catch (e) {
      console.error("Failed to load project file content:", e);
      toast.error(`Failed to load file: ${e.message || e}`);
    } finally {
      setLoadingFileKey(null);
    }
    return null;
  };

  const handleEditorChange = (value) => {
    setEditorValue(value ?? "");
  };

  const handleDiscardEditorChanges = () => {
    if (activeFile) {
      setEditorValue(activeFile.content ?? "");
    }
  };

  const handleSaveActiveFile = async () => {
    if (!canSaveFile || isSavingFile) {
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return;
    }

    try {
      setIsSavingFile(true);
      const res = await fetch(`${apiBase}/projects/${activeFile.projectId}/files/content`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          path: selectedProjectFile,
          content: editorValue ?? "",
        }),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      const saved = await res.json();
      setActiveFile((prev) =>
        prev
          ? {
              ...prev,
              content: editorValue ?? "",
              language: resolveLanguage(saved?.language || prev.language),
            }
          : prev
      );
      toast.success(`Saved ${saved?.path || "file"}`);
    } catch (e) {
      console.error("Failed to save file:", e);
      toast.error(`Failed to save file: ${e.message || e}`);
    } finally {
      setIsSavingFile(false);
    }
  };

  const handleRunTests = async () => {
    if (isRunningTests) {
      return;
    }
    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return;
    }
    try {
      setIsRunningTests(true);
      const res = await fetch(`${apiBase}/rag/run-generated-story-test`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      let payload = null;
      try {
        payload = await res.json();
      } catch (err) {
        payload = null;
      }
      const status = payload?.status || "Triggered";
      toast.success(`Test run status: ${status}`);
    } catch (e) {
      console.error("Failed to run generated tests:", e);
      toast.error(`Failed to run tests: ${e.message || e}`);
    } finally {
      setIsRunningTests(false);
    }
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
      const token = localStorage.getItem("token");
      if (!token) {
        handleLogout();
        return;
      }
      const res = await fetch(`${apiBase}/projects/save-details`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ project_name: projectName.trim(), framework, language }),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      const payload = await res.json().catch(() => null);
      const savedProject = payload?.project || null;
      toast.success('Project saved');
      // Optimistically add to local list
      setProjects((prev) => {
        if (savedProject) {
          return [savedProject, ...prev];
        }
        return [{
          organization: userOrganization,
          project_name: projectName.trim(),
          framework,
          language,
          created_at: new Date().toISOString()
        }, ...prev];
      });
    } catch (e) {
      console.error('Failed to save project:', e);
      toast.error(`Failed to save: ${e.message || e}`);
      return;
    }

    setShowDialog(false);
    navigate("/input", { state: { projectName: projectName } });
  };

  const handleDeleteProject = async (project) => {
    if (!project?.id) {
      toast.error("Cannot delete project: missing identifier.");
      return;
    }

    const confirmed = window.confirm(`Delete project "${project.project_name}"? This cannot be undone.`);
    if (!confirmed) {
      return;
    }

    const projectKey = getProjectKey(project);

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        handleLogout();
        return;
      }
      const res = await fetch(`${apiBase}/projects/${project.id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      toast.success(`Deleted project: ${project.project_name}`);
      setProjects((prev) =>
        prev.filter((p) => {
          if (p.id !== undefined && project.id !== undefined) {
            return p.id !== project.id;
          }
          return (p.project_name || "").trim().toLowerCase() !== (project.project_name || "").trim().toLowerCase();
        })
      );
      setProjectDetails((prev) => {
        const next = { ...prev };
        delete next[projectKey];
        return next;
      });
      if (expandedProjectKey === projectKey) {
        setExpandedProjectKey(null);
        clearEditorState();
      }
      if (loadingProjectKey === projectKey) {
        setLoadingProjectKey(null);
      }
    } catch (e) {
      console.error('Failed to delete project:', e);
      toast.error(`Failed to delete project: ${e.message || e}`);
    }
  };

  const handleToggleProject = async (project, explicitKey) => {
    const projectKey = explicitKey || getProjectKey(project);
    if (!projectKey) {
      return;
    }

    if (expandedProjectKey === projectKey) {
      setExpandedProjectKey(null);
      setLoadingFileKey(null);
      setOpenDirectories({});
      setSelectedFilePaths((prev) => {
        const next = { ...prev };
        delete next[projectKey];
        return next;
      });
      clearEditorState();
      return;
    }

    setExpandedProjectKey(projectKey);
    setOpenDirectories({});
    setLoadingFileKey(null);
    clearEditorState();
    setSelectedFilePaths((prev) => {
      const next = { ...prev };
      delete next[projectKey];
      return next;
    });

    if (projectDetails[projectKey]) {
      if (!projectFiles?.[projectKey]?.[""] && project?.id) {
        fetchProjectDirectory(project, projectKey, "");
      }
      return;
    }

    if (!project?.id) {
      setProjectDetails((prev) => ({
        ...prev,
        [projectKey]: { project },
      }));
      return;
    }

    try {
      setLoadingProjectKey(projectKey);
      const token = localStorage.getItem("token");
      if (!token) {
        handleLogout();
        return;
      }
      const res = await fetch(`${apiBase}/projects/${project.id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      const data = await res.json();
      setProjectDetails((prev) => ({
        ...prev,
        [projectKey]: data,
      }));
      fetchProjectDirectory(project, projectKey, "");
    } catch (e) {
      console.error('Failed to load project details:', e);
      toast.error(`Failed to load project details: ${e.message || e}`);
      setProjectDetails((prev) => ({
        ...prev,
        [projectKey]: { project },
      }));
    } finally {
      setLoadingProjectKey(null);
    }
  };

  const handleCloseEditor = () => {
    if (!expandedProjectKey) {
      return;
    }
    handleToggleProject(activeProject || null, expandedProjectKey);
  };

  const handleDownloadProject = async (project) => {
    if (!project?.id) {
      toast.error("Cannot download project: missing identifier.");
      return;
    }

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        handleLogout();
        return;
      }
      const res = await fetch(`${apiBase}/projects/${project.id}/download`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const safeName = (project.project_name || `project_${project.id}`)
        .trim()
        .replace(/[^\w\-]+/g, "_");

      const link = document.createElement("a");
      link.href = url;
      link.download = `${safeName || "project"}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`Downloading project: ${project.project_name}`);
    } catch (e) {
      console.error('Failed to download project:', e);
      toast.error(`Failed to download project: ${e.message || e}`);
    }
  };


  return (
    <div className={styles.homeContainer}>
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
          <span>{userOrganization || "Organization?"}</span>
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

      {expandedProjectKey && (
        <section className={styles.ideLayout}>
          <div className={styles.ideToolbar}>
            <div>
              <p className={styles.ideToolbarLabel}>Project editor</p>
              <h3 className={styles.ideToolbarTitle}>
                {activeProject?.project_name || "Generated files"}
              </h3>
              {selectedProjectFile && (
                <p className={styles.ideToolbarPath}>{selectedProjectFile}</p>
              )}
            </div>
            <div className={styles.ideToolbarActions}>
              <button
                type="button"
                className={`${styles.ideActionButton} ${styles.ideActionButtonPrimary}`}
                disabled={!canSaveFile || !isEditorDirty || isSavingFile}
                onClick={handleSaveActiveFile}
              >
                <i className="fa-solid fa-floppy-disk"></i>
                {isSavingFile ? "Saving..." : "Save changes"}
              </button>
              <button
                type="button"
                className={`${styles.ideActionButton} ${styles.ideActionButtonPrimary}`}
                onClick={handleRunTests}
                disabled={isRunningTests}
              >
                <i className="fa-solid fa-play"></i>
                {isRunningTests ? "Running..." : "Run tests"}
              </button>
              <button
                type="button"
                className={styles.ideActionButton}
                disabled={!isEditorDirty || isSavingFile}
                onClick={handleDiscardEditorChanges}
              >
                <i className="fa-solid fa-rotate-left"></i> Discard
              </button>
              <button
                type="button"
                className={`${styles.ideActionButton} ${styles.ideCloseButton}`}
                onClick={handleCloseEditor}
              >
                <i className="fa-solid fa-circle-xmark"></i> Close editor
              </button>
            </div>
          </div>

          <div className={styles.ideWorkspace}>
            <div className={styles.leftPanel}>
              <h4>Project Files</h4>
              {renderDirectoryTree()}
            </div>
            <div className={styles.rightPanel}>
              {activeFile ? (
                <Editor
                  height="100%"
                  language={resolveLanguage(activeFile.language)}
                  value={editorValue}
                  onChange={handleEditorChange}
                  options={{
                    readOnly: false,
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    fontSize: 14,
                    wordWrap: "on",
                  }}
                />
              ) : (
                <div className={styles.noFileSelected}>
                  <p>Select a file to view its content</p>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      <Dashboard
        projects={projects}
        expandedProjectKey={expandedProjectKey}
        loadingProjectKey={loadingProjectKey}
        getProjectKey={getProjectKey}
        hideRecentProjects={Boolean(expandedProjectKey)}
        onToggle={handleToggleProject}
        onOpen={async (p) => {
          try {
            const token = localStorage.getItem("token");
            if (!token) {
              handleLogout();
              return;
            }
            const res = await fetch(`${apiBase}/projects/activate`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({ project_name: p.project_name })
            });
            if (res.status === 401) {
              handleLogout();
              return;
            }
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
        onDownload={handleDownloadProject}
        onDelete={handleDeleteProject}
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
