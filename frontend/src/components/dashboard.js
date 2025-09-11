import React from "react";
import styles from "../css/Dashboard.module.css";

const Dashboard = () => {
  return (
    <div>
      <div className={styles.dashboardContainer}>
        <div className={styles.card}>
          <div>
            <h2 className={styles.cardTitle}> My Projects</h2>
            <p className={styles.cardValue}>2</p>
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
        <div className={styles.projectCard}>
          <div className={styles.projectCardHeader}>
            <h2 className={styles.projectCardTitle}>E-commerce App</h2>
            <span className={styles.projectStatus}>active</span>
          </div>

          <p className={styles.projectDescription}>
            Mobile app automation testing
          </p>

          <div className={styles.projectDetails}>
            <div className={styles.projectDetailRow}>
              <span className={styles.projectDetailLabel}>Test Cases</span>
              <strong className={styles.projectDetailValue}>45</strong>
            </div>
            <div className={styles.projectDetailRow}>
              <span className={styles.projectDetailLabel}>Framework</span>
              <strong className={styles.projectDetailValue}>Appium</strong>
            </div>
            <div className={styles.projectDetailRow}>
              <span className={styles.projectDetailLabel}>Last Updated</span>
              <strong className={styles.projectDetailValue}>2 hours ago</strong>
            </div>
          </div>

          <hr className={styles.projectCardDivider} />

          <div className={styles.projectCardActions}>
            <button className={styles.actionButton}>
              <i className="fa-solid fa-gear"></i> Configure
            </button>

            <button className={styles.executeButton}>
              <i className="fa-solid fa-play"></i> Execute
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
