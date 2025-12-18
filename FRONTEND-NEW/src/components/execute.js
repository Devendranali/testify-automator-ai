import React, { useMemo, useEffect, useState } from "react";
import axios from "axios";
import API_BASE_URL from "../config";
import { toast } from "react-toastify";
import styles from "../css/Execute.module.css";

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

const Execute = ({ onBack, fullTestData }) => {
  const [loadingExecution, setLoadingExecution] = useState(false);
  const [executionSuccess, setExecutionSuccess] = useState(false);
  const [executionError, setExecutionError] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [error, setError] = useState("");

  const [reportLoading, setReportLoading] = useState(false);
  const [visualizerImages, setVisualizerImages] = useState([]);
  const [visualizerLoading, setVisualizerLoading] = useState(false);
  const [visualizerError, setVisualizerError] = useState("");
  const [showVisualizer, setShowVisualizer] = useState(false);
  const [visualizerMode, setVisualizerMode] = useState("idle"); // idle | interactive | images
  const [visualizerDashboardUrl, setVisualizerDashboardUrl] = useState("");

  const [metrics, setMetrics] = useState(null);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [metricsError, setMetricsError] = useState("");

  const executeStoryTest = async () => {
    setLoadingExecution(true);
    setError("");
    setExecutionResult(null);

      try {
        const res = await axios.get(`${API_BASE_URL}/tests/report`, { params: { test: "tests/test_1.py" } });
        const data = res.data;
        if (!data) throw new Error("No response data returned from server");
        const uri = data.report_url || data.report_uri || data.file_uri || data.path;
        if (!uri) throw new Error("No report URL/URI returned");
        window.open(uri, "_blank", "noopener,noreferrer");
        setExecutionResult(data);
        toast.success("✅ Execution & report generated.");
        setExecutionSuccess(true);
        await fetchMetrics();
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
      const res = await axios.get(`${API_BASE_URL}/tests/open`, { params: { test: "tests/test_1.py" } });
      const data = res.data;
      if (!data) throw new Error("No response data returned from server");
      const uri = data.report_url || data.report_uri || data.file_uri || data.path;
      if (!uri) throw new Error("No report URL/URI returned from server");
      window.open(uri, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err.response?.data || err.message || "Failed to open report");
    } finally {
      setReportLoading(false);
    }
  };

  const formatVisualizerAssetUrl = (url) => {
    if (!url) return "";
    if (/^https?:\/\//i.test(url)) {
      return url;
    }
    const base = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const path = url.startsWith("/") ? url : `/${url}`;
    return `${base}${path}`;
  };

  const loadVisualizerContent = async () => {
    if (visualizerLoading) {
      return;
    }
    setVisualizerLoading(true);
    setVisualizerError("");
    try {
      const res = await axios.get(`${API_BASE_URL}/visualizer/images`);
      const images = Array.isArray(res.data?.images) ? res.data.images : [];
      const dashboardPath = res.data?.interactive_dashboard;

      if (dashboardPath) {
        const absoluteDashboard = formatVisualizerAssetUrl(dashboardPath);
        setVisualizerDashboardUrl(`${absoluteDashboard}?t=${Date.now()}`);
        setVisualizerMode("interactive");
        setVisualizerImages([]);
      } else {
        setVisualizerImages(images);
        setVisualizerMode("images");
      }

      setShowVisualizer(true);
    } catch (err) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data ||
        err?.message ||
        "Failed to load visualizations.";
      setVisualizerError(detail);
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
    if (visualizerMode === "interactive" && visualizerDashboardUrl) {
      const baseUrl = visualizerDashboardUrl.split("?")[0];
      setVisualizerDashboardUrl(`${baseUrl}?t=${Date.now()}`);
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
      const res = await axios.get(`${API_BASE_URL}/metrics/dashboard`);
      setMetrics(res.data);
    } catch (err) {
      setMetricsError(err?.response?.data?.detail || err?.message || "Unable to load quality metrics.");
    } finally {
      setMetricsLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  return (
    <div className={styles.executeContainer}>
      <div className={styles.contentBox}>
        {/* Heading Section */}
        <h3 className={styles.heading}>
          <i className={`fa-solid fa-code ${styles.headingIcon}`}></i>
          Generate Scripts
        </h3>
        <p className={styles.subheading}>Configure framework and generate test scripts</p>

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

        <div className={styles.metricsWrapper}>
          <div className={styles.metricsHeader}>
            <div>
              <h4>Quality &amp; Self-Healing Insights</h4>
              <p>Pass rates, self-healing power, flakiness, and risk heatmap generated from Allure.</p>
            </div>
            {metricsLoading && <span className={styles.metricsLoading}>Loading metrics…</span>}
          </div>

          {metricsError && <p className={styles.metricsError}>{metricsError}</p>}

          {metrics && (
            <>
              <div className={styles.metricCards}>
                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>Self-healing save rate</span>
                  <strong>{formatPercent(summary.save_rate)}</strong>
                  <p>
                    {summary.saved ?? 0}/{summary.tests ?? 0} tests healed successfully.
                  </p>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>Self-healing power</span>
                  <strong>{formatPercent(summary.power)}</strong>
                  <p>Pass rate × save rate indicates stability improvement.</p>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>Last run status</span>
                  <strong>
                    {formatCount(latestStatus.passed)} - pass  
                    <br/>{formatCount(latestStatus.failed)} - fail {" "}
                    <br/>{formatCount(latestStatus.broken)} - broken
                  </strong>
                  <p>{summary.total ?? 0} tests executed</p>
                </div>
                <div className={styles.metricCard}>
                  <span className={styles.metricLabel}>Trend window</span>
                  <strong>
                    {formatCount(periods?.["7_days"]?.passed)} - passed this week {" "}
                    <br/>{formatCount(periods?.["7_days"]?.failed)} - failed
                  </strong>
                  <p>{formatCount(periods?.["30_days"]?.total)} tests last 30 days</p>
                </div>
              </div>

              <div className={styles.metricsCharts}>
                <div className={styles.metricsChart}>
                  <div className={styles.chartHeader}>
                    <h5>Quality over time</h5>
                    <span>Pass rate history</span>
                  </div>
                  <QualitySparkline data={metrics.pass_rate_history} />
                </div>
                <div className={styles.metricsChart}>
                  <div className={styles.chartHeader}>
                    <h5>Self-healed actions</h5>
                    <span>Last {metrics.healing_history?.length ?? 0} runs</span>
                  </div>
                  <ul className={styles.metricsHistory}>
                    {(metrics.healing_history || []).slice(-5).map((item, index) => {
                      const label = item.timestamp ? new Date(item.timestamp).toLocaleString() : "Recent run";
                      return (
                        <li key={`${item.timestamp ?? "healing"}-${index}`}>
                          <strong>{item.healing_actions ?? 0}</strong> actions ·{" "}
                          <span>{item.healing_saved ?? 0} saved</span>
                          <small>{label}</small>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              </div>

              <div className={styles.metricsLists}>
                <div className={styles.metricsList}>
                  <h5>Flaky Champions</h5>
                  <ul>
                    {(metrics.flaky_champions || []).slice(0, 5).map((flaky) => (
                      <li key={flaky.name}>
                        <span>{flaky.name}</span>
                        <small>
                          {flaky.flaky_score} flips · {flaky.failures} failures · {flaky.healing_actions} healing
                        </small>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className={styles.metricsList}>
                  <h5>Risk heatmap / top healed pages</h5>
                  <ul>
                    {(metrics.risk_heatmap || []).slice(0, 5).map((feature) => (
                      <li key={feature.name}>
                        <span>{feature.name}</span>
                        <small>
                          fail rate {formatPercent(feature.fail_rate)} · {feature.healing_actions} healing
                        </small>
                      </li>
                    ))}
                  </ul>
                  <div className={styles.topHealed}>
                    <strong>Top healed pages</strong>
                    <ul>
                      {(metrics.top_healed_pages || []).map((page) => (
                        <li key={`healed-${page.name}`}>
                          <span>{page.name}</span>
                          <small>{page.healing_actions} healing actions</small>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
              <div className={styles.selfHealingSection}>
                <div className={styles.selfHealingHeader}>
                  <h5>Self-Healing Intelligence</h5>
                  <span>SmartAI actions per run</span>
                </div>
                <div className={styles.selfHealingCards}>
                  <div className={styles.selfHealingCard}>
                    <span className={styles.metricLabel}>Saved failures</span>
                    <strong>{formatCount(summary.saved)}</strong>
                    <p>{formatPercent(summary.save_rate)} save rate</p>
                  </div>
                  <div className={styles.selfHealingCard}>
                    <span className={styles.metricLabel}>Healing actions</span>
                    <strong>{formatCount(summary.actions)}</strong>
                    <p>{formatPercent(summary.power)} heal power</p>
                  </div>
                  <div className={styles.selfHealingCard}>
                    <span className={styles.metricLabel}>Failed heals</span>
                    <strong>{formatCount(selfHealing.summary?.failed || 0)}</strong>
                    <p>Need tuning</p>
                  </div>
                </div>
                <div className={styles.selfHealingGrid}>
                  <div className={styles.selfHealingList}>
                    <h6>Strategy usage</h6>
                    <ul>
                      {healingStrategies.length ? (
                        healingStrategies.slice(0, 5).map((strategy) => (
                          <li key={strategy.strategy}>
                            <span>{strategy.strategy}</span>
                            <small>{formatCount(strategy.count)} uses</small>
                          </li>
                        ))
                      ) : (
                        <li>No healing strategy data yet.</li>
                      )}
                    </ul>
                  </div>
                  <div className={styles.selfHealingList}>
                    <h6>Healed steps by feature</h6>
                    <ul>
                      {healingSteps.length ? (
                        healingSteps.slice(0, 5).map((entry) => (
                          <li key={entry.name}>
                            <span>{entry.name}</span>
                            <small>
                              {formatCount(entry.healed_steps)} of {formatCount(entry.total_steps)} steps healed
                            </small>
                          </li>
                        ))
                      ) : (
                        <li>Run tests with healing to collect data.</li>
                      )}
                    </ul>
                  </div>
                  <div className={styles.selfHealingList}>
                    <h6>Recent healing runs</h6>
                    <ul>
                      {healingHistory.length ? (
                        healingHistory.slice(-3).map((item) => (
                          <li key={item.timestamp}>
                            <span>{formatCount(item.healing_actions)} actions</span>
                            <small>{new Date(item.timestamp).toLocaleString()}</small>
                          </li>
                        ))
                      ) : (
                        <li>No history yet.</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Action Buttons: Report + Execute + Visualize */}
        <div className={styles.executeButtonContainer}>
          <div className={styles.actionButtons}>
            <button onClick={viewReport} disabled={true} className={styles.reportButton}>
              {reportLoading ? "Opening report..." : "Report"}
            </button>

            <button onClick={executeStoryTest} disabled={loadingExecution} className={styles.executeButton}>
              {loadingExecution ? "Executing..." : "Execute"}
            </button>

            <button onClick={handleToggleVisualizer} disabled={visualizerLoading} className={styles.visualizeButton}>
              {visualizerLoading ? "Loading visuals..." : showVisualizer ? "Hide Visual Charts" : "Visualize Charts"}
            </button>
          </div>
          {error && <div style={{ color: "red", marginTop: "0.5rem" }}>{error}</div>}

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
                          src={formatVisualizerAssetUrl(image.url)}
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
