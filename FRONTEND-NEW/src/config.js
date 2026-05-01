// config.js
const rawApiBaseUrl = (process.env.REACT_APP_API_URL || "").trim();
const isTest = process.env.NODE_ENV === "test";
const isProd = process.env.NODE_ENV === "production";

let resolvedBaseUrl = rawApiBaseUrl;
if (!resolvedBaseUrl) {
  if (isTest) {
    // Tests may import components without a full build-time env.
    // Keep a stable non-production fallback there only.
    // eslint-disable-next-line no-console
    console.warn("REACT_APP_API_URL is not set; using test fallback https://api.example.test");
    resolvedBaseUrl = "https://api.example.test";
  } else if (isProd) {
    resolvedBaseUrl = "/api";
  } else {
    // Local dev fallback to avoid blocking dev server.
    // eslint-disable-next-line no-console
    console.warn("REACT_APP_API_URL is not set; using dev fallback http://localhost:8001");
    resolvedBaseUrl = "http://localhost:8001";
  }
}

const API_BASE_URL = (resolvedBaseUrl || "/api").replace(/\/+$/, "");

export default API_BASE_URL;
