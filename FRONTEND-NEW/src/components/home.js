import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import Dashboard from "./dashboard";
import Editor from "@monaco-editor/react";
import styles from "../css/Home.module.css";
import API_BASE_URL from "../config";
import useAppStore from "../state/useAppStore";
import useScopedToast from "../hooks/useScopedToast";
import { openAuthenticatedReport } from "../utils/reportViewer";

const formatLabel = (label = "") =>
  label.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());

const normalizeEditorPath = (value = "") =>
  String(value || "").replace(/\\/g, "/").replace(/^\/+/, "").trim().toLowerCase();

const basenameWithoutExtension = (value = "") => {
  const normalized = String(value || "").replace(/\\/g, "/");
  const filename = normalized.split("/").filter(Boolean).pop() || "";
  return filename.replace(/\.[^.]+$/i, "").toLowerCase();
};

const buildImpactLineMatches = (content = "", item = {}, summary = null) => {
  const lines = String(content || "").split(/\r?\n/);
  const matchedLines = new Set();
  const terms = new Set();

  (Array.isArray(item?.where_impacted) ? item.where_impacted : []).forEach((value) => {
    const normalized = String(value || "").trim();
    if (normalized) {
      terms.add(normalized.toLowerCase());
    }
  });

  (Array.isArray(item?.impacted_page_modules) ? item.impacted_page_modules : []).forEach((value) => {
    const normalized = basenameWithoutExtension(value);
    if (normalized) {
      terms.add(normalized);
      terms.add(normalized.replace(/_page_methods$/i, ""));
      terms.add(normalized.replace(/_page$/i, ""));
    }
  });

  (Array.isArray(item?.matched_via) ? item.matched_via : []).forEach((value) => {
    const normalized = String(value || "").trim().toLowerCase();
    if (normalized) {
      terms.add(normalized);
    }
  });

  if (summary?.affectedPage) {
    terms.add(String(summary.affectedPage).trim().toLowerCase());
  }
  (Array.isArray(summary?.affectedPages) ? summary.affectedPages : []).forEach((value) => {
    const normalized = String(value || "").trim().toLowerCase();
    if (normalized) {
      terms.add(normalized);
    }
  });

  lines.forEach((line, index) => {
    const lower = line.toLowerCase();
    if (!lower.trim()) {
      return;
    }
    for (const term of terms) {
      if (term && lower.includes(term)) {
        matchedLines.add(index + 1);
      }
    }
  });

  return Array.from(matchedLines).sort((a, b) => a - b);
};

