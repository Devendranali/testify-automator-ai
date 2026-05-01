import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import styles from "../css/ImageHandles.module.css";

const ImagePreviewGrid = ({
  files,
  setFiles,
  onDeleteImage = null,
  onReplaceImage = null,
  onPreviewImage = null,
  impactedSummary = null,
  impactedItems = [],
  busy = false,
  allowMaintenance = true,
  allowPendingRemoval = false,
}) => {
  const dragItem = useRef(null);
  const dragOverItem = useRef(null);
  const replaceInputRef = useRef(null);
  const [activeIndex, setActiveIndex] = useState(null);
  const [confirmAction, setConfirmAction] = useState("");
  const [pendingReplacementFile, setPendingReplacementFile] = useState(null);
  const [loadingImpact, setLoadingImpact] = useState(false);

  const activeFile = useMemo(
    () => (activeIndex === null ? null : files[activeIndex] || null),
    [activeIndex, files]
  );

  const activeImpactItems = useMemo(() => {
    if (!activeFile || !Array.isArray(impactedItems) || impactedItems.length === 0) {
      return [];
    }
    const activeName = String(activeFile.name || "").trim().toLowerCase();
    const summaryImage = String(impactedSummary?.oldImageName || "").trim().toLowerCase();
    if (!activeName || !summaryImage || activeName !== summaryImage) {
      return [];
    }
    if (
      confirmAction === "replace" &&
      pendingReplacementFile?.name &&
      impactedSummary?.newImageName &&
      String(pendingReplacementFile.name).trim().toLowerCase() !==
        String(impactedSummary.newImageName || "").trim().toLowerCase()
    ) {
      return [];
    }
    return impactedItems;
  }, [activeFile, impactedItems, impactedSummary, confirmAction, pendingReplacementFile]);

  const activeImpactSummary = useMemo(() => {
    if (!activeFile || !impactedSummary) {
      return null;
    }
    const activeName = String(activeFile.name || "").trim().toLowerCase();
    const summaryImage = String(impactedSummary.oldImageName || "").trim().toLowerCase();
    if (!activeName || !summaryImage || activeName !== summaryImage) {
      return null;
    }
    if (
      confirmAction === "replace" &&
      pendingReplacementFile?.name &&
      impactedSummary?.newImageName &&
      String(pendingReplacementFile.name).trim().toLowerCase() !==
        String(impactedSummary.newImageName || "").trim().toLowerCase()
    ) {
      return null;
    }
    return impactedSummary;
  }, [activeFile, impactedSummary, confirmAction, pendingReplacementFile]);

  const canRemovePending = !activeFile?.persisted && allowPendingRemoval && typeof onDeleteImage === "function";
  const canMaintainPersisted = allowMaintenance && activeFile?.persisted;
  const canNavigate = files.length > 1;

  const resetPreviewState = useCallback(() => {
    setConfirmAction("");
    setPendingReplacementFile(null);
    setLoadingImpact(false);
  }, []);

  const loadPreviewImpact = useCallback((index, action = null, replacementFile = null) => {
    if (typeof onPreviewImage !== "function") {
      setLoadingImpact(false);
      return;
    }
    setLoadingImpact(true);
    Promise.resolve(onPreviewImage(files[index] || null, action, replacementFile)).finally(() => {
      setLoadingImpact(false);
    });
  }, [files, onPreviewImage]);

  const handleDragStart = (index) => {
    dragItem.current = index;
  };

  const handleDragEnter = (index) => {
    dragOverItem.current = index;
  };

  const handleDragEnd = () => {
    const fromIndex = dragItem.current;
    const toIndex = dragOverItem.current;
    if (fromIndex === null || toIndex === null || fromIndex === toIndex) {
      dragItem.current = null;
      dragOverItem.current = null;
      return;
    }
    const newList = [...files];
    const dragged = newList[fromIndex];
    newList.splice(fromIndex, 1);
    newList.splice(toIndex, 0, dragged);
    dragItem.current = null;
    dragOverItem.current = null;
    setFiles(newList);
  };

  const openPreview = (index) => {
    if (dragItem.current !== null || dragOverItem.current !== null) {
      return;
    }
    setActiveIndex(index);
    resetPreviewState();
    loadPreviewImpact(index);
  };

  const closePreview = useCallback(() => {
    setActiveIndex(null);
    resetPreviewState();
  }, [resetPreviewState]);

  const navigatePreview = useCallback((direction) => {
    if (!canNavigate || activeIndex === null) {
      return;
    }
    const nextIndex = (activeIndex + direction + files.length) % files.length;
    setActiveIndex(nextIndex);
    resetPreviewState();
    loadPreviewImpact(nextIndex);
  }, [activeIndex, canNavigate, files.length, loadPreviewImpact, resetPreviewState]);

  useEffect(() => {
    if (activeIndex === null) {
      return undefined;
    }
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        closePreview();
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        navigatePreview(-1);
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        navigatePreview(1);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activeIndex, closePreview, navigatePreview]);

  const handleDelete = () => {
    if (!activeFile || typeof onDeleteImage !== "function") {
      return;
    }
    if (!activeFile?.persisted) {
      onDeleteImage(activeFile);
      closePreview();
      return;
    }
    setConfirmAction("delete");
  };

  const handleConfirmDelete = () => {
    if (!activeFile || typeof onDeleteImage !== "function") {
      return;
    }
    onDeleteImage(activeFile);
    closePreview();
  };

  const handlePickReplacement = () => {
    if (!activeFile || typeof onReplaceImage !== "function") {
      return;
    }
    replaceInputRef.current?.click();
  };

  const handleReplacementSelected = async (e) => {
    const replacementFile = e.target.files?.[0];
    e.target.value = "";
    if (!replacementFile || !activeFile || typeof onReplaceImage !== "function") {
      return;
    }
    setPendingReplacementFile(replacementFile);
    setConfirmAction("replace");
    if (typeof onPreviewImage === "function") {
      setLoadingImpact(true);
      try {
        await onPreviewImage(activeFile, "replace", replacementFile);
      } finally {
        setLoadingImpact(false);
      }
    }
  };

  const handleConfirmReplace = () => {
    if (!activeFile || !pendingReplacementFile || typeof onReplaceImage !== "function") {
      return;
    }
    onReplaceImage(activeFile, pendingReplacementFile, { skipPreview: true });
    closePreview();
  };

  return (
    <>
      <div className={styles.imageDragDropContainer}>
        {files.map((file, idx) => (
          <button
            key={file.name + idx}
            type="button"
            draggable
            onDragStart={() => handleDragStart(idx)}
            onDragEnter={() => handleDragEnter(idx)}
            onDragEnd={handleDragEnd}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => openPreview(idx)}
            className={styles.imageCard}
          >
            {file.preview ? (
              <img src={file.preview} alt={file.name} className={styles.imagePreview} />
            ) : (
              <div className={styles.imagePreview}>
                <i className="fa-regular fa-image"></i>
              </div>
            )}
            <div className={styles.imageName}>{file.name}</div>
            <div className={styles.imageIndex}>{idx + 1}</div>
          </button>
        ))}
      </div>

      {activeFile ? (
        <div className={styles.previewOverlay} onClick={closePreview} role="presentation">
          <div className={styles.previewModal} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <button type="button" className={styles.previewClose} onClick={closePreview}>
              x
            </button>
            {canNavigate ? (
              <>
                <button
                  type="button"
                  className={`${styles.previewNav} ${styles.previewNavLeft}`}
                  onClick={() => navigatePreview(-1)}
                  aria-label="Show previous image"
                >
                  <i className="fa-solid fa-chevron-left"></i>
                </button>
                <button
                  type="button"
                  className={`${styles.previewNav} ${styles.previewNavRight}`}
                  onClick={() => navigatePreview(1)}
                  aria-label="Show next image"
                >
                  <i className="fa-solid fa-chevron-right"></i>
                </button>
              </>
            ) : null}
            <div className={styles.previewImageFrame}>
              {activeFile.preview ? (
                <img src={activeFile.preview} alt={activeFile.name} className={styles.previewImage} />
              ) : (
                <div className={styles.previewPlaceholder}>
                  <i className="fa-regular fa-image"></i>
                </div>
              )}
            </div>
            <div className={styles.previewMeta}>
              <div className={styles.previewName}>{activeFile.name}</div>
              {canNavigate ? (
                <div className={styles.previewCounter}>
                  {activeIndex + 1} / {files.length}
                </div>
              ) : null}
              <div className={styles.previewHint}>
                {canMaintainPersisted
                  ? "Use the actions below to replace or delete this image."
                  : canRemovePending
                  ? "Use the action below to remove this image from pending uploads."
                  : "Preview only in workflow mode. Use Image Update from the dashboard to replace or delete this screen."}
              </div>
            </div>
            {canMaintainPersisted ? (
              <div className={styles.previewImpactPanel}>
                <div className={styles.previewImpactHeader}>
                  <div>
                    <div className={styles.previewImpactTitle}>Impacted Testcases</div>
                    <div className={styles.previewImpactSubtitle}>
                      {loadingImpact
                        ? "Checking impacted testcases for this image."
                        : confirmAction === "replace" && pendingReplacementFile
                        ? `Review impacted testcases before replacing ${activeFile.name} with ${pendingReplacementFile.name}.`
                        : `Review impacted testcases before deleting or replacing ${activeFile.name}.`}
                    </div>
                  </div>
                  {activeImpactSummary ? (
                    <div className={styles.previewImpactBadge}>
                      {Number(activeImpactSummary.count) || 0} affected
                    </div>
                  ) : null}
                </div>
                {loadingImpact ? (
                  <div className={styles.previewImpactEmpty}>Loading impacted testcases...</div>
                ) : activeImpactItems.length > 0 ? (
                  <div className={styles.previewImpactList}>
                    {activeImpactItems.map((item, index) => (
                      <div
                        key={
                          item?.case_uuid ||
                          item?.script_path ||
                          item?.runner_script_path ||
                          item?.test_name ||
                          `${item?.display_name || "impact"}-${index}`
                        }
                        className={styles.previewImpactItem}
                      >
                        <div className={styles.previewImpactItemName}>
                          {item?.display_name || item?.test_name || "Unnamed testcase"}
                        </div>
                        <div className={styles.previewImpactItemMeta}>
                          {[item?.reason, item?.script_path || item?.runner_script_path]
                            .filter(Boolean)
                            .join(" | ")}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className={styles.previewImpactEmpty}>
                    No impacted testcases were found for this image.
                  </div>
                )}
              </div>
            ) : null}
            {canMaintainPersisted || canRemovePending ? (
              <div className={styles.previewActions}>
                {confirmAction === "delete" && canMaintainPersisted ? (
                  <>
                    <button
                      type="button"
                      className={styles.previewCancel}
                      onClick={() => setConfirmAction("")}
                      disabled={busy}
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      className={styles.previewDelete}
                      onClick={handleConfirmDelete}
                      disabled={busy || typeof onDeleteImage !== "function"}
                    >
                      Confirm Delete
                    </button>
                  </>
                ) : confirmAction === "replace" && canMaintainPersisted ? (
                  <>
                    <button
                      type="button"
                      className={styles.previewCancel}
                      onClick={() => {
                        setConfirmAction("");
                        setPendingReplacementFile(null);
                      }}
                      disabled={busy}
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      className={styles.previewReplace}
                      onClick={handleConfirmReplace}
                      disabled={busy || !pendingReplacementFile || typeof onReplaceImage !== "function"}
                    >
                      Confirm Replace
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      type="button"
                      className={styles.previewDelete}
                      onClick={handleDelete}
                      disabled={busy || typeof onDeleteImage !== "function"}
                    >
                      {activeFile?.persisted ? "Delete" : "Remove"}
                    </button>
                    {canMaintainPersisted ? (
                      <button
                        type="button"
                        className={styles.previewReplace}
                        onClick={handlePickReplacement}
                        disabled={busy || typeof onReplaceImage !== "function"}
                      >
                        Replace
                      </button>
                    ) : null}
                  </>
                )}
              </div>
            ) : (
              <div className={styles.previewReadOnlyBadge}>Workflow preview only</div>
            )}
            <input
              ref={replaceInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.bmp,.gif,.webp"
              style={{ display: "none" }}
              onChange={handleReplacementSelected}
            />
          </div>
        </div>
      ) : null}
    </>
  );
};

export default ImagePreviewGrid;
