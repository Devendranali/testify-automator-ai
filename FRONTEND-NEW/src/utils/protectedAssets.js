import axios from "axios";

import { requireBearerAuthHeaders } from "./auth";

export async function fetchProtectedAssetBlobUrl(url, responseType = "blob") {
  const response = await axios.get(url, {
    headers: requireBearerAuthHeaders(),
    responseType,
  });
  return URL.createObjectURL(response.data);
}
