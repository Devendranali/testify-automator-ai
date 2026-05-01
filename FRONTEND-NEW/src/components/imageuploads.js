import React, { useEffect, useState, useCallback, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import API_BASE_URL from "../config";
import ImagePreviewGrid from "./imagepreviewgrid";
import styles from "../css/ImageUpload.module.css";
import useAppStore from "../state/useAppStore";
import useScopedToast from "../hooks/useScopedToast";

const ImageUpload = ({ handleNext, projectName, projectId, mode = "workflow" }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const notify = useScopedToast();
  const [loadingIngestion, setLoadingIngestion] = useState(false);
  const [loadingMethods, setLoadingMethods] = useState(false);
  const [ingestionSuccess, setIngestionSuccess] = useState(false);
  const [deletingImages, setDeletingImages] = useState(false);
  const [replacingImage, setReplacingImage] = useState(false);
  const [error, setError] = useState("");
  const uploadAbortRef = useRef(null);
  const uploadSessionIdRef = useRef(null);
  const uploadSelectionSnapshotRef = useRef([]);
  const uploadCancelRequestedRef = useRef(false);
  const ALLOWED_IMAGE_EXTS = useRef(new Set(["png", "jpg", "jpeg", "bmp", "gif", "webp"]));
  const allowedFormatsLabel = "PNG, JPG, JPEG, BMP, GIF, WEBP";
  const activeProjectId = useAppStore((state) => state.project.activeProjectId);
  const activeProjectName = useAppStore((state) => state.project.activeProjectName);
  const setActiveProject = useAppStore((state) => state.setActiveProject);
  const selectedFiles = useAppStore((state) => state.uploads.images);
  const setSelectedFiles = useAppStore((state) => state.setUploadedImages);
  const addUploadedImages = useAppStore((state) => state.addUploadedImages);
  const pageNames = useAppStore((state) => state.uploads.pageNames);
  const setPageNames = useAppStore((state) => state.setPageNames);
  const impactedSummary = useAppStore((state) => state.testCases.impactedSummary);
  const impactedItems = useAppStore((state) => state.testCases.impactedItems);
  const setImpactedTestcases = useAppStore((state) => state.setImpactedTestcases);
  const clearImpactedTestcases = useAppStore((state) => state.clearImpactedTestcases);
  const inputFlow = useAppStore((state) => state.navigation.inputFlow);
  const inputStartFlow = useAppStore((state) => state.navigation.inputStartFlow);
  const flowFromState = location.state?.flow;
  const flowFromPath = (location.pathname || "").endsWith("/input/upload") ? null : null;
  const flowType = flowFromState || inputStartFlow || inputFlow || flowFromPath;
  const isUrlFlow = flowType === "url";
  const isMaintenanceMode =
    mode === "maintenance" || (location.pathname || "").endsWith("/input/image-update");
  const hasLoadedRemoteRef = useRef(false);
  const hasLoadedPagesRef = useRef(false);

  const syncActiveProject = useCallback(
    (id, name) => {
      if (id || name) {
        setActiveProject({
          id: id ? String(id) : null,
          name: name || null,
        });
      }
    },
    [setActiveProject]
  );

  useEffect(() => {
    syncActiveProject(projectId, projectName);
  }, [projectId, projectName, syncActiveProject]);

  const removePendingImage = useCallback(
    (targetFile) => {
      if (!targetFile) {
        return;
      }
      setSelectedFiles(
        selectedFiles.filter((file) => {
          if (targetFile.id && file?.id) {
            return file.id !== targetFile.id;
          }
          return file?.name !== targetFile.name;
        })
      );
    },
    [selectedFiles, setSelectedFiles]
  );

  const loadPersistedImages = useCallback(async ({ force = false, preservePending = false } = {}) => {
    if (!activeProjectId) {
      return;
    }
    if (!force && hasLoadedRemoteRef.current) {
      return;
    }
    const hasPreview = selectedFiles.some((file) => file?.preview || file?.dataUrl);
    if (!force && selectedFiles.length > 0 && hasPreview) {
      return;
    }
    hasLoadedRemoteRef.current = true;
    try {
      const token = localStorage.getItem("token");
      const listResponse = await fetch(
        `${API_BASE_URL}/projects/${activeProjectId}/files?path=data/images`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (!listResponse.ok) {
        if (force) {
          setSelectedFiles(
            preservePending ? selectedFiles.filter((file) => !file?.persisted) : []
          );
        }
        return;
      }
      const listPayload = await listResponse.json();
      const entries = Array.isArray(listPayload?.entries) ? listPayload.entries : [];
      const imageEntries = entries.filter((entry) => entry?.type === "file");
      if (imageEntries.length === 0) {
        setSelectedFiles(
          preservePending ? selectedFiles.filter((file) => !file?.persisted) : []
        );
        return;
      }
      const fetched = [];
      for (const entry of imageEntries) {
        const contentResponse = await fetch(
          `${API_BASE_URL}/projects/${activeProjectId}/files/content?path=${encodeURIComponent(
            entry.path
          )}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (!contentResponse.ok) continue;
        const payload = await contentResponse.json();
        const encoding = String(payload?.encoding || "").toLowerCase();
        const name = entry.name || payload?.path || "image";
        let dataUrl = "";
        if (encoding === "base64") {
          const ext = name.split(".").pop()?.toLowerCase() || "png";
          const mime =
            ext === "jpg" || ext === "jpeg"
              ? "image/jpeg"
              : ext === "bmp"
              ? "image/bmp"
              : ext === "gif"
              ? "image/gif"
              : ext === "webp"
              ? "image/webp"
              : "image/png";
          dataUrl = `data:${mime};base64,${payload?.content || ""}`;
        } else if (payload?.content) {
          dataUrl = payload.content;
        }
        if (!dataUrl) continue;
        fetched.push({
          id: `${name}-${Date.now()}`,
          name,
          type: dataUrl.startsWith("data:image/")
            ? dataUrl.slice("data:".length, dataUrl.indexOf(";"))
            : "",
          size: Number(payload?.size) || 0,
          dataUrl,
          preview: dataUrl,
          persisted: true,
        });
      }
      const pendingFiles = preservePending
        ? selectedFiles.filter((file) => !file?.persisted)
        : [];
      setSelectedFiles([...fetched, ...pendingFiles]);
    } catch (err) {
      console.error("Failed to load persisted images:", err);
    }
  }, [activeProjectId, selectedFiles, setSelectedFiles]);

  useEffect(() => {
    loadPersistedImages();
  }, [loadPersistedImages]);

  const loadPersistedPages = useCallback(async ({ force = false } = {}) => {
    if (!activeProjectId) {
      return;
    }
    if (!force && hasLoadedPagesRef.current) {
      return;
    }
    if (!force && pageNames.length > 0) {
      return;
    }
    hasLoadedPagesRef.current = true;
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${API_BASE_URL}/projects/${activeProjectId}/files?path=pages`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      if (!response.ok) {
        if (force) {
          setPageNames([]);
        }
        return;
      }
      const payload = await response.json();
      const entries = Array.isArray(payload?.entries) ? payload.entries : [];
      const names = entries
        .filter((entry) => entry?.type === "file")
        .map((entry) => entry.name || "")
        .filter(Boolean)
        .filter((name) => /(_page_methods\.py|_page\.py)$/i.test(name))
        .map((name) => name.replace(/_page_methods\.py$/i, "").replace(/_page\.py$/i, ""));
      setPageNames(Array.from(new Set(names)));
    } catch (err) {
      console.error("Failed to load persisted pages:", err);
    }
  }, [activeProjectId, pageNames.length, setPageNames]);

  useEffect(() => {
    loadPersistedPages();
  }, [loadPersistedPages]);

  const ensureActiveProject = useCallback(async () => {
    if (activeProjectId) {
      return activeProjectId;
    }
    const token = localStorage.getItem("token");
    const name = projectName || activeProjectName;
    if (!token || !name) {
      return null;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/projects/activate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ project_name: name }),
      });
      if (!response.ok) {
        const txt = await response.text().catch(() => null);
        throw new Error(txt || `Failed to activate project (${response.status})`);
      }
      const payload = await response.json();
      const newId = payload?.project?.id ? String(payload.project.id) : null;
      if (newId) {
        setActiveProject({ id: newId, name });
      }
      return newId;
    } catch (err) {
      console.error("Failed to activate project before upload:", err);
      notify.error(err.message || "Failed to activate project.");
      return null;
    }
  }, [activeProjectId, projectName, setActiveProject]);

  const createUploadSessionId = useCallback(() => {
    if (typeof window !== "undefined" && window.crypto?.randomUUID) {
      return window.crypto.randomUUID();
    }
    return `upload-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }, []);

  const requestUploadCancel = useCallback(async (projectIdToCancel, sessionIdOverride = null) => {
    const sessionId = sessionIdOverride || uploadSessionIdRef.current;
    if (!projectIdToCancel || !sessionId) {
      return;
    }
    try {
      const token = localStorage.getItem("token");
      await fetch(`${API_BASE_URL}/${projectIdToCancel}/upload-image/cancel`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch (cancelErr) {
      console.warn("Failed to notify backend about upload cancellation:", cancelErr);
    }
  }, []);

  const dataUrlToBlob = (dataUrl, fallbackType = "application/octet-stream") => {
    if (!dataUrl) {
      return null;
    }
    const [meta, data] = dataUrl.split(",");
    if (!data) {
      return null;
    }
    const match = meta.match(/data:(.*);base64/);
    const mime = match ? match[1] : fallbackType;
    const binary = atob(data);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new Blob([bytes], { type: mime });
  };

  const getFileExt = (name) => {
    if (!name) return "";
    const idx = name.lastIndexOf(".");
    return idx >= 0 ? name.slice(idx + 1).toLowerCase() : "";
  };

  const applyImpactPayload = useCallback(
    (impact, summaryOverrides = {}) => {
      setImpactedTestcases({
        summary: {
          mode: impact?.mode || "conservative",
          actionType: impact?.change_type || summaryOverrides.actionType || "replace",
          count: Number(impact?.count) || 0,
          affectedPage: impact?.affected_page || summaryOverrides.affectedPage || "",
          affectedPages: Array.isArray(impact?.affected_pages) ? impact.affected_pages : [],
          oldImageName: summaryOverrides.oldImageName || "",
          newImageName: summaryOverrides.newImageName || "",
        },
        items: Array.isArray(impact?.impacted_testcases) ? impact.impacted_testcases : [],
      });
    },
    [setImpactedTestcases]
  );

  const previewImageImpact = useCallback(
    async (targetFile, actionType = "delete", replacementFile = null) => {
      const imageName =
        typeof targetFile === "string" ? targetFile : targetFile?.name || "";
      const isPersistedImage =
        typeof targetFile === "object" ? Boolean(targetFile?.persisted) : true;

      if (!imageName) {
        return null;
      }
      if (!isPersistedImage) {
        clearImpactedTestcases();
        return null;
      }

      try {
        const activeId = await ensureActiveProject();
        if (!activeId) {
          throw new Error("No active project. Please start a project first.");
        }
        const token = localStorage.getItem("token");
        const response = await fetch(`${API_BASE_URL}/${activeId}/images/impact-preview`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            image_name: imageName,
            action_type: actionType,
            replacement_image_name: replacementFile?.name || null,
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload?.detail || "Failed to preview impacted testcases.");
        }
        applyImpactPayload(payload?.impact || {}, {
          actionType,
          affectedPage: payload?.impact?.affected_page || "",
          oldImageName: imageName || "",
          newImageName: replacementFile?.name || "",
        });
        return payload?.impact || null;
      } catch (err) {
        console.error("Failed to preview impacted testcases:", err);
        return null;
      }
    },
    [applyImpactPayload, clearImpactedTestcases, ensureActiveProject]
  );

  const handleFileChange = async (e) => {
    const inputFiles = Array.from(e.target.files);
    let allProcessedFiles = [];

    for (const file of inputFiles) {
      const ext = getFileExt(file?.name);
      const isAllowedImage = ALLOWED_IMAGE_EXTS.current.has(ext);
      const isZip = ext === "zip" || file?.name?.toLowerCase?.().endsWith(".zip");

      if (isAllowedImage) {
        const previewFile = new File([file], file.name, { type: file.type });
        previewFile.preview = URL.createObjectURL(previewFile);
        allProcessedFiles.push(previewFile);
      } else if (isZip) {
        try {
          const JSZip = (await import("jszip")).default;
          const zip = await JSZip.loadAsync(file);
          const unsupported = [];
          const extracted = [];

          for (const zipEntry of Object.values(zip.files)) {
            if (zipEntry.dir) continue;
            const entryBase = (zipEntry.name || "").split("/").pop() || "";
            const entryExt = getFileExt(entryBase);
            if (ALLOWED_IMAGE_EXTS.current.has(entryExt)) {
              const blob = await zipEntry.async("blob");
              const imageFile = new File([blob], zipEntry.name, {
                type: blob.type,
              });
              imageFile.preview = URL.createObjectURL(imageFile);
              extracted.push(imageFile);
            } else if (/\.(png|jpe?g|bmp|gif|webp|tiff?|jfif|heic|heif|svg|avif|ico)$/i.test(entryBase)) {
              unsupported.push(entryBase);
            }
          }

          if (unsupported.length > 0) {
            const preview = unsupported.slice(0, 10).join(", ");
            const suffix = unsupported.length > 10 ? "..." : "";
            notify.error(
              `Unsupported image format(s) in ZIP '${file.name}': ${preview}${suffix}. Supported formats: ${allowedFormatsLabel}.`
            );
            continue;
          }
          if (extracted.length === 0) {
            notify.error(`ZIP '${file.name}' contains no supported images. Supported formats: ${allowedFormatsLabel}.`);
            continue;
          }
          allProcessedFiles = allProcessedFiles.concat(extracted);
        } catch (err) {
          notify.error("Failed to extract ZIP file.");
        }
      } else {
        notify.error(
          `Unsupported file format: ${file?.name || "unknown"}. Supported formats: ${allowedFormatsLabel}.`
        );
      }
    }

    try {
      const result = await addUploadedImages(allProcessedFiles);
      const skipped = Number(result?.skippedCount) || 0;
      if (skipped > 0) {
        notify.info(`Skipped ${skipped} duplicate image${skipped === 1 ? "" : "s"}.`);
      }
    } catch (err) {
      console.error("Failed to process image files:", err);
      notify.error("Failed to process image files.");
    }
  };

  const handleContinue = async () => {
    setLoadingIngestion(true);
    setError("");
    setIngestionSuccess(false);
    uploadCancelRequestedRef.current = false;
    if (uploadAbortRef.current) {
      uploadAbortRef.current.abort();
    }
    uploadAbortRef.current = new AbortController();

    if (selectedFiles.length === 0) {
      notify.warn("Please upload at least one file.");
      setLoadingIngestion(false);
      return;
    }

    const uploadableFiles = selectedFiles.filter((file) => file?.dataUrl && !file?.persisted);
    uploadSelectionSnapshotRef.current = selectedFiles.map((file) => ({ ...file }));
    if (uploadableFiles.length === 0) {
      notify.warn(
        isMaintenanceMode
          ? "Add at least one new image to upload."
          : "Uploaded images are not ready yet. Please reselect the files."
      );
      setLoadingIngestion(false);
      return;
    }

    const formData = new FormData();
    uploadableFiles.forEach((file) => {
      if (file?.dataUrl) {
        const blob = dataUrlToBlob(file.dataUrl, file.type);
        if (blob) {
          formData.append("images", blob, file.name);
        }
      }
    });

    const orderedImageNames = uploadableFiles.map((file) => file.name);
    formData.append("ordered_images", JSON.stringify({ ordered_images: orderedImageNames }));
    const uploadSessionId = createUploadSessionId();
    uploadSessionIdRef.current = uploadSessionId;
    formData.append("upload_session_id", uploadSessionId);

    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
      const response = await axios.post(
        `${API_BASE_URL}/${activeId}/upload-image`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Bearer ${token}`,
          },
          signal: uploadAbortRef.current.signal,
        }
      );

      if (response.status === 200) {
        notify.success("OCR extracted and stored in ChromaDB successfully.");
        setIngestionSuccess(true);
        clearImpactedTestcases();
        hasLoadedRemoteRef.current = false;
        await loadPersistedImages({ force: true, preservePending: false });
      }
    } catch (error) {
      if (uploadAbortRef.current?.signal?.aborted) {
        setError("");
        setSelectedFiles(uploadSelectionSnapshotRef.current.map((file) => ({ ...file })));
      } else {
        console.error("Error uploading files:", error);
        const detail =
          error?.response?.data?.detail ||
          error?.response?.data?.message ||
          error?.message ||
          "Please try again.";
        setError(detail);
        notify.error(`Error uploading files: ${detail}`);
      }
    } finally {
      setLoadingIngestion(false);
      uploadAbortRef.current = null;
      uploadSessionIdRef.current = null;
      uploadCancelRequestedRef.current = false;
    }
  };

  const handleCancelUpload = async () => {
    if (loadingIngestion && uploadAbortRef.current) {
      if (uploadCancelRequestedRef.current) {
        return;
      }
      uploadCancelRequestedRef.current = true;
      const controller = uploadAbortRef.current;
      const sessionId = uploadSessionIdRef.current;
      controller.abort();
      setSelectedFiles(uploadSelectionSnapshotRef.current.map((file) => ({ ...file })));
      setIngestionSuccess(false);
      setError("");
      notify.info("Upload canceled.");
      Promise.resolve(ensureActiveProject())
        .then((activeId) => requestUploadCancel(activeId, sessionId))
        .catch((cancelErr) => {
          console.warn("Failed to complete backend upload cancellation:", cancelErr);
        });
      return;
    }
    setIngestionSuccess(false);
    setError("");
    clearImpactedTestcases();

    if (isMaintenanceMode) {
      hasLoadedRemoteRef.current = false;
      hasLoadedPagesRef.current = false;
      loadPersistedImages({ force: true, preservePending: false });
      loadPersistedPages({ force: true });
      notify.info("Pending image changes cleared.");
      return;
    }

    setSelectedFiles([]);
    setPageNames([]);
    notify.info("Selection cleared.");
  };

  const handleGenerateMethods = async () => {
    setLoadingMethods(true);
    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/${activeId}/rag/generate-page-methods`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({}),
      });

      const data = await response.json();
      const names = Object.keys(data || {});
      setPageNames(names);
      if (names.length > 0) {
        notify.success("Successfully generated methods");
      }
    } catch (error) {
      console.error("Error fetching page methods:", error);
      setPageNames([]);
      notify.error("Error generating methods");
    } finally {
      setLoadingMethods(false);
    }
  };

  const handleDeleteImage = async (targetFile) => {
    const imageName =
      typeof targetFile === "string" ? targetFile : targetFile?.name || "";
    const isPersistedImage =
      typeof targetFile === "object" ? Boolean(targetFile?.persisted) : true;

    if (!imageName) {
      return;
    }

    if (!isPersistedImage) {
      removePendingImage(targetFile);
      notify.info(`Removed ${imageName} from pending uploads.`);
      return;
    }

    setDeletingImages(true);
    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_BASE_URL}/${activeId}/images`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ image_names: [imageName] }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || "Failed to delete selected images.");
      }

      const deletedNames = Array.isArray(payload?.deleted)
        ? payload.deleted.map((item) => item?.image_name).filter(Boolean)
        : [];
      const deletedSet = new Set(deletedNames);

      setSelectedFiles(
        selectedFiles.filter((file) => {
          if (!file?.persisted) {
            return true;
          }
          return !deletedSet.has(file?.name);
        })
      );
      hasLoadedRemoteRef.current = false;
      hasLoadedPagesRef.current = false;
      await loadPersistedImages({ force: true, preservePending: true });
      await loadPersistedPages({ force: true });
      applyImpactPayload(payload?.impact || {}, {
        actionType: "delete",
        oldImageName: imageName || "",
      });

      notify.success(
        deletedNames.length > 0
          ? `Deleted ${deletedNames.length} image${deletedNames.length === 1 ? "" : "s"} and matching page methods.`
          : "No matching uploaded images were deleted."
      );
    } catch (err) {
      console.error("Failed to delete uploaded images:", err);
      notify.error(err.message || "Failed to delete uploaded images.");
    } finally {
      setDeletingImages(false);
    }
  };

  const handleReplaceImage = async (targetFile, replacementFile, options = {}) => {
    const oldImageName =
      typeof targetFile === "string" ? targetFile : targetFile?.name || "";
    const isPersistedImage =
      typeof targetFile === "object" ? Boolean(targetFile?.persisted) : true;

    if (!replacementFile) {
      return;
    }

    if (!oldImageName) {
      return;
    }

    const ext = getFileExt(replacementFile.name);
    if (!ALLOWED_IMAGE_EXTS.current.has(ext)) {
      notify.error(`Unsupported replacement format. Supported formats: ${allowedFormatsLabel}.`);
      return;
    }

    if (!isPersistedImage) {
      try {
        const result = await addUploadedImages([replacementFile]);
        if ((Number(result?.addedCount) || 0) === 0) {
          notify.warn(`Could not replace ${oldImageName}. The new file may already exist in the selection.`);
          return;
        }
        removePendingImage(targetFile);
        notify.success(`Replaced pending image ${oldImageName} with ${replacementFile.name}.`);
      } catch (err) {
        console.error("Failed to replace pending image:", err);
        notify.error("Failed to replace pending image.");
      }
      return;
    }

    notify.info(
      `Replacing ${oldImageName || "image"} with ${replacementFile.name || "selected image"}...`
    );
    setReplacingImage(true);
    try {
      if (!options?.skipPreview) {
        await previewImageImpact(targetFile, "replace", replacementFile);
      }
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("old_image_name", oldImageName);
      formData.append("image", replacementFile, replacementFile.name);

      const response = await axios.post(`${API_BASE_URL}/${activeId}/images/replace`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
          Authorization: `Bearer ${token}`,
        },
      });

      const replaced = response?.data?.replaced || {};
      const impact = response?.data?.impact || {};
      hasLoadedRemoteRef.current = false;
      hasLoadedPagesRef.current = false;
      await loadPersistedImages({ force: true, preservePending: true });
      await loadPersistedPages({ force: true });
      applyImpactPayload(impact, {
        actionType: "replace",
        affectedPage: impact.affected_page || replaced.old_page_name || "",
        oldImageName: replaced.old_image_name || oldImageName || "",
        newImageName: replaced.new_image_name || replacementFile.name || "",
      });

      notify.success(
        `Replaced ${replaced.old_image_name || "image"} with ${replaced.new_image_name || "new image"} and regenerated page methods.`
      );
    } catch (err) {
      console.error("Failed to replace uploaded image:", err);
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Failed to replace uploaded image.";
      notify.error(detail);
    } finally {
      setReplacingImage(false);
    }
  };

  const reviewImpactedTestcases = useCallback(() => {
    navigate("/input/story", {
      state: {
        projectName: projectName || activeProjectName,
        projectId: projectId || activeProjectId,
        flow: flowType,
      },
    });
  }, [activeProjectId, activeProjectName, flowType, navigate, projectId, projectName]);

  const continueWithFlow = useCallback(() => {
    navigate("/input/story", {
      state: {
        projectName: projectName || activeProjectName,
        projectId: projectId || activeProjectId,
        flow: flowType,
      },
    });
  }, [activeProjectId, activeProjectName, flowType, navigate, projectId, projectName]);

  const canProceed = isUrlFlow
    ? pageNames.length > 0 && !loadingIngestion && !loadingMethods
    : pageNames.length > 0 &&
      (!loadingIngestion && !loadingMethods) &&
      (ingestionSuccess || selectedFiles.length > 0);

  return (
    <div className={styles.imageUploadContainer}>
      <div
        className={`${styles.uploadBox} ${isMaintenanceMode ? styles.maintenanceUploadBox : ""}`}
      >
        <h2 className={styles.uploadTitle}>
          {isMaintenanceMode ? "Update Project Screens" : "Upload Designs"}
        </h2>
        <p className={styles.uploadSubtitle}>
          {isMaintenanceMode
            ? "Add new screens or maintain the existing library without interrupting the main workflow."
            : "Upload screenshots or visual designs of your application"}
        </p>

        <div className={`${styles.dropzone} ${isMaintenanceMode ? styles.maintenanceDropzone : ""}`}>
          <input
            id="file-upload"
            type="file"
            accept=".png,.jpg,.jpeg,.bmp,.gif,.webp,.zip"
            multiple
            style={{ display: "none" }}
            onChange={handleFileChange}
          />

          <i
            className={`fa-solid fa-cloud-arrow-up ${styles.uploadIcon} ${
              isMaintenanceMode ? styles.maintenanceUploadIcon : ""
            }`}
          ></i>

          <h3 className={styles.uploadText}>
            {isMaintenanceMode ? "Add new project screens" : "Upload Design Files"}
          </h3>

          <p className={styles.uploadInstructions}>
            {isMaintenanceMode
              ? "New uploads are added to this project. Replace or delete existing screens from the preview."
              : "Click the button below to select your files"}
          </p>

          <button
            onClick={() => document.getElementById("file-upload").click()}
            className={styles.selectFilesButton}
          >
            <i className={`fa-solid fa-upload ${styles.selectFilesButtonIcon}`}></i>
            <span className={styles.selectFilesButtonText}>
              {isMaintenanceMode ? "Add Screens" : "Select Files"}
            </span>
          </button>
        </div>

        {selectedFiles.length > 0 && (
          <div style={{ marginTop: "20px" }}>
            <ImagePreviewGrid
              files={selectedFiles}
              setFiles={setSelectedFiles}
              onDeleteImage={handleDeleteImage}
              onReplaceImage={handleReplaceImage}
              onPreviewImage={previewImageImpact}
              impactedSummary={impactedSummary}
              impactedItems={impactedItems}
              busy={deletingImages || replacingImage}
              allowMaintenance={isMaintenanceMode}
              allowPendingRemoval={!isMaintenanceMode}
            />
          </div>
        )}

        {selectedFiles.length > 0 && (
          <p className={styles.selectionHint}>
            {isMaintenanceMode
              ? "Open a screen preview to replace or delete it. New uploads are added without overwriting existing screens."
              : "Click any image to preview it. Pending images can be removed here before upload. To replace or delete an existing screen, use Image Update from the dashboard."}
          </p>
        )}

        {error && <p className={styles.errorText}>{error}</p>}

        {impactedSummary?.count > 0 && (
          <div className={styles.impactPanel}>
            <div className={styles.impactHeader}>
              <div>
                <h5 className={styles.impactTitle}>Impacted Testcases</h5>
                <p className={styles.impactSubtitle}>
                  {impactedSummary.count} testcase{impactedSummary.count === 1 ? "" : "s"} may be affected by{" "}
                  {impactedSummary.actionType === "delete" ? "deleting" : "replacing"}{" "}
                  <strong>{impactedSummary.oldImageName || "an image"}</strong>
                  {impactedSummary.actionType === "replace" ? (
                    <>
                      {" "}with <strong>{impactedSummary.newImageName || "a new image"}</strong>
                    </>
                  ) : null}
                  {Array.isArray(impactedSummary.affectedPages) && impactedSummary.affectedPages.length > 0
                    ? ` across ${impactedSummary.affectedPages.join(", ")}`
                    : impactedSummary.affectedPage
                    ? ` on page ${impactedSummary.affectedPage}`
                    : ""}.
                </p>
              </div>
              <button
                type="button"
                className={styles.impactDismissButton}
                onClick={clearImpactedTestcases}
              >
                Dismiss
              </button>
            </div>
            <div className={styles.impactList}>
              <div className={styles.impactRow}>
                <div style={{ width: "100%" }}>
                  <div className={styles.impactName}>This testcase is linked to the changed page and should be reviewed before the next run.</div>
                  <div className={styles.impactMeta}>
                    {isMaintenanceMode
                      ? "You can continue with the flow now or review the impacted testcase before the next run."
                      : "Open the testcase generation page to review and update the impacted testcase."}
                  </div>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.95rem" }}>
              <button
                type="button"
                className={styles.impactOpenButton}
                onClick={reviewImpactedTestcases}
              >
                Review Impacted Testcases
              </button>
            </div>
          </div>
        )}

        {ingestionSuccess && (
          <div className={styles.successMessage}>
            ✅ OCR extracted and stored in ChromaDB successfully.
          </div>
        )}

        {pageNames.length > 0 && (
          <div
            className={`${styles.availablePagesContainer} ${
              isMaintenanceMode ? styles.maintenancePagesContainer : ""
            }`}
          >
            <h5 className={styles.availablePagesTitle}>Available Pages:</h5>
            <ul className={styles.pageList}>
              {pageNames.map((name, idx) => (
                <li
                  key={idx}
                  className={styles.pageListItem}
                >
                  {name}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div
          className={`${styles.actionButtons} ${isMaintenanceMode ? styles.maintenanceActions : ""}`}
        >
          <button
            onClick={handleContinue}
            disabled={loadingIngestion}
            className={styles.uploadImagesButton}
          >
            {loadingIngestion ? (
              <div className={styles.spinner}></div>
            ) : isMaintenanceMode ? (
              "Upload New Screens"
            ) : (
              "Upload Images"
            )}
          </button>
          <button
            onClick={handleCancelUpload}
            disabled={loadingMethods || (!loadingIngestion && selectedFiles.length === 0)}
            className={styles.cancelUploadButton}
          >
            Cancel Upload
          </button>
          <button
            onClick={handleGenerateMethods}
            disabled={loadingMethods || deletingImages || replacingImage}
            className={styles.generateMethodsButton}
          >
            {loadingMethods ? (
              <div className={styles.spinner}></div>
            ) : isMaintenanceMode ? (
              "Refresh Page Methods"
            ) : (
              "Generate Page Methods"
            )}
          </button>
          {isMaintenanceMode && (
            <button
              onClick={continueWithFlow}
              disabled={loadingIngestion || loadingMethods || deletingImages || replacingImage}
              className={styles.continueFlowButton}
            >
              Continue with Flow
            </button>
          )}
        </div>
      </div>

      {!isMaintenanceMode && (
        <div className={styles.nextButtonContainer}>
          <button
            onClick={handleNext}
            disabled={!canProceed}
            className={styles.nextButton}
          >
            Next <i className="fa-solid fa-angle-right"></i>
          </button>
        </div>
      )}
    </div>
  );
};

export default ImageUpload;

