import React, { useMemo, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import API_BASE_URL from "../config";
import styles from "../css/Execute.module.css";
import useAppStore from "../state/useAppStore";
import useScopedToast from "../hooks/useScopedToast";
import { getStoredToken, requireBearerAuthHeaders } from "../utils/auth";
import { fetchProtectedAssetBlobUrl } from "../utils/protectedAssets";
import { createReportWindow, openAuthenticatedReport } from "../utils/reportViewer";


const extractExecutionOrderParts = (value) => {
  const raw = String(value || "").trim();
  const tsMatch = raw.match(/\bTS_(\d+)\b/i);
  const tcMatch = raw.match(/\bTC_(\d+)\b/i);
  return {
    raw,
    ts: tsMatch ? Number(tsMatch[1]) : Number.POSITIVE_INFINITY,
    tc: tcMatch ? Number(tcMatch[1]) : Number.POSITIVE_INFINITY,
  };
};

const compareExecutionNames = (left, right) => {
  const a = extractExecutionOrderParts(left);
  const b = extractExecutionOrderParts(right);
  if (a.ts !== b.ts) {
    return a.ts - b.ts;
  }
  if (a.tc !== b.tc) {
    return a.tc - b.tc;
  }
  return a.raw.localeCompare(b.raw, undefined, { numeric: true, sensitivity: "base" });
};

const dedupeExecutionNames = (items = []) =>
  Array.from(new Set((Array.isArray(items) ? items : []).filter(Boolean)));


const QualitySparkline = ({ data = [] }) => {
  const points = useMemo(() => {
    if (!data.length) return "";
    const values = data.map((item) => item.pass_rate ?? 0);
    const chartValues = values.length === 1 ? [values[0], values[0]] : values;
    const max = Math.max(...chartValues);
    const min = Math.min(...chartValues);
    const span = max - min || 1;
    return chartValues
      .map((value, index) => {
        const x = (index / (chartValues.length - 1 || 1)) * 100;
        const y = 100 - ((value - min) / span) * 100;
        return `${x},${y}`;
      })
      .join(" ");
  }, [data]);

  if (!points) {
    return <div className={styles.metricsSparklinePlaceholder}>No data</div>;
  }

  return (
    <svg viewBox="0 0 100 100" className={styles.metricsSparkline}>
      <polyline
        points={points}
        fill="none"
        stroke="var(--color-primary)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

const Execute = ({ onBack, fullTestData, projectName,
  projectId, }) => {
  const navigate = useNavigate();
  const notify = useScopedToast();
  const activeProjectId = useAppStore((state) => state.project.activeProjectId);
  const activeProjectName = useAppStore((state) => state.project.activeProjectName);
  const setActiveProject = useAppStore((state) => state.setActiveProject);
  const executionFilters = useAppStore((state) => state.execution.executionFilters);
  const setExecutionFilters = useAppStore((state) => state.setExecutionFilters);
  const categorySelections = useAppStore((state) => state.execution.categorySelections);
  const setCategorySelections = useAppStore((state) => state.setCategorySelections);
  const useUpdatedExecutionByCategory = useAppStore(
    (state) => state.execution.useUpdatedExecutionByCategory
  );
  const setUseUpdatedExecutionByCategory = useAppStore(
    (state) => state.setUseUpdatedExecutionByCategory
  );
  const tagCounts = useAppStore((state) => state.execution.tagCounts);
  const setTagCounts = useAppStore((state) => state.setTagCounts);
  const plannedTests = useAppStore((state) => state.execution.plannedTests);
  const setPlannedTests = useAppStore((state) => state.setPlannedTests);
  const plannedTestsProjectId = useAppStore((state) => state.execution.plannedTestsProjectId);
  const plannedTestsProjectName = useAppStore((state) => state.execution.plannedTestsProjectName);
  const setPlannedTestsMeta = useAppStore((state) => state.setPlannedTestsMeta);
  const metrics = useAppStore((state) => state.execution.metrics);
  const setMetrics = useAppStore((state) => state.setMetrics);
  const acResults = useAppStore((state) => state.execution.acResults);
  const setAcResults = useAppStore((state) => state.setAcResults);
  const parallelExecution = useAppStore((state) => state.execution.parallelExecution);
  const setParallelExecution = useAppStore((state) => state.setParallelExecution);
  const setExecutionStatus = useAppStore((state) => state.setExecutionStatus);
  const [loadingExecution, setLoadingExecution] = useState(false);
  const [runningTestName, setRunningTestName] = useState("");
  const [executionSuccess, setExecutionSuccess] = useState(false);
  const [executionError, setExecutionError] = useState(false);
  const [executionMessage, setExecutionMessage] = useState("");
  const [testStatuses, setTestStatuses] = useState({});
  const [error, setError] = useState("");

  const [reportLoading, setReportLoading] = useState(false);
  const [visualizerImages, setVisualizerImages] = useState([]);
  const [visualizerLoading, setVisualizerLoading] = useState(false);
  const [visualizerError, setVisualizerError] = useState("");
  const [showVisualizer, setShowVisualizer] = useState(false);
  const [visualizerMode, setVisualizerMode] = useState("idle"); // idle | interactive | images
  const [visualizerDashboardUrl, setVisualizerDashboardUrl] = useState("");
  const visualizerObjectUrlsRef = useRef([]);

  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState("");
  const [selectedPlannedTests, setSelectedPlannedTests] = useState([]);

  const [filtersExpanded, setFiltersExpanded] = useState({
    ui: true,
    accessibility: false,
    security: false,
  });
  const [testPageIndex, setTestPageIndex] = useState(1);
  const testsPerPage = 8;

  const hasSelectedTags = useMemo(() => {
    const uiSelected = Object.values(executionFilters.ui).some(Boolean);
    return uiSelected || categorySelections.accessibility || categorySelections.security;
  }, [executionFilters, categorySelections]);

  const hasUpdatedSelection = useMemo(
    () => Object.values(useUpdatedExecutionByCategory).some(Boolean),
    [useUpdatedExecutionByCategory]
  );

  useEffect(() => {
    if (projectId || projectName) {
      setActiveProject({
        id: projectId ? String(projectId) : null,
        name: projectName || null,
      });
    }
  }, [projectId, projectName, setActiveProject]);

  const ensureActiveProject = useCallback(async () => {
    if (activeProjectId) {
      return activeProjectId;
    }
    const token = getStoredToken();
    const name = projectName || activeProjectName;
    if (!token || !name) {
      return null;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/projects/activate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ project_name: name }),
      });
      if (!response.ok) {
        const txt = await response.text().catch(() => null);
        throw new Error(txt || `Failed to activate project (${response.status})`);
      }
      const payload = await response.json();
      const newId = payload?.project?.id ? String(payload.project.id) : null;
      if (newId) {
        setActiveProject({ id: newId, name });
      }
      return newId;
    } catch (err) {
      console.error("Failed to activate project before upload:", err);
      notify.error(err.message || "Failed to activate project.");
      return null;
    }
  }, [activeProjectId, projectName, setActiveProject]);

  const formatServerError = (err, fallbackMessage) => {
    const detail =
      err?.response?.data?.detail ??
      err?.response?.data?.message ??
      err?.response?.data ??
      err?.message;
    if (typeof detail === "object") {
      try {
        return JSON.stringify(detail);
      } catch {
        return fallbackMessage;
      }
    }
    return detail || fallbackMessage;
  };

  useEffect(() => {
    if (!hasSelectedTags && !hasUpdatedSelection) {
      setPlannedTests([]);
      setPlannedTestsMeta({ projectId: null, projectName: "" });
      setTagCounts({});
      setTestPageIndex(1);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const selectedTags = {
          ui: Object.keys(executionFilters.ui).filter((tag) => executionFilters.ui[tag]),
          accessibility: categorySelections.accessibility ? ["__all__"] : [],
          security: categorySelections.security ? ["__all__"] : [],
        };
        const activeId = await ensureActiveProject();
        if (!activeId) {
          throw new Error("No active project. Please start a project first.");
        }
        const token = getStoredToken();
        const res = await axios.post(`${API_BASE_URL}/${activeId}/rag/preview-tests`, {
          tags: selectedTags,
          use_test_plan: hasUpdatedSelection ? useUpdatedExecutionByCategory : false,
        } , {
        headers: {
          Authorization: `Bearer ${token}`,
        }});
        const data = res.data || {};
        if (Array.isArray(data.planned_tests)) {
          setPlannedTests(data.planned_tests);
          setTestPageIndex(1);
        }
        if (data.project_id || data.project_name) {
          setPlannedTestsMeta({
            projectId: data.project_id ?? null,
            projectName: data.project_name ?? "",
          });
        }
        if (data.tag_counts) {
          setTagCounts(data.tag_counts);
        } else {
          setTagCounts({});
        }
      } catch (err) {
        setError(formatServerError(err, "Failed to preview planned tests."));
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [executionFilters, categorySelections, useUpdatedExecutionByCategory, hasSelectedTags, hasUpdatedSelection]);

  const executeStoryTest = async (testsToRun = null, forcedCategory = null) => {
    const requestedTests = Array.isArray(testsToRun) && testsToRun.length
      ? dedupeExecutionNames(testsToRun).sort(compareExecutionNames)
      : [];
    const hasSingleTest = requestedTests.length > 0;
    const selectedSubset = !hasSingleTest ? selectedPlannedRunNames : [];
    const plannedRunNames =
      !hasSingleTest && !selectedSubset.length && flatPlannedTests.length
        ? allPlannedRunNames
        : [];
    setLoadingExecution(true);
    setError("");
    setPlannedTests([]);
    setPlannedTestsMeta({ projectId: null, projectName: "" });
    setTestPageIndex(1);
    setExecutionSuccess(false);
    setExecutionError(false);
    setExecutionMessage("");
    setTestStatuses({});
    setAcResults(null);
    if (hasSingleTest && requestedTests.length === 1) {
      setRunningTestName(requestedTests[0]);
    }

    try {
      // Calls the correct RAG runner endpoint using POST
      const baseTags = {
        ui: Object.keys(executionFilters.ui).filter((tag) => executionFilters.ui[tag]),
        accessibility: categorySelections.accessibility ? ["__all__"] : [],
        security: categorySelections.security ? ["__all__"] : [],
      };
      const selectedTags = forcedCategory
        ? {
          ui: [],
          accessibility: [],
          security: [],
          [forcedCategory]: ["__all__"],
        }
        : baseTags;
      const useUpdated = hasSingleTest || selectedSubset.length || plannedRunNames.length
        ? false
        : Object.values(useUpdatedExecutionByCategory).some(Boolean);
      const payload = {
        tags: selectedTags,
        use_test_plan: useUpdated ? useUpdatedExecutionByCategory : false,
        parallel_execution: parallelExecution,
      };
      if (hasSingleTest) {
        payload.tests_to_run = requestedTests;
      } else if (selectedSubset.length) {
        payload.tests_to_run = selectedSubset;
      } else if (plannedRunNames.length) {
        payload.tests_to_run = plannedRunNames;
      }
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = getStoredToken();
      const res = await axios.post(`${API_BASE_URL}/${activeId}/rag/run-generated-story-test`, payload, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = res.data;

      if (!data) {
        throw new Error("No response data returned from server");
      }

      if (Array.isArray(data.planned_tests)) {
        setPlannedTests(data.planned_tests);
        setTestPageIndex(1);
      }
      if (Array.isArray(data.planned_tests_to_run) && data.planned_tests_to_run.length) {
        notify.info(`Planned tests to run: ${data.planned_tests_to_run.join(", ")}`);
      }
      if (data.project_id || data.project_name) {
        setPlannedTestsMeta({
          projectId: data.project_id ?? null,
          projectName: data.project_name ?? "",
        });
      }
      if (data.ac) {
        setAcResults(data.ac);
      }

      const friendlyMessage =
        data?.message ||
        (data?.status === "PASS"
          ? hasSingleTest
            ? "Test executed successfully"
            : selectedSubset.length
              ? "Selected tests executed successfully"
            : "Generated tests executed successfully"
          : `Execution completed with status: ${data?.status || "UNKNOWN"}`);
      const executionResults = Array.isArray(data.results) ? data.results : [];
      const derivedStatuses = {};
      executionResults.forEach((result) => {
        const statusValue = result?.status ?? data?.status ?? "UNKNOWN";
        const normalizedStatus =
          typeof statusValue === "string" ? statusValue.toUpperCase() : statusValue;
        const resultTests = Array.isArray(result?.planned_tests)
          ? result.planned_tests
          : [];
        resultTests.forEach((testName) => {
          if (testName) {
            derivedStatuses[testName] = normalizedStatus;
          }
        });
      });
      if (!Object.keys(derivedStatuses).length) {
        const fallbackStatus =
          typeof data?.status === "string" ? data.status.toUpperCase() : "UNKNOWN";
        (data?.planned_tests || []).forEach((plan) => {
          (plan.tests || []).forEach((testName) => {
            if (testName) {
              derivedStatuses[testName] = fallbackStatus;
            }
          });
        });
      }
      setTestStatuses(derivedStatuses);
      setExecutionMessage(friendlyMessage);
      if (data.status === "PASS") {
        setExecutionSuccess(true);
        setExecutionError(false);
        setExecutionStatus({ status: "PASS", error: "" });
        notify.success(friendlyMessage);
      } else {
        setExecutionSuccess(false);
        setExecutionError(true);
        setExecutionStatus({ status: data.status || "FAIL", error: "" });
        notify.error(friendlyMessage);
      }

      // After execution, refresh the metrics dashboard
      fetchMetrics().catch(() => {});

      } catch (err) {
        const formattedError = formatServerError(err, "Error executing the test script.");
        setError(formattedError);
        setExecutionError(true);
        setExecutionMessage(formattedError);
        setExecutionStatus({ status: "ERROR", error: formattedError });
        notify.error(formattedError);
      } finally {
      setLoadingExecution(false);
      setRunningTestName("");
    }
  };

  const viewReport = async () => {
    let reportWindow;
    try {
      reportWindow = createReportWindow();
    } catch (err) {
      setError(formatServerError(err, "Failed to open report"));
      return;
    }
    setReportLoading(true);
    setError("");
    setPlannedTests([]);
    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      await openAuthenticatedReport(API_BASE_URL, activeId, reportWindow);
    } catch (err) {
      if (reportWindow && !reportWindow.closed) {
        reportWindow.close();
      }
      setError(formatServerError(err, "Failed to open report"));
    } finally {
      setReportLoading(false);
    }
  };

  const formatVisualizerAssetUrl = useCallback((url) => {
    if (!url) return "";
    if (/^https?:\/\//i.test(url)) {
      return url;
    }
    const base = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const path = url.startsWith("/") ? url : `/${url}`;
    return `${base}${path}`;
  }, []);

  const revokeVisualizerObjectUrls = useCallback(() => {
    visualizerObjectUrlsRef.current.forEach((url) => {
      try {
        URL.revokeObjectURL(url);
      } catch (err) {
        console.warn("Failed to revoke visualizer asset URL", err);
      }
    });
    visualizerObjectUrlsRef.current = [];
  }, []);

  const loadProtectedVisualizerAsset = useCallback(async (assetUrl) => {
    const blobUrl = await fetchProtectedAssetBlobUrl(formatVisualizerAssetUrl(assetUrl));
    visualizerObjectUrlsRef.current.push(blobUrl);
    return blobUrl;
  }, [formatVisualizerAssetUrl]);

  useEffect(() => () => {
    revokeVisualizerObjectUrls();
  }, [revokeVisualizerObjectUrls]);

  const loadVisualizerContent = async () => {
    if (visualizerLoading) {
      return;
    }
    setVisualizerLoading(true);
    setVisualizerError("");
    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const authHeaders = requireBearerAuthHeaders();
      const res = await axios.get(`${API_BASE_URL}/visualizer/images`, {
        params: { project_id: activeId },
        headers: authHeaders,
      });
      const images = Array.isArray(res.data?.images) ? res.data.images : [];
      const dashboardPath = res.data?.interactive_dashboard;
      revokeVisualizerObjectUrls();

      if (dashboardPath) {
        const dashboardBlobUrl = await loadProtectedVisualizerAsset(dashboardPath);
        setVisualizerDashboardUrl(dashboardBlobUrl);
        setVisualizerMode("interactive");
        setVisualizerImages([]);
      } else {
        const resolvedImages = await Promise.all(
          images.map(async (image) => ({
            ...image,
            renderUrl: await loadProtectedVisualizerAsset(image.url),
          }))
        );
        setVisualizerDashboardUrl("");
        setVisualizerImages(resolvedImages);
        setVisualizerMode("images");
      }

      setShowVisualizer(true);
    } catch (err) {
      setVisualizerError(formatServerError(err, "Failed to load visualizations."));
    } finally {
      setVisualizerLoading(false);
    }
  };

  const closeVisualizer = () => {
    setShowVisualizer(false);
    setVisualizerError("");
  };

  const handleToggleVisualizer = async () => {
    if (visualizerLoading) {
      return;
    }
    if (showVisualizer) {
      closeVisualizer();
      return;
    }

    if (visualizerMode === "idle") {
      await loadVisualizerContent();
      return;
    }

    setShowVisualizer(true);
  };

  const handleRefreshVisualizer = async () => {
    if (visualizerLoading) {
      return;
    }
    await loadVisualizerContent();
  };

  const formatPercent = (value) => `${Math.round((value ?? 0) * 100)}%`;
  const formatCount = (value) => (value ?? 0);
  const summary = metrics?.self_healing_summary || {};
  const periods = metrics?.periods || {};
  const latestStatus = metrics?.latest_run?.status_counts || {};
  const selfHealing = metrics?.self_healing_reports || {};
  const healingStrategies = selfHealing.strategy_usage || [];
  const healingSteps = selfHealing.healing_steps_per_feature || [];
  const healingHistory = selfHealing.history || [];

  const fetchMetrics = async () => {
    setMetricsLoading(true);
    setMetricsError("");
    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = getStoredToken();
      const res = await axios.get(`${API_BASE_URL}/metrics/dashboard`, {
        params: { project_id: activeId },
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      setMetrics(res.data);
    } catch (err) {
      setMetricsError(formatServerError(err, "Unable to load quality metrics."));
    } finally {
      setMetricsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  const toggleExecutionTag = (category, tag) => {
    setExecutionFilters({
      ...executionFilters,
      [category]: {
        ...executionFilters[category],
        [tag]: !executionFilters[category][tag],
      },
    });
  };

  const toggleFilterSection = (category) => {
    setFiltersExpanded((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const toggleUpdatedExecution = (category) => {
    setUseUpdatedExecutionByCategory({
      ...useUpdatedExecutionByCategory,
      [category]: !useUpdatedExecutionByCategory[category],
    });
  };

  const handleOpenTestFile = (filePath) => {
    if (!plannedTestsProjectId || !filePath) {
      return;
    }
    const params = new URLSearchParams();
    params.set("projectId", String(plannedTestsProjectId));
    if (plannedTestsProjectName) {
      params.set("projectName", plannedTestsProjectName);
    }
    params.set("path", filePath);
    navigate(
      {
        pathname: "/editor",
        search: `?${params.toString()}`,
      },
      {
        state: {
          openFile: {
            projectId: plannedTestsProjectId,
            projectName: plannedTestsProjectName,
            path: filePath,
          },
        },
      }
    );
  };

  const flatPlannedTests = useMemo(() => {
    if (!plannedTests.length) {
      return [];
    }
    const flattened = [];
    plannedTests.forEach((plan) => {
      const tests = plan.tests || [];
      const category = plan.category || "ui";
      const scriptKey = plan.script || plan.script_path || plan.name || "";
      tests.forEach((testName) => {
        const filePath =
          plan.test_files?.find((item) => item.name === testName)?.path || plan.script_path;
        flattened.push({
          category,
          scriptKey,
          script_path: plan.script_path,
          test_files: plan.test_files,
          testName,
          filePath,
        });
      });
    });
    return flattened.sort((a, b) => {
      const nameCompare = compareExecutionNames(a.testName, b.testName);
      if (nameCompare !== 0) {
        return nameCompare;
      }
      const categoryCompare = String(a.category || "").localeCompare(String(b.category || ""), undefined, {
        numeric: true,
        sensitivity: "base",
      });
      if (categoryCompare !== 0) {
        return categoryCompare;
      }
      return String(a.scriptKey || "").localeCompare(String(b.scriptKey || ""), undefined, {
        numeric: true,
        sensitivity: "base",
      });
    });
  }, [plannedTests]);

  const allPlannedRunNames = useMemo(
    () => dedupeExecutionNames(flatPlannedTests.map((item) => item.testName)).sort(compareExecutionNames),
    [flatPlannedTests]
  );

  useEffect(() => {
    setSelectedPlannedTests((current) => {
      if (!current.length) {
        return current;
      }
      const available = new Set(allPlannedRunNames);
      const filtered = current.filter((name) => available.has(name));
      return filtered.length === current.length ? current : filtered;
    });
  }, [allPlannedRunNames]);

  const selectedPlannedRunNames = useMemo(
    () => selectedPlannedTests.filter((name) => allPlannedRunNames.includes(name)).sort(compareExecutionNames),
    [selectedPlannedTests, allPlannedRunNames]
  );

  const allPlannedSelected =
    allPlannedRunNames.length > 0 && selectedPlannedRunNames.length === allPlannedRunNames.length;

  const togglePlannedTestSelection = useCallback((testName) => {
    setSelectedPlannedTests((current) => {
      if (current.includes(testName)) {
        return current.filter((name) => name !== testName);
      }
      return [...current, testName].sort(compareExecutionNames);
    });
  }, []);

  const toggleSelectAllPlannedTests = useCallback(() => {
    setSelectedPlannedTests((current) =>
      current.length === allPlannedRunNames.length ? [] : allPlannedRunNames
    );
  }, [allPlannedRunNames]);

  const totalPlannedCount = flatPlannedTests.length;
  const totalPages = Math.max(1, Math.ceil(totalPlannedCount / testsPerPage));
  const pagedPlans = useMemo(() => {
    if (!flatPlannedTests.length) {
      return [];
    }
    const start = (testPageIndex - 1) * testsPerPage;
    const pageItems = flatPlannedTests.slice(start, start + testsPerPage);
    const grouped = new Map();
    pageItems.forEach((item) => {
      const key = `${item.category}:${item.scriptKey}`;
      if (!grouped.has(key)) {
        grouped.set(key, {
          category: item.category,
          script: item.scriptKey,
          script_path: item.script_path,
          test_files: item.test_files,
          tests: [],
        });
      }
      grouped.get(key).tests.push({ name: item.testName, path: item.filePath });
    });
    return Array.from(grouped.values());
  }, [flatPlannedTests, testPageIndex, testsPerPage]);

  return (
    <div className={styles.executeContainer}>
      <div className={styles.contentBox}>
        {/* Heading Section */}
        <h3 className={styles.heading}>
          <i className={`fa-solid fa-code ${styles.headingIcon}`}></i>
          Execute tests
        </h3>
        <p className={styles.subheading}>Configure framework and Execute tests</p>

        {/* Icon & Description */}
        <div className={styles.centerContent}>
          <div className={styles.mainIcon}>
            <i className="fa-solid fa-code"></i>
          </div>
          <h2 className={styles.mainTitle}>Execute tests</h2>
          <p className={styles.mainDescription}>
            Your test scripts will be generated based on the uploaded designs and user stories.
          </p>
        </div>


        {/* Action Buttons: Report + Execute + Visualize */}
        <div className={styles.executeButtonContainer}>
          <div className={styles.tagFilterBox}>
            <div className={styles.tagFilterTitle}>Execution filters</div>
            <div className={styles.tagDropdownList}>
              {[
                { id: "ui", label: "UI" },
                { id: "accessibility", label: "Accessibility" },
                { id: "security", label: "Security" },
              ].map((section) => (
                <div key={section.id} className={styles.tagDropdown}>
                  <button
                    type="button"
                    className={styles.tagDropdownToggle}
                    onClick={() => toggleFilterSection(section.id)}
                  >
                    <span>{section.label}</span>
                    <i
                      className={`fa-solid fa-chevron-${filtersExpanded[section.id] ? "up" : "down"}`}
                      aria-hidden="true"
                    />
                  </button>
                  {filtersExpanded[section.id] && (
                    <>
                      {section.id === "ui" ? (
                        <>
                          <div className={styles.tagFilterGrid}>
                            {["regression", "functional"].map((tag) => {
                              const count = tagCounts?.[section.id]?.[tag] ?? 0;
                              return (
                                <label key={`${section.id}-${tag}`} className={styles.tagFilterItem}>
                                  <input
                                    type="checkbox"
                                    className={styles.tagCheckbox}
                                    checked={executionFilters[section.id][tag]}
                                    onChange={() => toggleExecutionTag(section.id, tag)}
                                  />
                                  <span>
                                    {tag.charAt(0).toUpperCase() + tag.slice(1)}
                                    {executionFilters[section.id][tag] ? ` (${count})` : ""}
                                  </span>
                                </label>
                              );
                            })}
                          </div>
                        </>
                      ) : (
                        <label className={styles.executionPlanToggle}>
                          <input
                            type="checkbox"
                            checked={categorySelections[section.id]}
                            onChange={() =>
                              setCategorySelections({
                                ...categorySelections,
                                [section.id]: !categorySelections[section.id],
                              })
                            }
                          />
                          Include {section.label} tests
                          {categorySelections[section.id]
                            ? ` (${plannedTests
                              .filter((plan) => plan.category === section.id)
                              .reduce((total, plan) => total + (plan.tests?.length || 0), 0)})`
                            : ""}
                        </label>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
            <div className={styles.executionOptions}>
              <label className={styles.executionPlanToggle}>
                <input
                  type="checkbox"
                  checked={parallelExecution}
                  onChange={() => setParallelExecution(!parallelExecution)}
                />
                Enable parallel execution
              </label>
              <div className={styles.executionOptionHint}>
                Runs tests in parallel when possible. Disable for serial execution.
              </div>
            </div>
          </div>
          <div className={styles.actionButtons}>
            <button onClick={viewReport} disabled={reportLoading || (!executionSuccess && !executionError)} className={styles.reportButton}>
              {reportLoading ? "Opening report..." : "Report"}
            </button>

            <button onClick={executeStoryTest} disabled={loadingExecution || totalPlannedCount === 0} className={styles.executeButton}>
              {loadingExecution
                ? "Executing..."
                : selectedPlannedRunNames.length
                  ? `Execute Selected (${selectedPlannedRunNames.length})`
                  : "Execute All"}
            </button>

          </div>
          {(executionSuccess || executionError || executionMessage) && (
            <div className={styles.executionStatus}>
              <div className={styles.executionStatusRow}>
                <span className={styles.executionStatusLabel}>Test result:</span>
                <span
                  className={`${styles.executionStatusValue} ${
                    executionSuccess ? styles.statusPass : styles.statusFail
                  }`}
                >
                  {executionSuccess ? "PASS" : "FAIL"}
                </span>
              </div>
              {executionMessage && (
                <p className={styles.executionStatusMessage}>{executionMessage}</p>
              )}
            </div>
          )}
          {error && <div className={styles.errorLog}>{error}</div>}
          {acResults && (
            <div className={styles.acResultsCard}>
              <div className={styles.acResultsHeader}>
                <h4>Acceptance Criteria</h4>
                <span>{acResults.overall_status || "UNKNOWN"}</span>
              </div>
              {Array.isArray(acResults.details) && acResults.details.length ? (
                <ul className={styles.acResultsList}>
                  {acResults.details.map((item, idx) => (
                    <li key={`${idx}-${item.ac}`}>
                      <strong>{item.status}</strong> {item.ac}
                      {item.reason ? <span className={styles.acResultsReason}> — {item.reason}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.acResultsEmpty}>No acceptance criteria detected.</p>
              )}
            </div>
          )}
          {plannedTests.length > 0 && (
            <div className={styles.executionPlan}>
              <div className={styles.executionPlanHeader}>
                <h4>Planned test cases</h4>
                <div className={styles.executionPlanHeaderControls}>
                  <label className={styles.executionPlanSelectAll}>
                    <input
                      type="checkbox"
                      checked={allPlannedSelected}
                      onChange={toggleSelectAllPlannedTests}
                      disabled={!allPlannedRunNames.length}
                    />
                    <span>Select all</span>
                  </label>
                  <span>
                    {selectedPlannedRunNames.length
                      ? `${selectedPlannedRunNames.length} chosen of ${totalPlannedCount}`
                      : `${totalPlannedCount} available`}
                  </span>
                </div>
              </div>
              {pagedPlans.map((plan) => (
                <div key={`${plan.category}-${plan.script}`} className={styles.executionPlanBlock}>
                  <strong>{(plan.category || "ui").toUpperCase()}</strong>
                  {plan.tests && plan.tests.length ? (
                    <ul>
                      {plan.tests.map((testItem) => {
                        const testName = testItem?.name ?? testItem;
                        const filePath = testItem?.path;
                        const rawStatus = testName ? testStatuses[testName] : null;
                        const normalizedStatus = rawStatus
                          ? String(rawStatus).toUpperCase()
                          : "";
                        return (
                          <li key={`${plan.category}-${testName}`}>
                            <div className={styles.executionPlanItem}>
                              <div className={styles.executionPlanNameGroup}>
                                <label className={styles.executionPlanCheckbox}>
                                  <input
                                    type="checkbox"
                                    checked={selectedPlannedRunNames.includes(testName)}
                                    onChange={() => togglePlannedTestSelection(testName)}
                                  />
                                </label>
                                {filePath ? (
                                  <button
                                    type="button"
                                    className={styles.executionPlanLink}
                                    onClick={() => handleOpenTestFile(filePath)}
                                  >
                                    {testName}
                                  </button>
                                ) : (
                                  <span className={styles.executionPlanName}>{testName}</span>
                                )}
                                {normalizedStatus && (
                                  <span
                                    className={`${styles.testStatusBadge} ${
                                      normalizedStatus === "PASS"
                                        ? styles.statusPass
                                        : styles.statusFail
                                    }`}
                                  >
                                    {normalizedStatus}
                                  </span>
                                )}
                              </div>
                              <button
                                type="button"
                                className={styles.executionPlanRunButton}
                                onClick={() => executeStoryTest([testName], plan.category || "ui")}
                                disabled={loadingExecution || runningTestName === testName}
                              >
                                {runningTestName === testName ? "Executing..." : "Execute"}
                              </button>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p>No matching tests for the selected tags.</p>
                  )}
                </div>
              ))}
              {totalPages > 1 && (
                <div className={styles.executionPagination}>
                  <button
                    type="button"
                    className={styles.executionPageButton}
                    onClick={() => setTestPageIndex((prev) => Math.max(1, prev - 1))}
                    disabled={testPageIndex === 1}
                  >
                    Prev
                  </button>
                  <span className={styles.executionPageInfo}>
                    Page {testPageIndex} of {totalPages}
                  </span>
                  <button
                    type="button"
                    className={styles.executionPageButton}
                    onClick={() => setTestPageIndex((prev) => Math.min(totalPages, prev + 1))}
                    disabled={testPageIndex === totalPages}
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}

          {showVisualizer && (
            <div className={styles.visualizerPanel}>
              <div className={styles.visualizerPanelHeader}>
                <h4>Allure Visualizations</h4>
                <button type="button" onClick={closeVisualizer} className={styles.visualizerPanelClose}>
                  Close
                </button>
              </div>
              {visualizerLoading && (
                <p className={styles.visualizerStatus}>Fetching the latest visualizations…</p>
              )}
              {visualizerError && <p className={styles.visualizerError}>{visualizerError}</p>}
              {!visualizerLoading && !visualizerError && (
                <div className={styles.visualizerToolbar}>
                  <span>
                    {visualizerMode === "interactive"
                      ? "Interactive Plotly dashboard"
                      : visualizerImages.length
                        ? "Static chart snapshots"
                        : "No visualizations detected yet"}
                  </span>
                  <div className={styles.visualizerToolbarActions}>
                    <button type="button" onClick={handleRefreshVisualizer}>
                      Refresh
                    </button>
                    {visualizerMode === "interactive" && visualizerDashboardUrl && (
                      <a
                        href={visualizerDashboardUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open full screen
                      </a>
                    )}
                  </div>
                </div>
              )}
              {!visualizerLoading && !visualizerError && (
                visualizerMode === "interactive" && visualizerDashboardUrl ? (
                  <div className={styles.visualizerIframeWrapper}>
                    <iframe
                      key={visualizerDashboardUrl}
                      src={visualizerDashboardUrl}
                      title="Interactive Allure dashboard"
                      className={styles.visualizerIframe}
                      loading="lazy"
                    />
                  </div>
                ) : visualizerImages.length ? (
                  <div className={styles.visualizerGrid}>
                    {visualizerImages.map((image) => (
                      <div key={image.name} className={styles.visualizerCard}>
                        <img
                          src={image.renderUrl || formatVisualizerAssetUrl(image.url)}
                          alt={image.name}
                          className={styles.visualizerImage}
                        />
                        <span className={styles.visualizerCaption}>{image.name}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className={styles.visualizerStatus}>
                    No visualizations found yet. Run the Allure visualizer or execute tests to generate charts under
                    the backend's allure_reports folder.
                  </p>
                )
              )}
            </div>
          )}
        </div>
      </div>

      {/* Back Button */}
      <div className={styles.backButtonContainer}>
        <button onClick={onBack} className={styles.backButton}>
          <i className="fa-solid fa-angle-left"></i>
          Back
        </button>
      </div>
    </div>
  );
};

export default Execute;
