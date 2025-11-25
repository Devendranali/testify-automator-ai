import React, { useState } from "react";
import axios from "axios";
import API_BASE_URL from "../config";
import { toast } from "react-toastify";
import styles from "../css/Execute.module.css";

const Execute = ({ onBack, fullTestData }) => {
  const [loadingExecution, setLoadingExecution] = useState(false);
  const [executionSuccess, setExecutionSuccess] = useState(false);
  const [executionError, setExecutionError] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [error, setError] = useState("");

  const [reportLoading, setReportLoading] = useState(false);

  const executeStoryTest = async () => {
    setLoadingExecution(true);
    setError("");
    setExecutionResult(null);

    try {
      // Generate Allure report for test_1.py and open it
      const res = await axios.get(`${API_BASE_URL}/tests/report`, { params: { test: "tests/test_1.py" } });
      const data = res.data;
      if (!data) throw new Error("No response data returned from server");
      // Accept multiple possible keys from the backend for compatibility
      const uri = data.report_url || data.report_uri || data.file_uri || data.path;
      if (!uri) throw new Error("No report URL/URI returned");
      window.open(uri, "_blank", "noopener,noreferrer");
      setExecutionResult(data);
      toast.success("✅ Execution & report generated.");
      setExecutionSuccess(true);
    } catch (err) {
      setError(err.response?.data || err.message || "Error executing and generating report.");
      setExecutionError(true);
    } finally {
      setLoadingExecution(false);
    }
  };

  const viewReport = async () => {
    setReportLoading(true);
    setError("");
    try {
      // Ask backend for an existing report file URI inside generated_runs (will return file:// URI)
      const res = await axios.get(`${API_BASE_URL}/tests/open`, { params: { test: "tests/test_1.py" } });
      const data = res.data;
      if (!data) throw new Error("No response data returned from server");
      const uri = data.report_url || data.report_uri || data.file_uri || data.path;
      if (!uri) throw new Error("No report URL/URI returned from server");
      // Open whichever URI is provided (HTTP viewer or file://)
      window.open(uri, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err.response?.data || err.message || "Failed to open report");
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div className={styles.executeContainer}>
      <div className={styles.contentBox}>
        {/* Heading Section */}
        <h3 className={styles.heading}>
          <i className={`fa-solid fa-code ${styles.headingIcon}`}></i>
          Generate Scripts
        </h3>
        <p className={styles.subheading}>
          Configure framework and generate test scripts
        </p>

        {/* Icon & Description */}
        <div className={styles.centerContent}>
          <div className={styles.mainIcon}>
            <i className="fa-solid fa-code"></i>
          </div>
          <h2 className={styles.mainTitle}>Generate Test Scripts</h2>
          <p className={styles.mainDescription}>
            Your test scripts will be generated based on the uploaded designs and user stories.
          </p>
        </div>

        {/* Two-Column Responsive Layout */}
        <div className={styles.summaryCardsContainer}>
          {/* Project Summary Card */}
          <div className={styles.summaryCard}>
            <h3 className={styles.summaryCardTitle}>Project Summary</h3>

            <div className={styles.summaryItem}>
              <span>Design Files:</span>
              <strong className={styles.summaryItemValue}>0</strong>
            </div>

            <div className={styles.summaryItem}>
              <span>User Stories:</span>
              <strong className={styles.summaryItemValue}>0</strong>
            </div>

            <div className={styles.summaryItem}>
              <span>Selected Framework:</span>
              <strong className={styles.summaryItemValue}>Selenium (Web)</strong>
            </div>
          </div>
        </div>

        {/* Action Buttons: Report (left) + Execute (right) */}
        <div className={styles.executeButtonContainer}>
          <div className={styles.actionButtons}>
            <button
              onClick={viewReport}
              disabled={reportLoading}
              className={styles.reportButton}
            >
              {reportLoading ? "Opening report..." : "Report"}
            </button>

            <button
              onClick={executeStoryTest}
              disabled={loadingExecution}
              className={styles.executeButton}
            >
              {loadingExecution ? "Executing..." : "Execute"}
            </button>
          </div>
          {error && <div style={{ color: "red", marginTop: "0.5rem" }}>{error}</div>}
        </div>
      </div>

      {/* Back Button */}
      <div className={styles.backButtonContainer}>
        <button
          onClick={onBack}
          className={styles.backButton}
        >
          <i className="fa-solid fa-angle-left"></i>
          Back
        </button>
      </div>
    </div>
  );
};

export default Execute;

