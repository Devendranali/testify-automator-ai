
import React, { useState } from "react";
import API_BASE_URL from "../config";
import useAppStore from "../state/useAppStore";
import { createReportWindow, openAuthenticatedReport } from "../utils/reportViewer";
import { requireBearerAuthHeaders } from "../utils/auth";

const API_BASE = API_BASE_URL;

export default function TestRunner() {
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [error, setError] = useState(null);
  const activeProjectId = useAppStore((state) => state.project.activeProjectId);

  const runTests = async () => {
    let reportWindow;
    setLoading(true);
    setError(null);
    try {
      reportWindow = createReportWindow();
      if (!activeProjectId) {
        throw new Error("No active project. Please activate a project first.");
      }
      const res = await fetch(
        `${API_BASE}/tests/run?project_id=${encodeURIComponent(activeProjectId)}`,
        {
          method: "GET",
          headers: requireBearerAuthHeaders(),
        }
      );
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      if (!data.report_url) throw new Error("No report_url returned");
      await openAuthenticatedReport(API_BASE, activeProjectId, reportWindow);
    } catch (e) {
      if (reportWindow && !reportWindow.closed) {
        reportWindow.close();
      }
      setError(e.message || "Failed to run tests");
    } finally {
      setLoading(false);
    }
  };

  const viewReport = async () => {
    let reportWindow;
    setReportLoading(true);
    setError(null);
    try {
      reportWindow = createReportWindow();
      // request report specifically for test_1.py
      if (!activeProjectId) {
        throw new Error("No active project. Please activate a project first.");
      }
      const res = await fetch(
        `${API_BASE}/tests/report?test=tests/test_1.py&project_id=${encodeURIComponent(activeProjectId)}`,
        {
          method: "GET",
          headers: requireBearerAuthHeaders(),
        }
      );
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      const data = await res.json();
      if (!data.report_url) throw new Error("No report_url returned");
      await openAuthenticatedReport(API_BASE, activeProjectId, reportWindow);
    } catch (e) {
      if (reportWindow && !reportWindow.closed) {
        reportWindow.close();
      }
      setError(e.message || "Failed to fetch report");
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div style={{ padding: "1rem" }}>
      <h2>Test Runner</h2>
      <button onClick={viewReport} disabled={reportLoading} style={{ marginRight: "0.5rem" }}>
        {reportLoading ? "Preparing report…" : "Report"}
      </button>
      <button onClick={runTests} disabled={loading}>
        {loading ? "Running tests…" : "Run Tests & View Report"}
      </button>
      {error && <div style={{ color: "red", marginTop: "0.5rem" }}>{error}</div>}
    </div>
  );
}
