import React, { useState } from "react";
import axios from "axios";
import API_BASE_URL from "../config";
import { toast } from "react-toastify";
import styles from "./URLInput.module.css";

const URLInput = ({ onBack, onNext }) => {
  const [url, setUrl] = useState("");
  const [fullTestData, setFullTestData] = useState(null);
  const [loadingEnrich, setLoadingEnrich] = useState(false);
  const [error, setError] = useState("");

  const enrichLocaters = async () => {
    if (!url || url.trim() === "") {
      setError("Please enter a valid URL");
      return;
    }

    try {
      new URL(url);
    } catch (_) {
      setError("Please enter a valid URL format (e.g., https://example.com)");
      return;
    }

    setLoadingEnrich(true);
    setError("");
    setFullTestData(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/launch-browser`, {
        url: url
      });

      const data = response.data;
      setFullTestData(data);
      toast.success("Locators enriched successfully");
    } catch (err) {
      setError(err.response?.data?.message || "Error enriching locators");
    } finally {
      setLoadingEnrich(false);
    }
  };

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
            {loadingEnrich ? "Enriching..." : "Enrich Locaters"}
          </button>
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
          className={`${styles.navButton} ${styles.next}`}
        >
          Next <i className="fa-solid fa-angle-right"></i>
        </button>
      </div>
    </div>
  );
};

export default URLInput;