const Home = ({ editorOnly = false }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const notify = useScopedToast();
  const settings = useAppStore((state) => state.settings);
  const setSettings = useAppStore((state) => state.setSettings);
  const setActiveProject = useAppStore((state) => state.setActiveProject);
  const activeProjectId = useAppStore((state) => state.project.activeProjectId);
  const executionFilters = useAppStore((state) => state.execution.executionFilters);
  const categorySelections = useAppStore((state) => state.execution.categorySelections);
  const useUpdatedExecutionByCategory = useAppStore(
    (state) => state.execution.useUpdatedExecutionByCategory,
  );
  const tagCounts = useAppStore((state) => state.execution.tagCounts);
  const lastExecutionStatus = useAppStore((state) => state.execution.lastExecutionStatus);
  const lastExecutionError = useAppStore((state) => state.execution.lastExecutionError);
  const setExecutionFilters = useAppStore((state) => state.setExecutionFilters);
  const setCategorySelections = useAppStore((state) => state.setCategorySelections);
  const setUseUpdatedExecutionByCategory = useAppStore(
    (state) => state.setUseUpdatedExecutionByCategory,
  );
  const setTagCounts = useAppStore((state) => state.setTagCounts);
  const setExecutionStatus = useAppStore((state) => state.setExecutionStatus);
  const setInputStartFlow = useAppStore((state) => state.setInputStartFlow);
  const setInputFlow = useAppStore((state) => state.setInputFlow);
  const inputStartFlow = useAppStore((state) => state.navigation.inputStartFlow);
  const impactedSummary = useAppStore((state) => state.testCases.impactedSummary);
  const impactedItems = useAppStore((state) => state.testCases.impactedItems);

  const [showDialog, setShowDialog] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [framework, setFramework] = useState(settings.framework || "Playwright");
  const [language, setLanguage] = useState(settings.language || "Python");
  const [userEmail, setUserEmail] = useState("");
  const [userOrganization, setUserOrganization] = useState("");
  const [projects, setProjects] = useState([]);
  const [totalTestCases, setTotalTestCases] = useState(0);
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
  const [editorAutoOpened, setEditorAutoOpened] = useState(false);
  const [startFlow, setStartFlow] = useState(settings.startFlow || "ocr");
  const [hasRunTestsInSession, setHasRunTestsInSession] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const editorRef = React.useRef(null);
  const monacoRef = React.useRef(null);
  const impactDecorationIdsRef = React.useRef([]);

  const isEditorOnly = editorOnly || location.pathname === "/editor";
  const editorParams = new URLSearchParams(location.search || "");
  const editorProjectId = editorParams.get("projectId");
  const editorProjectName = editorParams.get("projectName");
  const editorRequestedPath = editorParams.get("path");
  const [showGitDialog, setShowGitDialog] = useState(false);
  const [gitRepoUrl, setGitRepoUrl] = useState("");
  const [gitBaseBranch, setGitBaseBranch] = useState("main");
  const [gitTargetBranch, setGitTargetBranch] = useState(
    "feature/generated-tests",
  );
  const [gitCommitMessage, setGitCommitMessage] = useState(
    "Sync generated tests",
  );
  const [gitUsername, setGitUsername] = useState("");
  const [gitToken, setGitToken] = useState("");
  const [gitAuthorName, setGitAuthorName] = useState("");
  const [gitAuthorEmail, setGitAuthorEmail] = useState("");
  const [gitTargetProject, setGitTargetProject] = useState(null);
  const [isPushingToGit, setIsPushingToGit] = useState(false);

  useEffect(() => {
    setSettings({ framework, language, startFlow });
  }, [framework, language, startFlow, setSettings]);

  const clearEditorState = () => {
    setActiveFile(null);
    setEditorValue("");
  };

  const apiBase = API_BASE_URL;

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
        try {
          const countsRes = await fetch(`${apiBase}/projects/testcase-counts`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (countsRes.ok) {
            const countsData = await countsRes.json();
            setTotalTestCases(Number(countsData?.total) || 0);
          } else {
            setTotalTestCases(0);
          }
        } catch (err) {
          setTotalTestCases(0);
        }
      } catch (err) {
        console.error("Failed to load projects:", err);
        setProjects([]);
        setTotalTestCases(0);
      }
    };

    loadProjects();
  }, []);

  useEffect(() => {
    const openFile = location.state?.openFile;
    if (!openFile?.path) {
      return;
    }

    if (!projects.length) {
      return;
    }

    const project =
      openFile.projectId !== undefined && openFile.projectId !== null
        ? projects.find((item) => String(item.id) === String(openFile.projectId))
        : projects.find(
            (item) =>
              (item.project_name || "").trim().toLowerCase() ===
              String(openFile.projectName || "").trim().toLowerCase()
          );

    if (!project) {
      return;
    }

    const projectKey = getProjectKey(project);
    const normalizedPath = String(openFile.path).replace(/^\/+/, "");

    if (expandedProjectKey !== projectKey) {
      handleToggleProject(project, projectKey);
    } else if (!projectFiles?.[projectKey]?.[""]) {
      fetchProjectDirectory(project, projectKey, "");
    }

    fetchProjectFileContent(project, projectKey, normalizedPath);
    navigate(".", { replace: true, state: {} });
  }, [location.state, projects, expandedProjectKey, projectFiles]);

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
      notify.error(`Failed to load files: ${e.message || e}`);
    } finally {
      setLoadingFileKey(null);
    }
    return null;
  };

  const activeProjectKey = expandedProjectKey;
  const activeProjectDetails = activeProjectKey
    ? projectDetails[activeProjectKey]
    : null;
  const activeProject =
    activeProjectDetails?.project ||
    projects.find((proj) => getProjectKey(proj) === activeProjectKey) ||
    null;
  const activePaths = activeProjectDetails?.paths || null;
  const activeFileMap = activeProjectKey
    ? projectFiles[activeProjectKey] || {}
    : {};
  const selectedProjectFile = activeProjectKey
    ? selectedFilePaths[activeProjectKey] || ""
    : "";
  const isEditorDirty = Boolean(
    activeFile && editorValue !== (activeFile.content ?? ""),
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
        const isRootLoading =
          loadingFileKey === `dir:${activeProjectKey}:${pathKey}`;
        return (
          <button
            type="button"
            className={styles.projectFileLoadButton}
            onClick={() =>
              fetchProjectDirectory(activeProject, activeProjectKey, "")
            }
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
            const isDirLoading =
              loadingFileKey === `dir:${activeProjectKey}:${entryPath}`;
            const handleToggle = () => {
              setOpenDirectories((prev) => ({
                ...prev,
                [entryKey]: !isOpen,
              }));
              if (!isOpen && activeProject?.id) {
                fetchProjectDirectory(
                  activeProject,
                  activeProjectKey,
                  entryPath,
                );
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
                  <span className={styles.projectFileIcon}>
                    {isOpen ? "▾" : "▸"}
                  </span>
                  {entry.name}
                  {isDirLoading && (
                    <span className={styles.projectFileLoading}>
                      Loading...
                    </span>
                  )}
                </button>
                {isOpen && renderDirectoryTree(entryPath, depth + 1)}
              </li>
            );
          }

          const isFileLoading =
            loadingFileKey === `file:${activeProjectKey}:${entryPath}`;
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
                  fetchProjectFileContent(
                    activeProject,
                    activeProjectKey,
                    entryPath,
                  )
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
        const existingIdx = projectEntries.findIndex(
          (entry) => entry.path === filePayload.path,
        );
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
      notify.error(`Failed to load file: ${e.message || e}`);
    } finally {
      setLoadingFileKey(null);
    }
    return null;
  };

  const fetchProjectTree = async (project, projectKey, path = "") => {
    const data = await fetchProjectDirectory(project, projectKey, path);
    const entries = Array.isArray(data?.entries) ? data.entries : [];
    for (const entry of entries) {
      if (entry.type === "directory") {
        await fetchProjectTree(project, projectKey, entry.path);
      }
    }
  };

  const handleEditorChange = (value) => {
    setEditorValue(value ?? "");
  };

  const applyPythonDiagnostics = React.useCallback(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor?.getModel?.();
    if (!editor || !monaco || !model) {
      return;
    }

    const diagnostics = Array.isArray(activeFile?.diagnostics) ? activeFile.diagnostics : [];
    const markers = diagnostics.map((item) => ({
      startLineNumber: Math.max(1, Number(item?.line) || 1),
      startColumn: Math.max(1, Number(item?.column) || 1),
      endLineNumber: Math.max(1, Number(item?.end_line) || Number(item?.line) || 1),
      endColumn: Math.max(
        Math.max(1, Number(item?.column) || 1) + 1,
        Number(item?.end_column) || Math.max(1, Number(item?.column) || 1) + 1,
      ),
      severity:
        String(item?.severity || "").toLowerCase() === "warning"
          ? monaco.MarkerSeverity.Warning
          : String(item?.severity || "").toLowerCase() === "info"
            ? monaco.MarkerSeverity.Info
            : monaco.MarkerSeverity.Error,
      message: item?.message || "Python error",
      code: item?.code || undefined,
    }));

    monaco.editor.setModelMarkers(model, "python-diagnostics", markers);
  }, [activeFile?.diagnostics]);

  const applyImpactHighlights = React.useCallback(() => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor?.getModel?.();
    if (!editor || !monaco || !model) {
      return;
    }

    const owner = "impact-highlights";
    const clearDecorations = () => {
      impactDecorationIdsRef.current = editor.deltaDecorations(
        impactDecorationIdsRef.current || [],
        [],
      );
      monaco.editor.setModelMarkers(model, owner, []);
    };

    const activePath = normalizeEditorPath(activeFile?.path || selectedProjectFile || "");
    if (!activePath || !Array.isArray(impactedItems) || impactedItems.length === 0) {
      clearDecorations();
      return;
    }

    const relevantItems = impactedItems.filter((item) => {
      const runnerPath = normalizeEditorPath(item?.runner_script_path || "");
      const testcasePath = normalizeEditorPath(item?.script_path || "");
      return activePath === runnerPath || activePath === testcasePath;
    });

    if (!relevantItems.length) {
      clearDecorations();
      return;
    }

    const markers = [];
    const decorations = [];
    const seenLines = new Set();
    const messageBase =
      impactedSummary?.affectedPage || impactedSummary?.oldImageName
        ? `Potential impact from ${impactedSummary?.affectedPage || impactedSummary?.oldImageName}`
        : "Potential impact from recent screen change";

    relevantItems.forEach((item) => {
      const directLabel =
        item?.display_name || item?.test_name || item?.case_uuid || "Impacted testcase";
      const matchedLines = buildImpactLineMatches(editorValue, item, impactedSummary);
      const linesToMark = matchedLines.length ? matchedLines : [1];

      linesToMark.forEach((lineNumber) => {
        if (seenLines.has(lineNumber)) {
          return;
        }
        seenLines.add(lineNumber);
        const lineLength = model.getLineLength(lineNumber) || 1;
        markers.push({
          startLineNumber: lineNumber,
          startColumn: 1,
          endLineNumber: lineNumber,
          endColumn: Math.max(2, lineLength + 1),
          severity: monaco.MarkerSeverity.Warning,
          message: `${messageBase}. Review ${directLabel}.`,
        });
        decorations.push({
          range: new monaco.Range(lineNumber, 1, lineNumber, 1),
          options: {
            isWholeLine: true,
            className: "impactLineHighlight",
            glyphMarginClassName: "impactGlyphMargin",
            glyphMarginHoverMessage: {
              value: `${messageBase}. Review ${directLabel}.`,
            },
            linesDecorationsTooltip: `${messageBase}. Review ${directLabel}.`,
          },
        });
      });
    });

    impactDecorationIdsRef.current = editor.deltaDecorations(
      impactDecorationIdsRef.current || [],
      decorations,
    );
    monaco.editor.setModelMarkers(model, owner, markers);
  }, [activeFile?.path, editorValue, impactedItems, impactedSummary, selectedProjectFile]);

  React.useEffect(() => {
    applyImpactHighlights();
  }, [applyImpactHighlights]);

  React.useEffect(() => {
    applyPythonDiagnostics();
  }, [applyPythonDiagnostics]);

  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    applyImpactHighlights();
    applyPythonDiagnostics();
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
      const res = await fetch(
        `${apiBase}/projects/${activeFile.projectId}/files/content`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            path: selectedProjectFile,
            content: editorValue ?? "",
          }),
        },
      );
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
              diagnostics: Array.isArray(saved?.diagnostics) ? saved.diagnostics : [],
            }
          : prev,
      );
      notify.success(`Saved ${saved?.path || "file"}`);
    } catch (e) {
      console.error("Failed to save file:", e);
      notify.error(`Failed to save file: ${e.message || e}`);
    } finally {
      setIsSavingFile(false);
    }
  };

  const formatServerError = (err, fallbackMessage) => {
    const fallback = fallbackMessage || "Request failed.";
    if (!err) return fallback;
    const raw =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      err?.response?.data?.error;
    if (!raw) return err.message || fallback;
    if (Array.isArray(raw)) {
      return raw.map((item) => item?.msg || item?.message || JSON.stringify(item)).join("; ");
    }
    return typeof raw === "string" ? raw : JSON.stringify(raw);
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
    const projectId = activeProject?.id || activeProjectId || editorProjectId;
    if (!projectId) {
      notify.error("Project ID not found. Please activate a project first.");
      return;
    }
    try {
      setIsRunningTests(true);
      const selectedTags = {
        ui: Object.keys(executionFilters.ui).filter((tag) => executionFilters.ui[tag]),
        accessibility: categorySelections.accessibility ? ["__all__"] : [],
        security: categorySelections.security ? ["__all__"] : [],
      };
      const useUpdated = Object.values(useUpdatedExecutionByCategory).some(Boolean);
      const requestPayload = {
        tags: selectedTags,
        use_test_plan: useUpdated ? useUpdatedExecutionByCategory : false,
      };
      const res = await fetch(`${apiBase}/${projectId}/rag/run-generated-story-test`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
      });
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      let responsePayload = null;
      try {
        responsePayload = await res.json();
      } catch (err) {
        responsePayload = null;
      }
      const status = responsePayload?.status || "Triggered";
      if (status === "PASS") {
        notify.success("✅ Tests executed successfully.");
        setExecutionStatus({ status: "PASS", error: "" });
        setHasRunTestsInSession(true);
      } else {
        notify.error("❌ Tests failed. Check logs for details.");
        setExecutionStatus({ status, error: "" });
        setHasRunTestsInSession(true);
      }
    } catch (e) {
      console.error("Failed to run generated tests:", e);
      const message = formatServerError(e, "Failed to run tests.");
      notify.error(message);
      setExecutionStatus({ status: "ERROR", error: message });
      setHasRunTestsInSession(true);
    } finally {
      setIsRunningTests(false);
    }
  };

  const handleViewReport = async () => {
    if (reportLoading) {
      return;
    }
    const projectId = activeProject?.id || activeProjectId;
    if (!projectId) {
      notify.error("Project ID not found. Please activate a project first.");
      return;
    }
    setReportLoading(true);
    try {
      await openAuthenticatedReport(apiBase, projectId);
    } catch (e) {
      notify.error(`Failed to open report: ${e.message || e}`);
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const projectId = activeProjectId || editorProjectId;
    if (!expandedProjectKey || !projectId) {
      return () => {
        isMounted = false;
      };
    }
    const token = localStorage.getItem("token");
    if (!token) {
      return () => {
        isMounted = false;
      };
    }
    const timer = setTimeout(async () => {
      try {
        const selectedTags = {
          ui: Object.keys(executionFilters.ui).filter((tag) => executionFilters.ui[tag]),
          accessibility: categorySelections.accessibility ? ["__all__"] : [],
          security: categorySelections.security ? ["__all__"] : [],
        };
        const useUpdated = Object.values(useUpdatedExecutionByCategory).some(Boolean);
        const payload = {
          tags: selectedTags,
          use_test_plan: useUpdated ? useUpdatedExecutionByCategory : false,
        };
        const res = await fetch(`${apiBase}/${projectId}/rag/preview-tests`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          return;
        }
        const data = await res.json();
        if (isMounted && data?.tag_counts) {
          setTagCounts(data.tag_counts);
        }
      } catch (err) {
        // ignore preview errors in editor
      }
    }, 250);
    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [
    activeProjectId,
    editorProjectId,
    expandedProjectKey,
    executionFilters,
    categorySelections,
    useUpdatedExecutionByCategory,
    setTagCounts,
  ]);

  useEffect(() => {
    setHasRunTestsInSession(false);
  }, [expandedProjectKey]);

  const handleStartProject = async () => {
    if (!projectName.trim()) {
      notify.error("Please enter a project name."); // Using toast for better UX
      return;
    }

    // Prevent duplicate project names (client-side)
    const exists = projects.some(
      (p) =>
        (p?.project_name || "").trim().toLowerCase() ===
        projectName.trim().toLowerCase(),
    );
    if (exists) {
      notify.error(`Project '${projectName.trim()}' already exists.`);
      return;
    }

    console.log("Project Name:", projectName);
    console.log("Test Framework:", framework);
    console.log("Programming Language:", language);

    const resolvedFlow = inputStartFlow || startFlow;
    let savedProject = null;
    // Send details to backend
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        handleLogout();
        return;
      }
      const res = await fetch(`${apiBase}/projects/save-details`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          project_name: projectName.trim(),
          framework,
          language,
          ...(resolvedFlow === "url" ? { project_mode: "URL_EXECUTION" } : {}),
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
      const payload = await res.json().catch(() => null);
      savedProject = payload?.project || null;
      if (savedProject?.id || savedProject?.project_name) {
        setActiveProject({
          id: savedProject?.id ? String(savedProject.id) : null,
          name: savedProject?.project_name || null,
        });
      }
      notify.success("Project saved");
      // Optimistically add to local list
      setProjects((prev) => {
        if (savedProject) {
          return [savedProject, ...prev];
        }
        return [
          {
            organization: userOrganization,
            project_name: projectName.trim(),
            framework,
            language,
            created_at: new Date().toISOString(),
          },
          ...prev,
        ];
      });
    } catch (e) {
      console.error("Failed to save project:", e);
      notify.error(`Failed to save: ${e.message || e}`);
      return;
    }

    setShowDialog(false);
    const startPath = resolvedFlow === "url" ? "/input/url" : "/input/upload";
    navigate(startPath, {
      state: {
        projectName: projectName,
        projectId: savedProject?.id,
        flow: resolvedFlow,
      },
    });
      setStartFlow("ocr");
      setInputStartFlow(null);
  };

  const handleDeleteProject = async (project) => {
    if (!project?.id) {
      notify.error("Cannot delete project: missing identifier.");
      return;
    }

    const confirmed = window.confirm(
      `Delete project "${project.project_name}"? This cannot be undone.`,
    );
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
        method: "DELETE",
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
      notify.success(`Deleted project: ${project.project_name}`);
      setProjects((prev) =>
        prev.filter((p) => {
          if (p.id !== undefined && project.id !== undefined) {
            return p.id !== project.id;
          }
          return (
            (p.project_name || "").trim().toLowerCase() !==
            (project.project_name || "").trim().toLowerCase()
          );
        }),
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
      console.error("Failed to delete project:", e);
      notify.error(`Failed to delete project: ${e.message || e}`);
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
      console.error("Failed to load project details:", e);
      notify.error(`Failed to load project details: ${e.message || e}`);
      setProjectDetails((prev) => ({
        ...prev,
        [projectKey]: { project },
      }));
    } finally {
      setLoadingProjectKey(null);
    }
  };

  const handleCloseEditor = () => {
    if (isEditorOnly) {
      setExpandedProjectKey(null);
      setLoadingProjectKey(null);
      setLoadingFileKey(null);
      setOpenDirectories({});
      setSelectedFilePaths({});
      setOpenFiles({});
      clearEditorState();
      try {
        window.close();
      } catch (e) {
        // Ignore and fall back to in-app navigation below.
      }
      navigate("/", { replace: true });
      return;
    }
    if (!expandedProjectKey) {
      return;
    }
    handleToggleProject(activeProject || null, expandedProjectKey);
  };

  useEffect(() => {
    if (!isEditorOnly || editorAutoOpened) {
      return;
    }
    if (!projects.length) {
      return;
    }
    const matched = projects.find((p) => {
      if (editorProjectId && String(p.id) === String(editorProjectId)) {
        return true;
      }
      if (editorProjectName) {
        return (
          (p.project_name || "").trim().toLowerCase() ===
          editorProjectName.trim().toLowerCase()
        );
      }
      return false;
    });
    if (matched) {
      handleConfigureProject(matched, getProjectKey(matched));
      setEditorAutoOpened(true);
      return;
    }
    if (editorProjectId || editorProjectName) {
      notify.error("Project not found for editor view.");
      setEditorAutoOpened(true);
    }
  }, [
    isEditorOnly,
    editorAutoOpened,
    projects,
    editorProjectId,
    editorProjectName,
  ]);

  useEffect(() => {
    if (!isEditorOnly || !editorRequestedPath || !projects.length) {
      return;
    }

    const normalizedPath = String(editorRequestedPath).replace(/^\/+/, "");
    if (!normalizedPath) {
      return;
    }

    const matchedProject = projects.find((p) => {
      if (editorProjectId && String(p.id) === String(editorProjectId)) {
        return true;
      }
      if (editorProjectName) {
        return (
          (p.project_name || "").trim().toLowerCase() ===
          editorProjectName.trim().toLowerCase()
        );
      }
      return false;
    });

    if (!matchedProject) {
      return;
    }

    const matchedProjectKey = getProjectKey(matchedProject);
    if (!matchedProjectKey) {
      return;
    }

    if (expandedProjectKey !== matchedProjectKey) {
      return;
    }

    if (normalizeEditorPath(selectedProjectFile || "") === normalizeEditorPath(normalizedPath)) {
      return;
    }

    fetchProjectFileContent(matchedProject, matchedProjectKey, normalizedPath);
  }, [
    isEditorOnly,
    editorRequestedPath,
    projects,
    editorProjectId,
    editorProjectName,
    expandedProjectKey,
    selectedProjectFile,
  ]);

  const handleDownloadProject = async (project) => {
    if (!project?.id) {
      notify.error("Cannot download project: missing identifier.");
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
      notify.success(`Downloading project: ${project.project_name}`);
    } catch (e) {
      console.error("Failed to download project:", e);
      notify.error(`Failed to download project: ${e.message || e}`);
    }
  };

  const handleConfigureInNewTab = (project) => {
    if (!project) {
      return;
    }
    const params = new URLSearchParams();
    if (project.id) {
      params.set("projectId", String(project.id));
    }
    if (project.project_name) {
      params.set("projectName", project.project_name);
    }
    const query = params.toString();
    const basePath = "/editor";
    const url = query
      ? `${window.location.origin}${basePath}?${query}`
      : `${window.location.origin}${basePath}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const activateProjectForFlow = async (project) => {
    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return null;
    }

    const res = await fetch(`${apiBase}/projects/activate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ project_name: project.project_name }),
    });
    if (res.status === 401) {
      handleLogout();
      return null;
    }
    if (!res.ok) {
      const txt = await res.text().catch(() => null);
      throw new Error(txt || `Server returned ${res.status}`);
    }

    const payload = await res.json();
    const resolvedProjectId = payload?.project?.id;
    if (resolvedProjectId) {
      setActiveProject({
        id: String(resolvedProjectId),
        name: project.project_name || null,
      });
    } else if (project.project_name) {
      setActiveProject({ id: null, name: project.project_name });
    }

    const projectMode =
      payload?.project?.project_mode || project.project_mode || "OCR_EXECUTION";
    const flow = projectMode === "URL_EXECUTION" ? "url" : "ocr";
    setInputFlow(flow);
    setInputStartFlow(null);

    return {
      flow,
      projectId: resolvedProjectId,
      projectName: project.project_name,
    };
  };

  const handleOpenProject = async (project) => {
    const activation = await activateProjectForFlow(project);
    if (!activation) {
      return;
    }

    notify.success(`Activated project: ${project.project_name}`);
    const targetPath = activation.flow === "url" ? "/input/url" : "/input/upload";
    navigate(targetPath, {
      state: {
        projectName: activation.projectName,
        projectId: activation.projectId,
        flow: activation.flow,
      },
    });
  };

  const handleImageUpdate = async (project) => {
    const activation = await activateProjectForFlow(project);
    if (!activation) {
      return;
    }

    notify.success(`Opened image updates for: ${project.project_name}`);
    navigate("/input/image-update", {
      state: {
        projectName: activation.projectName,
        projectId: activation.projectId,
        flow: activation.flow,
        mode: "maintenance",
      },
    });
  };

  const handleConfigureProject = async (project, explicitKey) => {
    const projectKey = explicitKey || getProjectKey(project);
    if (!projectKey) {
      return;
    }

    if (expandedProjectKey === projectKey) {
      if (project?.id) {
        await fetchProjectTree(project, projectKey, "");
      }
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
      if (project?.id) {
        await fetchProjectTree(project, projectKey, "");
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
      await fetchProjectTree(project, projectKey, "");
    } catch (e) {
      console.error("Failed to load project details:", e);
      notify.error(`Failed to load project details: ${e.message || e}`);
      setProjectDetails((prev) => ({
        ...prev,
        [projectKey]: { project },
      }));
    } finally {
      setLoadingProjectKey(null);
    }
  };

  const handlePushProjectToGit = (project) => {
    if (!project) {
      notify.error("Select a project to push.");
      return;
    }
    setGitTargetProject(project);
    setShowGitDialog(true);
  };

  const handleGitDialogClose = () => {
    if (isPushingToGit) {
      return;
    }
    setShowGitDialog(false);
    setGitRepoUrl("");
    setGitBaseBranch("main");
    setGitTargetBranch("feature/generated-tests");
    setGitCommitMessage("Sync generated tests");
    setGitUsername("");
    setGitToken("");
    setGitAuthorName("");
    setGitAuthorEmail("");
    setGitTargetProject(null);
  };


  const handleGitDialogSubmit = async () => {
    if (!gitTargetProject?.id) {
      notify.error("Missing project identifier.");
      return;
    }
    if (
      !gitRepoUrl.trim() ||
      !gitBaseBranch.trim() ||
      !gitTargetBranch.trim() ||
      !gitCommitMessage.trim() ||
      !gitUsername.trim() ||
      !gitToken.trim() ||
      !gitAuthorName.trim() ||
      !gitAuthorEmail.trim()
    ) {
      notify.error("All Git fields are required.");
      return;
    }

    if (["main", "master"].includes(gitTargetBranch.trim().toLowerCase())) {
      notify.error("Target branch cannot be main/master.");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      handleLogout();
      return;
    }

    try {
      setIsPushingToGit(true);
      const res = await fetch(
        `${apiBase}/projects/${gitTargetProject.id}/git/push`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            repo_url: gitRepoUrl.trim(),
            base_branch: gitBaseBranch.trim(),
            target_branch: gitTargetBranch.trim(),
            git_username: gitUsername.trim(),
            git_token: gitToken.trim(),
            commit_message: gitCommitMessage.trim(),
            author_name: gitAuthorName.trim(),
            author_email: gitAuthorEmail.trim(),
          }),
        },
      );
      if (res.status === 401) {
        handleLogout();
        return;
      }
      if (!res.ok) {
        const txt = await res.text().catch(() => null);
        throw new Error(txt || `Server returned ${res.status}`);
      }
      const payload = await res.json().catch(() => null);
      notify.success(payload?.message || "Project pushed to Git.");
      handleGitDialogClose();
    } catch (e) {
      console.error("Failed to push project to Git:", e);
      notify.error(`Failed to push project: ${e.message || e}`);
    } finally {
      setIsPushingToGit(false);
    }
  };

  return (
    <div
      className={`${styles.homeContainer} ${isEditorOnly ? styles.editorOnly : ""}`}
    >
      <nav className={styles.navbar}>
        <div className={styles.navbarBrand}>
          <i className={`fa fa-code ${styles.navbarIcon}`}></i>
          <div>
            <h4 className={styles.navbarTitle}>AutoTest Studio</h4>
            <p className={styles.navbarSubtitle}>
              Automation Development Platform
            </p>
          </div>
        </div>

        <div className={styles.navbarUser}>
          <span>{userOrganization || "Organization?"}</span>
          <span>{userEmail}</span>
          <button onClick={handleLogout} className={styles.logoutButton}>
            Logout
          </button>
        </div>
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

          <div className={styles.ideFilters}>
            <div className={styles.ideFiltersTitle}>Execution filters</div>
            <div className={styles.ideFilterGroup}>
              {["regression", "functional"].map((tag) => {
                const count = tagCounts?.ui?.[tag] ?? 0;
                return (
                  <label key={`ui-${tag}`} className={styles.ideFilterItem}>
                    <input
                      type="checkbox"
                      checked={executionFilters.ui[tag]}
                      onChange={() =>
                        setExecutionFilters({
                          ...executionFilters,
                          ui: { ...executionFilters.ui, [tag]: !executionFilters.ui[tag] },
                        })
                      }
                    />
                    <span>
                      {formatLabel(tag)}
                      {executionFilters.ui[tag] ? ` (${count})` : ""}
                    </span>
                  </label>
                );
              })}
              <label className={styles.ideFilterToggle}>
                <input
                  type="checkbox"
                  checked={useUpdatedExecutionByCategory.ui}
                  onChange={() =>
                    setUseUpdatedExecutionByCategory({
                      ...useUpdatedExecutionByCategory,
                      ui: !useUpdatedExecutionByCategory.ui,
                    })
                  }
                />
                Run only updated tests (UI)
              </label>
              <label className={styles.ideFilterToggle}>
                <input
                  type="checkbox"
                  checked={categorySelections.accessibility}
                  onChange={() =>
                    setCategorySelections({
                      ...categorySelections,
                      accessibility: !categorySelections.accessibility,
                    })
                  }
                />
                Include Accessibility tests
              </label>
              <label className={styles.ideFilterToggle}>
                <input
                  type="checkbox"
                  checked={categorySelections.security}
                  onChange={() =>
                    setCategorySelections({
                      ...categorySelections,
                      security: !categorySelections.security,
                    })
                  }
                />
                Include Security tests
              </label>
            </div>

            <div className={styles.ideFiltersActions}>
              <button
                type="button"
                className={styles.ideReportButton}
                onClick={handleViewReport}
                disabled={reportLoading}
              >
                {reportLoading ? "Opening report..." : "Report"}
              </button>
              {hasRunTestsInSession && lastExecutionStatus ? (
                <div className={styles.ideFiltersStatus}>
                  <span className={styles.ideFiltersStatusLabel}>Test result:</span>
                  <span
                    className={`${styles.ideFiltersStatusValue} ${
                      lastExecutionStatus === "PASS"
                        ? styles.statusPass
                        : styles.statusFail
                    }`}
                  >
                    {lastExecutionStatus === "PASS" ? "PASS" : "FAIL"}
                  </span>
                </div>
              ) : null}
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
                  onMount={handleEditorMount}
                  options={{
                    readOnly: false,
                    glyphMargin: true,
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

      {!isEditorOnly && (
        <Dashboard
          projects={projects}
          totalTestCases={totalTestCases}
          expandedProjectKey={expandedProjectKey}
          loadingProjectKey={loadingProjectKey}
          getProjectKey={getProjectKey}
          hideRecentProjects={Boolean(expandedProjectKey)}
          onToggle={handleToggleProject}
          onConfigure={handleConfigureInNewTab}
          onOpen={async (p) => {
            try {
              await handleOpenProject(p);
            } catch (e) {
              console.error("Failed to activate project:", e);
              notify.error(`Failed to open project: ${e.message || e}`);
            }
          }}
          onImageUpdate={async (p) => {
            try {
              await handleImageUpdate(p);
            } catch (e) {
              console.error("Failed to open image update flow:", e);
              notify.error(`Failed to open image updates: ${e.message || e}`);
            }
          }}
          onDownload={handleDownloadProject}
          onDelete={handleDeleteProject}
          onPushToGit={handlePushProjectToGit}
          onStartOCRProject={() => {
            setStartFlow("ocr");
            setInputStartFlow("ocr");
            setShowDialog(true);
          }}
          onStartUrlExecution={() => {
            setStartFlow("url");
            setInputStartFlow("url");
            setShowDialog(true);
          }}
        />
      )}

      {/* Projects are now displayed inside Dashboard's Recent Projects */}

      {/* Project Setup Dialog */}
      {!isEditorOnly && showDialog && (
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

      {showGitDialog && (
        <div className={styles.dialogOverlay}>
          <div className={styles.dialogContent}>
            <h2 className={styles.dialogContentH2}>Push Project to Git</h2>

            <label className={styles.formLabel}>
              Repository URL:
              <input
                type="text"
                value={gitRepoUrl}
                onChange={(e) => setGitRepoUrl(e.target.value)}
                placeholder="https://github.com/user/repo.git"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Base Branch:
              <input
                type="text"
                value={gitBaseBranch}
                onChange={(e) => setGitBaseBranch(e.target.value)}
                placeholder="main"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Target Branch:
              <input
                type="text"
                value={gitTargetBranch}
                onChange={(e) => setGitTargetBranch(e.target.value)}
                placeholder="feature/generated-tests"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Git Username:
              <input
                type="text"
                value={gitUsername}
                onChange={(e) => setGitUsername(e.target.value)}
                placeholder="github-username"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Personal Access Token:
              <input
                type="password"
                value={gitToken}
                onChange={(e) => setGitToken(e.target.value)}
                placeholder="PAT (stored in UI only)"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Author Name:
              <input
                type="text"
                value={gitAuthorName}
                onChange={(e) => setGitAuthorName(e.target.value)}
                placeholder="Automation Bot"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Author Email:
              <input
                type="email"
                value={gitAuthorEmail}
                onChange={(e) => setGitAuthorEmail(e.target.value)}
                placeholder="automation@example.com"
                className={styles.formInput}
              />
            </label>

            <label className={styles.formLabel}>
              Commit Message:
              <textarea
                rows="3"
                value={gitCommitMessage}
                onChange={(e) => setGitCommitMessage(e.target.value)}
                placeholder="Sync generated tests"
                className={styles.formInput}
              ></textarea>
            </label>

            <div className={styles.dialogActions}>
              <button
                onClick={handleGitDialogClose}
                className={styles.cancelButton}
                disabled={isPushingToGit}
              >
                Cancel
              </button>
              <button
                onClick={handleGitDialogSubmit}
                className={styles.startButton}
                disabled={isPushingToGit}
              >
                {isPushingToGit ? "Pushing..." : "Push to Git"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Home;
