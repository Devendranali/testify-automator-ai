import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

const STORAGE_KEY = "auto-test-studio-state";
const STORAGE_VERSION = 2;

const createId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `img_${Date.now()}_${Math.random().toString(16).slice(2)}`;
};

const fileToDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });

const normalizeImages = (images = []) =>
  images.map((img) => ({
    ...img,
    preview: img.preview || img.dataUrl || "",
  }));

const stripImagePayload = (images = []) =>
  images.map(({ id, name, type, size }) => ({
    id,
    name,
    type,
    size,
  }));

const summarizeEnrichment = (data) => {
  if (!data || typeof data !== "object") return data;
  const summary = {
    status: data.status,
    message: data.message,
    auto_enrich_result: null,
    auto_enrich_job: data.auto_enrich_job ?? null,
  };
  const result = data.auto_enrich_result;
  if (result && typeof result === "object") {
    summary.auto_enrich_result = {
      strategy: result.strategy,
      results: Array.isArray(result.results) ? result.results : undefined,
      file: result.file ?? undefined,
    };
  }
  return summary;
};

const stripLargePayloads = (state) => {
  if (!state) return state;
  const next = { ...state };
  if (next.uploads?.images) {
    next.uploads = {
      ...next.uploads,
      images: stripImagePayload(next.uploads.images),
    };
  }
  if (next.enrichment?.fullTestData) {
    next.enrichment = {
      ...next.enrichment,
      fullTestData: summarizeEnrichment(next.enrichment.fullTestData),
    };
  }
  if (next.projectData) {
    const updated = {};
    Object.entries(next.projectData).forEach(([key, entry]) => {
      if (!entry) return;
      const uploads = entry.uploads || {};
      const enrichment = entry.enrichment || {};
      updated[key] = {
        ...entry,
        uploads: {
          ...uploads,
          images: stripImagePayload(uploads.images || []),
        },
        enrichment: {
          ...enrichment,
          fullTestData: summarizeEnrichment(enrichment.fullTestData),
        },
      };
    });
    next.projectData = updated;
  }
  return next;
};

const createSafeStorage = () => {
  const base = localStorage;
  return {
    getItem: (name) => base.getItem(name),
    removeItem: (name) => base.removeItem(name),
    setItem: (name, value) => {
      try {
        base.setItem(name, value);
      } catch (err) {
        try {
          const parsed = JSON.parse(value);
          const pruned = stripLargePayloads(parsed);
          base.setItem(name, JSON.stringify(pruned));
        } catch (innerErr) {
          base.removeItem(name);
        }
      }
    },
  };
};
const normalizeProjectName = (value) => (value || "").trim().toLowerCase();
const buildProjectKey = (id, name) => {
  if (id !== undefined && id !== null && id !== "") {
    return `id:${String(id)}`;
  }
  const normalized = normalizeProjectName(name);
  return normalized ? `name:${normalized}` : "";
};

const buildImageKey = (name, size, type) => {
  const normalizedName = String(name || "").trim().toLowerCase();
  const normalizedSize = Number.isFinite(Number(size)) ? Number(size) : 0;
  const normalizedType = String(type || "").trim().toLowerCase();
  return `${normalizedName}::${normalizedSize}::${normalizedType}`;
};

const deriveImpactedTestcaseName = (item) => {
  const scriptPath = String(item?.script_path || "").trim();
  if (scriptPath) {
    const filename = scriptPath.split("/").filter(Boolean).pop() || "";
    if (filename) {
      return filename.replace(/\.py$/i, "");
    }
  }
  const testName = String(item?.test_name || "").trim();
  if (testName) {
    return testName;
  }
  const displayName = String(item?.display_name || "").trim();
  if (displayName) {
    return displayName;
  }
  return String(item?.case_uuid || "").trim() || "Impacted testcase";
};

