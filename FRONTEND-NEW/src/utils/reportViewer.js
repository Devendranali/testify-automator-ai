import axios from "axios";

import { getStoredToken, requireBearerAuthHeaders } from "./auth";

const normalizeBase = (apiBaseUrl) => apiBaseUrl.replace(/\/+$/, "");

export function createReportWindow() {
  const reportWindow = window.open("", "_blank");
  if (!reportWindow) {
    throw new Error("Unable to open report window. Check your pop-up blocker settings.");
  }
  try {
    reportWindow.opener = null;
  } catch (error) {
    // Some browsers restrict direct opener reassignment; opening the window is still valid.
  }
  return reportWindow;
}

export async function prepareReportSession(apiBaseUrl, projectId) {
  const base = normalizeBase(apiBaseUrl);
  const response = await axios.post(
    `${base}/reports/session/${encodeURIComponent(projectId)}`,
    {},
    {
      headers: requireBearerAuthHeaders(),
      withCredentials: true,
    },
  );
  return response.data?.report_url || `/reports/view/${projectId}/`;
}

export async function openAuthenticatedReport(apiBaseUrl, projectId, reportWindow = createReportWindow()) {
  try {
    const base = normalizeBase(apiBaseUrl);
    const token = getStoredToken();
    if (!token) {
      throw new Error("Authentication required. Please log in again.");
    }
    const sessionUrl = `${base}/reports/session/${encodeURIComponent(projectId)}?token=${encodeURIComponent(token)}`;
    reportWindow.location.replace(sessionUrl);
  } catch (error) {
    reportWindow.close();
    throw error;
  }
}
