import React from "react";
import styles from "./Dashboard.module.css";

const Dashboard = ({ projects = [], onOpen }) => {
  const totalProjects = Array.isArray(projects) ? projects.length : 0;
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
            <p className={styles.cardValue}> 68 </p>
          </div>
          <i className={`fa-regular fa-file ${styles.cardIcon}`}></i>
        </div>

        <div className={styles.card}>
          <div>
            <h2 className={styles.cardTitle}> Active Projects</h2>
            <p className={styles.cardValue}> 1 </p>
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
          <div style={{ color: '#666' }}>No projects yet. Create one to get started.</div>
        ) : (
          projects.map((p, idx) => (
            <div key={`${p.project_name}-${idx}`} className={styles.projectCard}>
              <div className={styles.projectCardHeader}>
                <h2 className={styles.projectCardTitle}>{p.project_name}</h2>
                <span className={styles.projectStatus}>saved</span>
              </div>
              <p className={styles.projectDescription}>
                {(p.framework || '').trim()} {p.language ? ` / ${p.language}` : ''}
              </p>
              <div className={styles.projectDetails}>
                <div className={styles.projectDetailRow}>
                  <span className={styles.projectDetailLabel}>Created</span>
                  <strong className={styles.projectDetailValue}>{p.created_at ? new Date(p.created_at).toLocaleString() : '-'}</strong>
                </div>
              </div>
              <hr className={styles.projectCardDivider} />
              <div className={styles.projectCardActions}>
                <button className={styles.actionButton} disabled>
                  <i className="fa-solid fa-gear"></i> Configure
                </button>
                <button
                  className={styles.executeButton}
                  onClick={() => onOpen && onOpen(p)}
                >
                  <i className="fa-solid fa-play"></i> Open
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Dashboard;