const dedupeImpactedTestcases = (items = []) => {
  const buckets = new Map();
  (Array.isArray(items) ? items : []).forEach((item) => {
    if (!item || typeof item !== "object") {
      return;
    }
    const key = (
      String(item.script_path || "").trim() ||
      String(item.runner_script_path || "").trim() ||
      String(item.test_name || "").trim() ||
      String(item.display_name || "").trim() ||
      String(item.case_uuid || "").trim()
    ).toLowerCase();
    if (!key) {
      return;
    }
    if (!buckets.has(key)) {
      buckets.set(key, { ...item });
      return;
    }
    const existing = buckets.get(key);
    buckets.set(key, {
      ...existing,
      matched_via: Array.from(new Set([...(existing.matched_via || []), ...(item.matched_via || [])])),
      where_impacted: Array.from(
        new Set([...(existing.where_impacted || []), ...(item.where_impacted || [])])
      ),
      impacted_page_modules: Array.from(
        new Set([...(existing.impacted_page_modules || []), ...(item.impacted_page_modules || [])])
      ),
    });
  });

  return Array.from(buckets.values()).map((item) => ({
    ...item,
    display_name: deriveImpactedTestcaseName(item),
  }));
};

const initialState = {
  project: {
    activeProjectId: null,
    activeProjectName: "",
  },
  projectData: {},
  navigation: {
    inputFlow: null,
    inputStartFlow: null,
  },
  uploads: {
    images: [],
    pageNames: [],
  },
    testCases: {
      items: [],
      userStoriesInput: "",
      selectedTestCaseId: "",
      selectedTestCaseType: "",
      selectedTestCaseScriptPath: "",
      selectedTestCaseRunnerScriptPath: "",
      selectedTestTypes: [],
      jiraStoryObjects: [],
      impactedSummary: null,
      impactedItems: [],
    },
  enrichment: {
    url: "",
    fullTestData: null,
  },
  execution: {
    executionFilters: {
      ui: { regression: false, functional: false },
      accessibility: { regression: false, functional: false },
      security: { regression: false, functional: false },
    },
    categorySelections: {
      accessibility: false,
      security: false,
    },
    useUpdatedExecutionByCategory: {
      ui: false,
      accessibility: false,
      security: false,
    },
    tagCounts: {},
    plannedTests: [],
    plannedTestsProjectId: null,
    plannedTestsProjectName: "",
    metrics: null,
    acResults: null,
    lastExecutionStatus: null,
    lastExecutionError: "",
    parallelExecution: false,
  },
  settings: {
    framework: "Playwright",
    language: "Python",
    startFlow: "ocr",
  },
};

