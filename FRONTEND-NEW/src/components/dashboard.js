import React from "react";
import styles from "../css/Dashboard.module.css";

const Dashboard = ({
  projects = [],
  onOpen,
  onDelete,
  onToggle,
  onDownload,
  expandedProjectKey,
  loadingProjectKey,
  getProjectKey,
}) => {
  const totalProjects = Array.isArray(projects) ? projects.length : 0;

  const resolveProjectKey = (project, idx) => {
    if (typeof getProjectKey === "function") {
      return getProjectKey(project, idx);
    }
    return project?.id ?? `${project?.project_name || "project"}-${idx}`;
  };

  return (
    <div>
      <div className={styles.dashboardContainer}>
        <div className={styles.card}>
          <div>
            <h2 className={styles.cardTitle}> My Projects</h2>
            <p className={styles.cardValue}>{totalProjects}</p>
          </div>
          <i className={`fa-regular fa-folder ${styles.cardIcon}`}></i>
        </div>

        <div className={styles.card}>
          <div>
            <h2 className={styles.cardTitle}> Test Cases </h2>
            <p className={styles.cardValue}> 1 </p>
          </div>
          <i className={`fa-regular fa-file ${styles.cardIcon}`}></i>
        </div>

        <div className={styles.card}>
          <div>
            <h2 className={styles.cardTitle}> Active Projects</h2>
            <p className={styles.cardValue}> 2 </p>
          </div>
          <i className={`fa-solid fa-play ${styles.cardIcon}`}></i>
        </div>

        <div className={styles.card}>
          <div>
            <h2 className={styles.cardTitle}> Frameworks </h2>
            <p className={styles.cardValue}> 3 </p>
          </div>
          <i className={`fa-solid fa-code ${styles.cardIcon}`}></i>
        </div>
      </div>

      <div className={styles.recentProjectsHeader}>
        <h1 className={styles.recentProjectsTitle}>Recent Projects</h1>
        <button className={styles.viewAllButton}>
          View All Projects <i className="fa-solid fa-circle-chevron-down"></i>
        </button>
      </div>

      <div className={styles.projectList}>
        {totalProjects === 0 ? (
          <div style={{ color: "#666" }}>No projects yet. Create one to get started.</div>
        ) : (
          projects.map((p, idx) => {
            const projectKey = resolveProjectKey(p, idx);
            const isActive = expandedProjectKey === projectKey;
            const isLoading = loadingProjectKey === projectKey;

            return (
              <div
                key={projectKey}
                className={`${styles.projectCard} ${isActive ? styles.projectCardActive : ""}`}
              >
                <div className={styles.projectCardHeader}>
                  <h2 className={styles.projectCardTitle}>{p.project_name}</h2>
                  <div className={styles.projectCardMeta}>
                    <span className={styles.projectStatus}>saved</span>
                    <button
                      type="button"
                      className={styles.deleteButton}
                      onClick={() => onDelete && onDelete(p)}
                      aria-label={`Delete ${p.project_name}`}
                    >
                      <i className="fa-solid fa-trash" aria-hidden="true"></i>
                    </button>
                  </div>
                </div>

                <p className={styles.projectDescription}>
                  {(p.framework || "").trim()} {p.language ? ` / ${p.language}` : ""}
                </p>

                <div className={styles.projectDetails}>
                  <div className={styles.projectDetailRow}>
                    <span className={styles.projectDetailLabel}>Created</span>
                    <strong className={styles.projectDetailValue}>
                      {p.created_at ? new Date(p.created_at).toLocaleString() : "-"}
                    </strong>
                  </div>
                </div>

                <hr className={styles.projectCardDivider} />

                <div className={styles.projectCardActions}>
                  <button
                    className={styles.actionButton}
                    onClick={() => onToggle && onToggle(p, projectKey)}
                  >
                    <i className="fa-solid fa-gear"></i> Configure
                  </button>
                  <button
                    className={styles.actionButton}
                    onClick={() => onDownload && onDownload(p)}
                  >
                    <i className="fa-solid fa-download"></i> Download
                  </button>
                  <button
                    className={styles.executeButton}
                    onClick={() => onOpen && onOpen(p)}
                  >
                    <i className="fa-solid fa-play"></i> Open
                  </button>
                </div>

                {isActive && isLoading && (
                  <p className={styles.projectInlineLoading}>Loading...</p>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default Dashboard;
