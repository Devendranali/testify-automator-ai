export function getStoredToken() {
  return localStorage.getItem("token") || "";
}

export function buildBearerAuthHeaders(token = getStoredToken()) {
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`,
  };
}

export function requireBearerAuthHeaders(token = getStoredToken()) {
  const headers = buildBearerAuthHeaders(token);
  if (!headers.Authorization) {
    throw new Error("Authentication required. Please log in again.");
  }
  return headers;
}