const useAppStore = create(
  persist(
    (set, get) => ({
      ...initialState,
      setActiveProject: ({ id, name }) =>
        set((state) => {
          const prevId = state.project.activeProjectId;
          const prevName = state.project.activeProjectName;
          const nextId = id ?? prevId;
          const nextName = name ?? prevName;
          const prevKey = buildProjectKey(prevId, prevName);
          const nextKey = buildProjectKey(nextId, nextName);
          const changed = prevKey !== nextKey && (prevKey || nextKey);

          if (!changed) {
            return {
              project: {
                ...state.project,
                activeProjectId: nextId,
                activeProjectName: nextName,
              },
            };
          }

          const projectData = { ...(state.projectData || {}) };
          if (prevKey) {
            projectData[prevKey] = {
              uploads: state.uploads,
              testCases: state.testCases,
              enrichment: state.enrichment,
              execution: state.execution,
            };
          }

          const nextData = nextKey ? projectData[nextKey] : null;
          return {
            uploads: nextData?.uploads || initialState.uploads,
            testCases: nextData?.testCases || initialState.testCases,
            enrichment: nextData?.enrichment || initialState.enrichment,
            execution: nextData?.execution || initialState.execution,
            navigation: state.navigation,
            project: {
              ...state.project,
              activeProjectId: nextId,
              activeProjectName: nextName,
            },
            projectData,
            settings: state.settings,
          };
        }),
      clearActiveProject: () =>
        set((state) => ({
          project: { ...state.project, activeProjectId: null, activeProjectName: "" },
        })),
      setInputFlow: (flow) =>
        set((state) => ({
          navigation: { ...state.navigation, inputFlow: flow || null },
        })),
      setInputStartFlow: (flow) =>
        set((state) => ({
          navigation: { ...state.navigation, inputStartFlow: flow || null },
        })),
      clearInputStartFlow: () =>
        set((state) => ({
          navigation: { ...state.navigation, inputStartFlow: null },
        })),
      addUploadedImages: async (files = []) => {
        const normalized = Array.from(files);
        if (!normalized.length) {
          return { addedCount: 0, skippedCount: 0 };
        }

        const existing = get()?.uploads?.images || [];
        const existingKeys = new Set(
          existing.map((img) => buildImageKey(img?.name, img?.size, img?.type)),
        );

        const seenIncoming = new Set();
        const uniqueIncoming = [];
        let skippedCount = 0;

        normalized.forEach((file) => {
          const key = buildImageKey(file?.name, file?.size, file?.type);
          if (!key || key === "::0::") {
            uniqueIncoming.push(file);
            return;
          }
          if (existingKeys.has(key) || seenIncoming.has(key)) {
            skippedCount += 1;
            return;
          }
          seenIncoming.add(key);
          uniqueIncoming.push(file);
        });

        if (!uniqueIncoming.length) {
          return { addedCount: 0, skippedCount };
        }

        const processed = await Promise.all(
          uniqueIncoming.map(async (file) => {
            const dataUrl = await fileToDataUrl(file);
            return {
              id: createId(),
              name: file.name,
              type: file.type,
              size: file.size,
              dataUrl,
              preview: dataUrl,
            };
          }),
        );
        set((state) => ({
          uploads: {
            ...state.uploads,
            images: [...state.uploads.images, ...processed],
          },
        }));
        return { addedCount: processed.length, skippedCount };
      },
      setUploadedImages: (images) =>
        set((state) => ({
          uploads: {
            ...state.uploads,
            images: normalizeImages(images || []),
          },
        })),
      removeUploadedImage: (id) =>
        set((state) => ({
          uploads: {
            ...state.uploads,
            images: state.uploads.images.filter((img) => img.id !== id),
          },
        })),
      clearUploadedImages: () =>
        set((state) => ({
          uploads: { ...state.uploads, images: [] },
        })),
      setPageNames: (names) =>
        set((state) => ({
          uploads: { ...state.uploads, pageNames: Array.isArray(names) ? names : [] },
        })),
      setTestCases: (items) =>
        set((state) => ({
          testCases: { ...state.testCases, items: Array.isArray(items) ? items : [] },
        })),
      setUserStoriesInput: (value) =>
        set((state) => ({
          testCases: { ...state.testCases, userStoriesInput: value || "" },
        })),
      setSelectedTestCaseId: (value) =>
        set((state) => ({
          testCases: { ...state.testCases, selectedTestCaseId: value || "" },
        })),
      setSelectedTestCaseType: (value) =>
        set((state) => ({
          testCases: { ...state.testCases, selectedTestCaseType: value || "" },
        })),
      setSelectedTestCaseScriptPath: (value) =>
        set((state) => ({
          testCases: { ...state.testCases, selectedTestCaseScriptPath: value || "" },
        })),
      setSelectedTestCaseRunnerScriptPath: (value) =>
        set((state) => ({
          testCases: { ...state.testCases, selectedTestCaseRunnerScriptPath: value || "" },
        })),
      clearSelectedTestCase: () =>
        set((state) => ({
          testCases: {
            ...state.testCases,
            selectedTestCaseId: "",
            selectedTestCaseType: "",
            selectedTestCaseScriptPath: "",
            selectedTestCaseRunnerScriptPath: "",
          },
        })),
      setSelectedTestTypes: (values) =>
        set((state) => ({
          testCases: { ...state.testCases, selectedTestTypes: values || [] },
        })),
      setJiraStoryObjects: (items) =>
        set((state) => ({
          testCases: { ...state.testCases, jiraStoryObjects: Array.isArray(items) ? items : [] },
        })),
      setImpactedTestcases: (payload) =>
        set((state) => {
          const impactedItems = dedupeImpactedTestcases(payload?.items);
          const summary = payload?.summary
            ? {
                ...payload.summary,
                count: impactedItems.length,
              }
            : null;
          return {
            testCases: {
              ...state.testCases,
              impactedSummary: summary,
              impactedItems,
            },
          };
        }),
      clearImpactedTestcases: () =>
        set((state) => ({
          testCases: {
            ...state.testCases,
            impactedSummary: null,
            impactedItems: [],
          },
        })),
      setEnrichmentUrl: (url) =>
        set((state) => ({
          enrichment: { ...state.enrichment, url: url || "" },
        })),
      setEnrichmentResult: (data) =>
        set((state) => ({
          enrichment: { ...state.enrichment, fullTestData: data || null },
        })),
      clearEnrichmentResult: () =>
        set((state) => ({
          enrichment: { ...state.enrichment, fullTestData: null },
        })),
      setExecutionFilters: (filters) =>
        set((state) => ({
          execution: { ...state.execution, executionFilters: filters },
        })),
      setCategorySelections: (selections) =>
        set((state) => ({
          execution: { ...state.execution, categorySelections: selections },
        })),
      setUseUpdatedExecutionByCategory: (value) =>
        set((state) => ({
          execution: { ...state.execution, useUpdatedExecutionByCategory: value },
        })),
      setTagCounts: (counts) =>
        set((state) => ({
          execution: { ...state.execution, tagCounts: counts || {} },
        })),
      setPlannedTests: (tests) =>
        set((state) => ({
          execution: { ...state.execution, plannedTests: Array.isArray(tests) ? tests : [] },
        })),
      setPlannedTestsMeta: ({ projectId, projectName }) =>
        set((state) => ({
          execution: {
            ...state.execution,
            plannedTestsProjectId:
              projectId !== undefined ? projectId : state.execution.plannedTestsProjectId,
            plannedTestsProjectName:
              projectName !== undefined ? projectName : state.execution.plannedTestsProjectName,
          },
        })),
      setMetrics: (metrics) =>
        set((state) => ({
          execution: { ...state.execution, metrics: metrics || null },
        })),
      setAcResults: (acResults) =>
        set((state) => ({
          execution: { ...state.execution, acResults: acResults || null },
        })),
      setExecutionStatus: ({ status, error }) =>
        set((state) => ({
          execution: {
            ...state.execution,
            lastExecutionStatus: status ?? state.execution.lastExecutionStatus,
            lastExecutionError: error ?? state.execution.lastExecutionError,
          },
        })),
      setParallelExecution: (value) =>
        set((state) => ({
          execution: { ...state.execution, parallelExecution: !!value },
        })),
      setSettings: (settings) =>
        set((state) => ({
          settings: { ...state.settings, ...(settings || {}) },
        })),
      resetProjectState: () =>
        set((state) => ({
          uploads: initialState.uploads,
          testCases: initialState.testCases,
          enrichment: initialState.enrichment,
          execution: initialState.execution,
          navigation: state.navigation,
          project: state.project,
          settings: state.settings,
        })),
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(createSafeStorage),
      version: STORAGE_VERSION,
      partialize: (state) => ({
        project: state.project,
        projectData: state.projectData,
        navigation: state.navigation,
        uploads: {
          images: stripImagePayload(state.uploads.images),
          pageNames: state.uploads.pageNames,
        },
        testCases: state.testCases,
        enrichment: {
          ...state.enrichment,
          fullTestData: summarizeEnrichment(state.enrichment.fullTestData),
        },
        execution: state.execution,
        settings: state.settings,
      }),
      migrate: (persistedState) => stripLargePayloads(persistedState),
      onRehydrateStorage: () => (state) => {
        if (state?.uploads?.images) {
          state.uploads.images = normalizeImages(state.uploads.images);
        }
        if (state?.projectData) {
          Object.values(state.projectData).forEach((entry) => {
            if (entry?.uploads?.images) {
              entry.uploads.images = normalizeImages(entry.uploads.images);
            }
          });
        }
      },
    }
  )
);

export default useAppStore;

