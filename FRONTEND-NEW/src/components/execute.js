import React, { useState } from "react";
import axios from "axios";
import API_BASE_URL from "../config";
import { toast } from "react-toastify";
import styles from "./Execute.module.css";

const Execute = ({ onBack, fullTestData }) => {
  const [loadingExecution, setLoadingExecution] = useState(false);
  const [executionSuccess, setExecutionSuccess] = useState(false);
  const [executionError, setExecutionError] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [error, setError] = useState("");

  const executeStoryTest = async () => {
    setLoadingExecution(true);
    setError("");
    setExecutionResult(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/rag/run-generated-story-test`);

      setExecutionResult(response.data);
      toast.success("✅ Execution successful.");
      setExecutionSuccess(true);
    } catch (err) {
      setError(err.response?.data?.message || "Error executing story test.");
      setExecutionError(true);
    } finally {
      setLoadingExecution(false);
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

        {/* Execute Button */}
        <div className={styles.executeButtonContainer}>
          <button
            onClick={executeStoryTest}
            disabled={loadingExecution}
            className={styles.executeButton}
          >
            {loadingExecution ? "Executing..." : "Execute"}
          </button>
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

