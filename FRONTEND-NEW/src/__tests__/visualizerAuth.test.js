import axios from "axios";

import {
  buildBearerAuthHeaders,
  getStoredToken,
  requireBearerAuthHeaders,
} from "../utils/auth";
import { fetchProtectedAssetBlobUrl } from "../utils/protectedAssets";

jest.mock("axios");

describe("visualizer auth helpers", () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  test("reads the stored bearer token from localStorage", () => {
    localStorage.setItem("token", "abc123");

    expect(getStoredToken()).toBe("abc123");
    expect(buildBearerAuthHeaders()).toEqual({
      Authorization: "Bearer abc123",
    });
  });

  test("throws a clear error when a protected request is attempted without auth", () => {
    expect(() => requireBearerAuthHeaders()).toThrow("Authentication required. Please log in again.");
  });

  test("fetches protected visualizer assets with the bearer token", async () => {
    const blob = new Blob(["chart"], { type: "text/html" });
    const assetUrl = "https://api.example.test/visualizer/dashboard";
    localStorage.setItem("token", "secret-token");
    axios.get.mockResolvedValue({ data: blob });
    const createObjectURLSpy = jest
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:visualizer-dashboard");

    const result = await fetchProtectedAssetBlobUrl(assetUrl);

    expect(axios.get).toHaveBeenCalledWith(assetUrl, {
      headers: {
        Authorization: "Bearer secret-token",
      },
      responseType: "blob",
    });
    expect(result).toBe("blob:visualizer-dashboard");

    createObjectURLSpy.mockRestore();
  });
});
