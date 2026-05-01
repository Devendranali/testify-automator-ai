import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import API_BASE_URL from "../config";
import styles from "../css/URLInput.module.css";
import useAppStore from "../state/useAppStore";
import useScopedToast from "../hooks/useScopedToast";

const URLInput = ({ onBack, onNext, apiMode = "ocr", projectName,
  projectId, }) => {
  const notify = useScopedToast();
  const url = useAppStore((state) => state.enrichment.url);
  const setUrl = useAppStore((state) => state.setEnrichmentUrl);
  const fullTestData = useAppStore((state) => state.enrichment.fullTestData);
  const setFullTestData = useAppStore((state) => state.setEnrichmentResult);
  const clearFullTestData = useAppStore((state) => state.clearEnrichmentResult);
  const [loadingEnrich, setLoadingEnrich] = useState(false);
  const [loadingManualEnrich, setLoadingManualEnrich] = useState(false);
  const [error, setError] = useState("");
  const hasLoadedPersistedRef = React.useRef(false);
  const activeProjectId = useAppStore((state) => state.project.activeProjectId);
  const activeProjectName = useAppStore((state) => state.project.activeProjectName);
  const setActiveProject = useAppStore((state) => state.setActiveProject);
  const resolvedProjectId = projectId || activeProjectId;
  const resolvedProjectName = projectName || activeProjectName;
  const hasProject = Boolean(resolvedProjectId || resolvedProjectName);
  const normalizedUrl = (url || "").trim();
  const canProceed =
    !loadingEnrich &&
    !loadingManualEnrich &&
    Boolean(fullTestData) &&
    Boolean(fullTestData?.auto_enrich_result || fullTestData?.auto_enrich_job || fullTestData?.status);

  const buildApiUrl = useCallback((path) => {
    if (!path) return null;
    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }
    const sep = path.startsWith("/") ? "" : "/";
    return `${API_BASE_URL}${sep}${path}`;
  }, []);

  const pollEnrichmentJob = useCallback(
    async (jobInfo, token) => {
      const jobUrl = buildApiUrl(jobInfo?.job_endpoint);
      const resultUrl = buildApiUrl(jobInfo?.result_endpoint);
      if (!jobUrl) {
        throw new Error("Missing enrichment job endpoint.");
      }
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const delayMs = 2000;
      while (true) {
        const statusResp = await axios.get(jobUrl, { headers });
        const status = statusResp?.data?.status;
        if (status === "completed") {
          if (!resultUrl) {
            return statusResp?.data?.result ?? statusResp?.data;
          }
          const resultResp = await axios.get(resultUrl, { headers });
          return resultResp?.data?.result ?? resultResp?.data;
        }
        if (status === "failed") {
          const errMsg = statusResp?.data?.error || "Enrichment job failed.";
          throw new Error(errMsg);
        }
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    },
    [buildApiUrl]
  );

  const pollManualCaptureResult = useCallback(
    async (projectId, token) => {
      const resultUrl = buildApiUrl(`/manual/latest-result?project_id=${projectId}`);
      if (!resultUrl) {
        throw new Error("Missing manual capture result endpoint.");
      }
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const maxAttempts = 600;
      const delayMs = 2000;
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        const resultResp = await axios.get(resultUrl, { headers });
        const status = resultResp?.data?.status;
        if (status === "success") {
          return resultResp?.data ?? null;
        }
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
      throw new Error("Manual capture result not available yet.");
    },
    [buildApiUrl]
  );

  const pollManualCaptureClosed = useCallback(
    async (projectId, token, isUrlMode) => {
      const statusPath = isUrlMode
        ? `/manual/browser-status?project_id=${projectId}`
        : `/manual-enrichment/browser-status?project_id=${projectId}`;
      const statusUrl = buildApiUrl(statusPath);
      if (!statusUrl) {
        throw new Error("Missing manual capture status endpoint.");
      }
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const maxAttempts = 600;
      const delayMs = 2000;
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        const statusResp = await axios.get(statusUrl, { headers });
        if (statusResp?.data?.closed) {
          return true;
        }
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
      throw new Error("Manual capture browser was not closed yet.");
    },
    [buildApiUrl]
  );

  const pollManualEnrichmentResult = useCallback(
    async (projectId, token) => {
      const resultUrl = buildApiUrl(`/manual/latest-result?project_id=${projectId}`);
      if (!resultUrl) {
        throw new Error("Missing manual enrichment result endpoint.");
      }
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const maxAttempts = 600;
      const delayMs = 2000;
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        const resultResp = await axios.get(resultUrl, { headers });
        const status = resultResp?.data?.status;
        if (status === "success") {
          return resultResp?.data ?? null;
        }
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
      throw new Error("Manual enrichment result not available yet.");
    },
    [buildApiUrl]
  );

  const validateUrl = useCallback(() => {
    if (!normalizedUrl) {
      setError("Please enter a valid URL");
      return false;
    }

    try {
      new URL(normalizedUrl);
    } catch (_) {
      setError("Please enter a valid URL format (e.g., https://example.com)");
      return false;
    }

    return true;
  }, [normalizedUrl]);

  const ensureActiveProject = useCallback(async () => {
    if (activeProjectId) {
      return activeProjectId;
    }
    const token = localStorage.getItem("token");
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
  }, [activeProjectId, projectName, activeProjectName, setActiveProject]);

  const buildEnrichmentSummaryFromMetadata = useCallback((metadata, filePath) => {
    if (!Array.isArray(metadata) || metadata.length === 0) {
      return null;
    }
    const counts = {};
    metadata.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const pageName = String(entry.page_name || entry.page || "page").trim() || "page";
      counts[pageName] = (counts[pageName] || 0) + 1;
    });
    const results = Object.keys(counts)
      .sort()
      .map((name) => ({
        page_name: name,
        count: counts[name],
        file: filePath || null,
      }));
    if (results.length === 0) {
      return null;
    }
    return {
      status: "success",
      message: "Loaded saved enrichment data.",
      auto_enrich_result: {
        strategy: "stored",
        results,
        file: filePath || null,
      },
      auto_enrich_job: null,
    };
  }, []);

  const loadPersistedEnrichment = useCallback(async () => {
    if (hasLoadedPersistedRef.current) {
      return;
    }
    if (fullTestData) {
      return;
    }
    const token = localStorage.getItem("token");
    if (!token) {
      return;
    }
    const activeId = resolvedProjectId || activeProjectId || (await ensureActiveProject());
    if (!activeId) {
      return;
    }
    hasLoadedPersistedRef.current = true;
    const targetPath = "metadata/after_enrichment.json";
    try {
      const response = await fetch(
        `${API_BASE_URL}/projects/${activeId}/files/content?path=${encodeURIComponent(targetPath)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      let content = payload?.content;
      if (!content) {
        return;
      }
      if (String(payload?.encoding || "").toLowerCase() === "base64") {
        try {
          content = atob(content);
        } catch (_) {
          return;
        }
      }
      const parsed = JSON.parse(content);
      const summary = buildEnrichmentSummaryFromMetadata(parsed, targetPath);
      if (summary) {
        setFullTestData(summary);
      }
    } catch (err) {
      console.error("Failed to load saved enrichment data:", err);
    }
  }, [
    activeProjectId,
    buildEnrichmentSummaryFromMetadata,
    ensureActiveProject,
    fullTestData,
    resolvedProjectId,
    setFullTestData,
  ]);

  useEffect(() => {
    if (projectId || projectName) {
      setActiveProject({
        id: projectId ? String(projectId) : null,
        name: projectName || null,
      });
    }
  }, [projectId, projectName, setActiveProject]);

  useEffect(() => {
    loadPersistedEnrichment();
  }, [loadPersistedEnrichment]);

  const enrichLocaters = async () => {
    if (!validateUrl()) {
      return;
    }

    setLoadingEnrich(true);
    setError("");
    clearFullTestData();

    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
      const endpoint = apiMode === "url" ? "/url/launch-browser" : "/launch-browser";
      const launchQuery = "?async_launch=true";
      const response = await axios.post(`${API_BASE_URL}${"/"}${activeId}${endpoint}${launchQuery}`, 
        { url: normalizedUrl, job_timeout_s: 0 } ,{ 
          headers: {
            Authorization: `Bearer ${token}`,
          }
        }
      );
    const data = response.data;
    if (data?.auto_enrich_job?.job_id) {
      notify.success("Enrichment started. Waiting for results...");
      const resultPayload = await pollEnrichmentJob(data.auto_enrich_job, token);
      setFullTestData(resultPayload);
      notify.success("Locators enriched successfully");
    } else {
      setFullTestData(data);
      notify.success("Locators enriched successfully");
    }
  } catch (err) {
    const raw = err.response?.data?.detail || err.response?.data?.message || err.message;
    const message = Array.isArray(raw)
      ? raw.map((item) => item?.msg || item?.message || JSON.stringify(item)).join("; ")
      : typeof raw === "string"
        ? raw
        : JSON.stringify(raw);
    setError(message || "Error enriching locators");
  } finally {
    setLoadingEnrich(false);
  }
  };


  const openManualCapture = useCallback(async () => {
  if (!validateUrl()) {
    return;
  }
  if (!hasProject) {
    notify.error("No active project. Please start a project first.");
    return;
  }
  const token = localStorage.getItem("token");
  if (!token) {
    notify.error("Missing user session. Please login again.");
    return;
  }

  setLoadingManualEnrich(true);
  setError("");
  clearFullTestData();

  try {
    const activeId = await ensureActiveProject();
    if (!activeId && !resolvedProjectName) {
      throw new Error("No active project. Please start a project first.");
    }

    const numericProjectId = Number(activeId || resolvedProjectId);
    const safeProjectId = Number.isFinite(numericProjectId) ? numericProjectId : null;

    const isUrlMode = apiMode === "url";
    const endpoint = isUrlMode
      ? `${API_BASE_URL}/${activeId}/manual/launch-browser`
      : `${API_BASE_URL}/manual-enrichment/launch-browser`;
    const payload = isUrlMode
      ? { url: normalizedUrl }
      : {
          url: normalizedUrl,
          project_name: resolvedProjectName || projectName || activeProjectName || "",
          project_id: safeProjectId,
        };

    await axios.post(endpoint, payload, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (isUrlMode) {
      notify.success("Manual enrichment browser launched. Close the browser once enrichment is done.");
      pollManualCaptureClosed(activeId, token, true)
        .then(() => pollManualEnrichmentResult(activeId, token))
        .then((resultPayload) => {
          if (resultPayload) {
            let results = Array.isArray(resultPayload.results)
              ? resultPayload.results.filter((item) => item && item.page_name)
              : [];
            if (results.length === 0) {
              const pageName = resultPayload.page_name || "page";
              const count = typeof resultPayload.count === "number" ? resultPayload.count : 0;
              const filePath = resultPayload.file || null;
              results = [
                {
                  page_name: pageName,
                  count,
                  file: filePath,
                },
              ];
            }
            setFullTestData({
              status: "success",
              message: "Manual enrichment completed.",
              auto_enrich_result: {
                strategy: "manual",
                results,
              },
              auto_enrich_job: null,
            });
            notify.success("Manual enrichment results received.");
          }
        })
        .catch((err) => {
          console.error("Manual enrichment polling error:", err);
          notify.error(err?.message || "Manual enrichment polling error.");
        });
      return;
    }

    notify.success("Manual capture browser launched. Close the browser once capture is done.");
      pollManualCaptureClosed(activeId, token, false)
      .then(() => pollManualCaptureResult(activeId, token))
      .then((resultPayload) => {
        if (resultPayload) {
          let results = Array.isArray(resultPayload.results)
            ? resultPayload.results.filter((item) => item && item.page_name)
            : [];
          if (results.length === 0) {
            const pageName = resultPayload.page_name || "page";
            const count = typeof resultPayload.count === "number" ? resultPayload.count : 0;
            const filePath = resultPayload.file || null;
            results = [
              {
                page_name: pageName,
                count,
                file: filePath,
              },
            ];
          }
          setFullTestData({
            status: "success",
            message: "Manual capture completed.",
            auto_enrich_result: {
              strategy: "manual",
              results,
            },
            auto_enrich_job: null,
          });
          notify.success("Manual capture results received.");
        }
      })
      .catch((err) => {
        console.error("Manual capture polling error:", err);
        notify.error(err?.message || "Manual capture polling error.");
      });
  } catch (err) {
    const raw =
      err.response?.data?.detail || err.response?.data?.message || "Error starting manual capture";
    const message = Array.isArray(raw)
      ? raw.map((item) => item?.msg || item?.message || JSON.stringify(item)).join("; ")
      : typeof raw === "string"
        ? raw
        : JSON.stringify(raw);
    notify.error(message || "Error starting manual capture");
  } finally {
    setLoadingManualEnrich(false);
  }
}, [
  activeProjectName,
  clearFullTestData,
  ensureActiveProject,
  hasProject,
  pollManualCaptureResult,
  projectName,
  resolvedProjectId,
  resolvedProjectName,
  normalizedUrl,
  setFullTestData,
  validateUrl,
]);

return (
  <div className={styles.urlInputContainer}>
    <div className={styles.contentBox}>
      <h3 className={styles.title}>Enter URL</h3>
      <input
        type="text"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="Paste your app URL here..."
        className={styles.urlInput}
      />
      {error && <p className={styles.errorText}>{error}</p>}

      <div className={styles.enrichButtonContainer}>
        <button
          onClick={enrichLocaters}
          className={styles.enrichButton}
        >
          {loadingEnrich ? "Enriching..." : "Enrich Locators"}
        </button>
       {/* {apiMode === "url" && ( ~ manual enrichment made available */}
          <button
            onClick={openManualCapture}
            className={styles.refreshButton}
            disabled={!hasProject || loadingManualEnrich}
          >
            {loadingManualEnrich
              ? "Launching..."
              : apiMode === "url"
                ? "Manual Enrichment"
                : "Manual Capture"}
          </button>
       {/* )} */}
      </div>

      {fullTestData && (
        <div className={styles.testCaseOutput}>
          <h3 className={styles.testCaseOutputTitle}>
            Test Case JSON Output :
          </h3>
          <pre className={styles.jsonPre}>
            {JSON.stringify(fullTestData, null, 2)}
          </pre>
        </div>
      )}

    </div>

    <div className={styles.navigationButtons}>
      <button
        onClick={onBack}
        className={styles.navButton}
      >
        <i className="fa-solid fa-angle-left"></i>
        Previous
      </button>

      <button
        onClick={onNext}
        disabled={!canProceed}
        className={`${styles.navButton} ${styles.next}`}
      >
        Next <i className="fa-solid fa-angle-right"></i>
      </button>
    </div>
  </div>
);
};

export default URLInput;
