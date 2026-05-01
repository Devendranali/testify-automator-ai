import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import * as XLSX from "xlsx";
import styles from "../css/StoryInput.module.css";
import API_BASE_URL from "../config";
import useAppStore from "../state/useAppStore";
import useScopedToast from "../hooks/useScopedToast";
import { requireBearerAuthHeaders } from "../utils/auth";

const TEST_TYPE_OPTIONS = [
  { label: "UI Tests", value: "ui" },
  { label: "Security Tests", value: "security" },
  { label: "Accessibility Tests", value: "accessibility" },
];

const parseTagsInput = (value) =>
  (value || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

const deriveRunnerScriptPath = (testCase) => {
  const scriptPath = testCase?.script_path || "";
  if (!scriptPath) {
    return "";
  }
  const segments = scriptPath.split("/").filter(Boolean);
  if (!segments.length) {
    return "";
  }
  const filename = segments[segments.length - 1];
  const match = filename.match(/^test_(.+)\.py$/);
  if (!match) {
    return "";
  }
  const slug = match[1];
  const category = (testCase?.test_type || "ui").toLowerCase();
  return `tests/${category}_scripts/${category}_script_${slug}.py`;
};

const StoryInput = ({ onBack, onNext, projectName, projectId }) => {
  const notify = useScopedToast();
  const navigate = useNavigate();
  const userStoriesInput = useAppStore((state) => state.testCases.userStoriesInput);
  const setUserStoriesInput = useAppStore((state) => state.setUserStoriesInput);
  const selectedTestTypes = useAppStore((state) => state.testCases.selectedTestTypes);
  const setSelectedTestTypes = useAppStore((state) => state.setSelectedTestTypes);
  const jiraStoryObjects = useAppStore((state) => state.testCases.jiraStoryObjects);
  const setJiraStoryObjects = useAppStore((state) => state.setJiraStoryObjects);
  const impactedSummary = useAppStore((state) => state.testCases.impactedSummary);
  const impactedItems = useAppStore((state) => state.testCases.impactedItems);
  const clearImpactedTestcases = useAppStore((state) => state.clearImpactedTestcases);
  const testCases = useAppStore((state) => state.testCases.items);
  const setTestCases = useAppStore((state) => state.setTestCases);
  const selectedTestCaseId = useAppStore((state) => state.testCases.selectedTestCaseId);
  const selectedTestCaseType = useAppStore((state) => state.testCases.selectedTestCaseType);
  const selectedTestCaseScriptPath = useAppStore(
    (state) => state.testCases.selectedTestCaseScriptPath
  );
  const setSelectedTestCaseId = useAppStore((state) => state.setSelectedTestCaseId);
  const setSelectedTestCaseType = useAppStore((state) => state.setSelectedTestCaseType);
  const setSelectedTestCaseScriptPath = useAppStore(
    (state) => state.setSelectedTestCaseScriptPath
  );
  const clearSelectedTestCase = useAppStore((state) => state.clearSelectedTestCase);
  const selectedTestCaseRunnerScriptPath = useAppStore(
    (state) => state.testCases.selectedTestCaseRunnerScriptPath
  );
  const setSelectedTestCaseRunnerScriptPath = useAppStore(
    (state) => state.setSelectedTestCaseRunnerScriptPath
  );
  const prevStoryCountRef = useRef(0);
  const storyInputRef = useRef(null);
  const normalizedTestCases = useMemo(() => {
    const byKey = new Map();
    (testCases || []).forEach((tc) => {
      const baseKey =
        (tc.script_path || "").trim() ||
        (tc.test_name || "").trim() ||
        (tc.display_name || "").trim() ||
        (tc.case_uuid || tc.id || "").toString().trim();
      if (!baseKey) {
        return;
      }
      const key = `${(tc.test_type || "ui").toLowerCase()}::${baseKey}`.toLowerCase();
      const existing = byKey.get(key);
      if (!existing) {
        byKey.set(key, tc);
        return;
      }
      const existingTime = new Date(existing.updated_at).getTime();
      const nextTime = new Date(tc.updated_at).getTime();
      if (Number.isFinite(nextTime) && (!Number.isFinite(existingTime) || nextTime > existingTime)) {
        byKey.set(key, tc);
      }
    });
    return Array.from(byKey.values());
  }, [testCases]);

  const storyGroups = useMemo(() => {
    const map = new Map();
    normalizedTestCases.forEach((tc) => {
      const story = (tc.user_story || "").trim() || "Untitled Story";
      if (!map.has(story)) {
        map.set(story, []);
      }
      map.get(story).push(tc);
    });
    const groups = Array.from(map.entries()).map(([story, cases]) => {
      const sortKey = cases.reduce((acc, tc) => {
        const time = new Date(tc.updated_at).getTime();
        return Number.isFinite(time) ? Math.min(acc, time) : acc;
      }, Infinity);
      return { story, cases, sortKey: Number.isFinite(sortKey) ? sortKey : Date.now() };
    });
    groups.sort((a, b) => a.sortKey - b.sortKey);
    return groups;
  }, [normalizedTestCases]);

  useEffect(() => {
    prevStoryCountRef.current = storyGroups.length;
  }, [storyGroups.length]);

  const getCasesByType = useCallback((cases) => {
    const map = {};
    const seenByType = {};
    (cases || []).forEach((tc) => {
      const type = (tc.test_type || "ui").toLowerCase();
      const uniqueKey =
        (tc.script_path || "").trim() ||
        (tc.display_name || "").trim() ||
        (tc.test_name || "").trim() ||
        tc.case_uuid;
      if (!map[type]) {
        map[type] = [];
        seenByType[type] = new Set();
      }
      if (uniqueKey && seenByType[type].has(uniqueKey)) {
        return;
      }
      if (uniqueKey) {
        seenByType[type].add(uniqueKey);
      }
      map[type].push(tc);
    });
    return map;
  }, []);
  const setActiveProject = useAppStore((state) => state.setActiveProject);
  const activeProjectId = useAppStore((state) => state.project.activeProjectId);
  const activeProjectName = useAppStore((state) => state.project.activeProjectName);
  const [selectedFile, setSelectedFile] = useState(null);

  const [loadingGeneration, setLoadingGeneration] = useState(false);
  const [loadingJira, setLoadingJira] = useState(false);
  const [loadingExcel, setLoadingExcel] = useState(false);
  const [error, setError] = useState("");
  const [impactPage, setImpactPage] = useState(1);
  const [testCaseFormName, setTestCaseFormName] = useState("");
  const [testCaseFormTags, setTestCaseFormTags] = useState("");
  const [testCaseFormPriority, setTestCaseFormPriority] = useState("Low");
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");

  const [showJiraModal, setShowJiraModal] = useState(false);
  const [jiraBaseUrl, setJiraBaseUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraApiToken, setJiraApiToken] = useState("");
  const [jiraProjectKey, setJiraProjectKey] = useState("");
  const [jiraIssueKey, setJiraIssueKey] = useState("");
  const [jiraIssueKeys] = useState("");
  const [jiraJql, setJiraJql] = useState("");
  const [showGitModal, setShowGitModal] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [branchName, setBranchName] = useState("main");
  const [commitMessage, setCommitMessage] = useState("Add automated test cases");
  const [isPushingToGit, setIsPushingToGit] = useState(false);
  const impactPageSize = 5;
  const impactPageCount = Math.max(1, Math.ceil((impactedItems?.length || 0) / impactPageSize));
  const normalizedImpactPage = Math.min(impactPage, impactPageCount);
  const pagedImpactedItems = (impactedItems || []).slice(
    (normalizedImpactPage - 1) * impactPageSize,
    normalizedImpactPage * impactPageSize
  );
  const handleTestTypeChange = (e) => {
    const { value, checked } = e.target;
    if (checked) {
      setSelectedTestTypes([...selectedTestTypes, value]);
    } else {
      setSelectedTestTypes(selectedTestTypes.filter((type) => type !== value));
    }
  };


  const handleCreateNewTestCase = () => {
    clearSelectedTestCase();
    setUserStoriesInput("");
    setTestCaseFormName("");
    setTestCaseFormTags("");
    setTestCaseFormPriority("Low");
    setError("");
  };

  const handleSelectTestCaseRow = (testCase) => {
    const identifier = testCase?.case_uuid || testCase?.id;
    if (!identifier) {
      return;
    }
    const normalizedType = (testCase?.test_type || "ui").toLowerCase();
    if (selectedTestCaseId === identifier && selectedTestCaseType === normalizedType) {
      clearSelectedTestCase();
      return;
    }
    setSelectedTestCaseId(identifier);
    setSelectedTestCaseType(normalizedType);
    setSelectedTestCaseScriptPath(testCase?.script_path || "");
    setSelectedTestCaseRunnerScriptPath(
      testCase?.runner_script_path || deriveRunnerScriptPath(testCase) || ""
    );
  };

  const handleOpenImpactedTestcase = useCallback(
    (item) => {
      if (!item) {
        return;
      }
      handleSelectTestCaseRow({
        case_uuid: item.case_uuid,
        id: item.id,
        test_type: item.test_type,
        script_path: item.script_path,
        runner_script_path: item.runner_script_path,
      });
      navigate("/input/story", { replace: true });
    },
    [handleSelectTestCaseRow, navigate]
  );

  const handleOpenImpactedTestFile = useCallback(
    (item) => {
      const filePath = item?.runner_script_path || deriveRunnerScriptPath(item) || item?.script_path;
      const resolvedProjectId = projectId || activeProjectId;
      const resolvedProjectName = projectName || activeProjectName;
      if (!filePath || (!resolvedProjectId && !resolvedProjectName)) {
        return;
      }

      const params = new URLSearchParams();
      if (resolvedProjectId !== undefined && resolvedProjectId !== null && resolvedProjectId !== "") {
        params.set("projectId", String(resolvedProjectId));
      }
      if (resolvedProjectName) {
        params.set("projectName", resolvedProjectName);
      }
      params.set("path", filePath);

      navigate(
        {
          pathname: "/editor",
          search: `?${params.toString()}`,
        },
        {
          state: {
            openFile: {
              projectId: resolvedProjectId,
              projectName: resolvedProjectName,
              path: filePath,
            },
          },
        }
      );
    },
    [activeProjectId, activeProjectName, navigate, projectId, projectName]
  );

  useEffect(() => {
    if (projectId || projectName) {
      setActiveProject({
        id: projectId ? String(projectId) : null,
        name: projectName || null,
      });
    }
  }, [projectId, projectName, setActiveProject]);

  useEffect(() => {
    setImpactPage(1);
  }, [impactedItems]);

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

  const collectGenerationResults = useCallback(async () => {
    const activeId = await ensureActiveProject();
    if (!activeId) {
      throw new Error("No active project. Please start a project first.");
    }
    const targetTestTypes = selectedTestCaseType
      ? [selectedTestCaseType]
      : selectedTestTypes;
    const targetScriptPathValue =
      selectedTestCaseId && selectedTestCaseScriptPath ? selectedTestCaseScriptPath : "";
    const targetRunnerScriptPathValue =
      selectedTestCaseId && selectedTestCaseRunnerScriptPath
        ? selectedTestCaseRunnerScriptPath
        : "";

    if (!targetTestTypes.length) {
      throw new Error("Select at least one test type.");
    }

    const token = localStorage.getItem("token");
    const aggregated = [];
    const baseUrl = `${API_BASE_URL}/${activeId}/rag/generate-from-story`;

    const typedResults = (response, type) => {
      if (!Array.isArray(response?.data?.results)) {
        return [];
      }
      return response.data.results.map((entry) => ({ ...entry, test_type: type }));
    };

    if (selectedFile) {
        for (const type of targetTestTypes) {
          const formData = new FormData();
          formData.append("file", selectedFile);
          formData.append("test_type", type);
        if (targetScriptPathValue) {
          formData.append("target_script_path", targetScriptPathValue);
        }
        if (targetRunnerScriptPathValue) {
          formData.append("target_runner_script_path", targetRunnerScriptPathValue);
        }
        if (selectedTestCaseId) {
          formData.append("replace_existing", "true");
          formData.append("case_uuid", selectedTestCaseId);
        }
        const res = await axios.post(baseUrl, formData, {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Bearer ${token}`,
          },
        });
        aggregated.push(...typedResults(res, type));
      }
      return aggregated;
    }

    const storyObjectsToUse =
      Array.isArray(jiraStoryObjects) && jiraStoryObjects.length ? jiraStoryObjects : null;
    const stories = storyObjectsToUse
      ? storyObjectsToUse
        .map((obj) => obj?.executable_text || "")
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
      : (userStoriesInput || "")
        .split("|")
        .map((s) => s.trim())
        .filter((s) => s.length > 0);

    if (!stories.length) {
      throw new Error("Please enter at least one valid user story separated by |");
    }

    for (const story of stories) {
      const storyObject = storyObjectsToUse
        ? jiraStoryObjects.find((obj) => (obj?.executable_text || "").trim() === story)
        : null;
        for (const type of targetTestTypes) {
          const params = new URLSearchParams({
            user_story: story,
            test_type: type,
          });

          if (selectedTestCaseId) {
            params.append("replace_existing", "true");
            params.append("case_uuid", selectedTestCaseId);
          }
          if (storyObject?.jira_key) {
            params.append("jira_key", storyObject.jira_key);
          }
        if (Array.isArray(storyObject?.acceptance_criteria)) {
          params.append("acceptance_criteria", JSON.stringify(storyObject.acceptance_criteria));
        }
        if (targetScriptPathValue) {
          params.append("target_script_path", targetScriptPathValue);
        }
        if (targetRunnerScriptPathValue) {
          params.append("target_runner_script_path", targetRunnerScriptPathValue);
        }
        const res = await axios.post(baseUrl, params, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        aggregated.push(...typedResults(res, type));
      }
    }

    return aggregated;
  }, [
    ensureActiveProject,
    jiraStoryObjects,
    selectedFile,
    selectedTestTypes,
    selectedTestCaseType,
    selectedTestCaseScriptPath,
    selectedTestCaseRunnerScriptPath,
    userStoriesInput,
  ]);

  const createTestCasesFromResults = useCallback(
    async (results) => {
      if (!results.length) {
        return [];
      }
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
      const createdIds = [];
      for (const result of results) {
        const body = {
          test_name: (testCaseFormName || result?.test_name || "").trim() || undefined,
          user_story: (result?.original_story || userStoriesInput || "").trim(),
          auto_testcase: (result?.auto_testcase || "").trim(),
          script_path: result?.test_file_path,
          runner_script_path: result?.runner_script_path,
          tags: parseTagsInput(testCaseFormTags),
          markers: [],
          priority: testCaseFormPriority || "Low",
          test_type: result?.test_type || "ui",
        };
        if (!body.auto_testcase) {
          throw new Error("Generated test case did not include executable steps.");
        }
        const response = await axios.post(`${API_BASE_URL}/projects/${activeId}/testcases`, body, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        if (response?.data?.testcase?.case_uuid) {
          createdIds.push(response.data.testcase.case_uuid);
        }
      }
      return createdIds;
    },
    [
      ensureActiveProject,
      testCaseFormName,
      testCaseFormTags,
      testCaseFormPriority,
      userStoriesInput,
    ]
  );

  const updateTestCaseFromResult = useCallback(
    async (result) => {
      if (!selectedTestCaseId) {
        throw new Error("Select a test case to update.");
      }
      const activeId = await ensureActiveProject();
      if (!activeId) {
        throw new Error("No active project. Please start a project first.");
      }
      const token = localStorage.getItem("token");
        const updatedTags = parseTagsInput(testCaseFormTags);
        const body = {
          test_name: (testCaseFormName || result?.test_name || "").trim() || undefined,
          user_story: (userStoriesInput || result?.original_story || "").trim(),
          auto_testcase: (result?.auto_testcase || "").trim(),
          script_path: selectedTestCaseScriptPath || undefined,
          runner_script_path: selectedTestCaseRunnerScriptPath || undefined,
          tags: updatedTags.length ? updatedTags : undefined,
          priority: testCaseFormPriority || "Low",
          test_type: result?.test_type || "ui",
        };
      if (!body.auto_testcase) {
        throw new Error("Generated test case did not include executable steps.");
      }
      const response = await axios.put(
        `${API_BASE_URL}/projects/${activeId}/testcases/${selectedTestCaseId}`,
        body,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      return response?.data?.testcase;
  },
  [
    ensureActiveProject,
    selectedTestCaseId,
    selectedTestCaseScriptPath,
    testCaseFormName,
      testCaseFormTags,
      testCaseFormPriority,
      userStoriesInput,
    ]
  );

  const fetchStoredTestCases = useCallback(async () => {
    setListLoading(true);
    setListError("");
    try {
      const activeId = await ensureActiveProject();
      if (!activeId) {
        setTestCases([]);
        return;
      }
      const token = localStorage.getItem("token");
      const response = await axios.get(`${API_BASE_URL}/projects/${activeId}/testcases`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const list = Array.isArray(response?.data?.testcases) ? response.data.testcases : [];
      setTestCases(list);
      if (selectedTestCaseId && !list.some((tc) => tc.case_uuid === selectedTestCaseId)) {
        clearSelectedTestCase();
      } else if (
        selectedTestCaseType &&
        !list.some((tc) => ((tc.test_type || "ui").toLowerCase() === selectedTestCaseType))
      ) {
        clearSelectedTestCase();
      }
    } catch (err) {
      console.error("Failed to load test cases:", err);
      setListError("Unable to load stored test cases.");
    } finally {
      setListLoading(false);
    }
  }, [ensureActiveProject, selectedTestCaseId, setTestCases, clearSelectedTestCase]);

  useEffect(() => {
    fetchStoredTestCases();
  }, [fetchStoredTestCases]);

  useEffect(() => {
    if (!selectedTestCaseId) {
      return;
    }
    const record = testCases.find((tc) => tc.case_uuid === selectedTestCaseId);
    if (record) {
      setUserStoriesInput(record.user_story || "");
      setTestCaseFormName(record.test_name || "");
      setTestCaseFormTags((record.tags || []).join(", "));
      setTestCaseFormPriority(record.priority || "Low");
      setSelectedTestCaseType((record.test_type || "ui").toLowerCase());
      setSelectedTestCaseScriptPath(record.script_path || "");
      setSelectedTestCaseRunnerScriptPath(record.runner_script_path || "");
    }
  }, [
    selectedTestCaseId,
    setUserStoriesInput,
    setSelectedTestCaseScriptPath,
    setSelectedTestCaseType,
    testCases,
  ]);

  const fetchTestCases = async () => {
    if ((!userStoriesInput || userStoriesInput.trim() === "") && !selectedFile) {
      setError("Please enter at least one user story or upload a file.");
      return;
    }

    if (selectedTestCaseId && (!userStoriesInput || !userStoriesInput.trim())) {
      setError("Enter a user story to update the selected test case.");
      return;
    }

    try {
      setLoadingGeneration(true);
    setError("");
    const generated = await collectGenerationResults();
      if (!generated.length) {
        throw new Error("No test cases were generated.");
      }

      if (selectedTestCaseId) {
        await updateTestCaseFromResult(generated[0]);
        notify.success("Test case updated successfully.");
        clearSelectedTestCase();
        setUserStoriesInput("");
        setSelectedFile(null);
        setJiraStoryObjects([]);
        if (storyInputRef.current) {
          storyInputRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
          storyInputRef.current.focus();
        }
      } else {
        const createdIds = await createTestCasesFromResults(generated);
        if (!createdIds.length) {
          throw new Error("Failed to save generated test cases.");
        }
        const createdCount = createdIds.length || generated.length;
        notify.success(`Test case(s) created successfully (${createdCount}).`);
        handleCreateNewTestCase();
      }

      fetchStoredTestCases().catch(() => {});
    } catch (err) {
      console.error(err);
      const message = err?.response?.data?.detail || err?.message || "Error generating test cases.";
      setError(message);
      notify.error(message);
    } finally {
      setLoadingGeneration(false);
    }
  };
  // Import from Jira
  const handleJiraImport = async (payload) => {
    setLoadingJira(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/jira/import`, payload, {
        headers: requireBearerAuthHeaders(),
      });
      const importedStories = response.data?.stories || [];

      if (importedStories.length > 0) {
        if (Array.isArray(response.data?.story_objects) && response.data.story_objects.length) {
          setJiraStoryObjects(response.data.story_objects);
          setUserStoriesInput(
            response.data.story_objects
              .map((obj) => obj?.executable_text || "")
              .filter((text) => text)
              .join(" |\n")
          );
        } else {
          setJiraStoryObjects([]);
          setUserStoriesInput(importedStories.join(" |\n"));
        }
        // join with pipe so UI shows the delimiter clearly
        setSelectedFile(null);
        notify.success("User stories imported from Jira.");
        setShowJiraModal(false);
      } else {
        notify.info("No stories found in Jira.");
      }
    } catch (err) {
      console.error(err);
      notify.error("Failed to import stories from Jira.");
    } finally {
      setLoadingJira(false);
    }
  };

  // Import from Excel: extract 'User Story' from 'User Stories' sheet
const handleExcelImport = () => {
  setLoadingExcel(true);
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".xlsx, .xls";

  input.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();

    reader.onload = (event) => {
      try {
        const data = new Uint8Array(event.target.result);
        const workbook = XLSX.read(data, { type: "array" });

        if (!workbook.SheetNames || workbook.SheetNames.length === 0) {
          notify.error("No sheets found in the Excel file.");
          setLoadingExcel(false);
          return;
        }

        const sheetName = workbook.SheetNames.includes("User Stories")
          ? "User Stories"
          : workbook.SheetNames[0];
        const userStoriesSheet = workbook.Sheets[sheetName];
        if (!userStoriesSheet) {
          notify.error(`Sheet named '${sheetName}' not found.`);
          setLoadingExcel(false);
          return;
        }

        const jsonSheet = XLSX.utils.sheet_to_json(userStoriesSheet, { defval: "" });

        const normalizeKey = (key) =>
          String(key || "")
            .trim()
            .toLowerCase()
            .replace(/[^a-z0-9]+/g, "");

        const headerRow = jsonSheet.find((row) => row && Object.keys(row).length > 0) || {};
        const headers = Object.keys(headerRow);
        const allowedKeys = new Set(["userstory", "userstories", "story"]);

        let userStoryColKey =
          headers.find((k) => allowedKeys.has(normalizeKey(k))) || null;

        if (!userStoryColKey && headers.length === 1) {
          userStoryColKey = headers[0];
        }

        if (!userStoryColKey) {
          const cols = headers.length ? headers.join(", ") : "none";
          notify.error(
            `Column 'User Story' not found in '${sheetName}' sheet. Columns present: ${cols}`
          );
          setLoadingExcel(false);
          return;
        }

        const stories = jsonSheet
          .map((row) => row[userStoryColKey])
          .filter((val) => typeof val === "string" && val.trim().length > 0);

        // Join with pipe so user can see delimiters; fetchTestCases will split on '|'
        setUserStoriesInput(stories.join(" |\n"));
        setSelectedFile(file);
        setJiraStoryObjects([]);
        notify.success("User stories imported from Excel.");
      } catch (err) {
        console.error(err);
        notify.error("Failed to import user stories from Excel.");
      }
      setLoadingExcel(false);
    };

    reader.readAsArrayBuffer(file);
  };

  input.click();
};

  // Git push feature functions
  const handlePushToGitClick = () => {
    notify.info("Push to Git is not available from this screen.");
  };

  const handleGitModalSubmit = async () => {
    notify.info("Push to Git is not available from this screen.");
  };


  const handleGitModalClose = () => {
    setShowGitModal(false);
    setRepoUrl("");
    setBranchName("main");
    setCommitMessage("Add automated test cases");
  };

  const handleJiraModalClose = () => {
    setShowJiraModal(false);
  };

  const parseListInput = (value) =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);

  const handleJiraModalSubmit = async () => {
    if (!jiraBaseUrl.trim() || !jiraEmail.trim() || !jiraApiToken.trim() || !jiraProjectKey.trim()) {
      notify.error("Jira base URL, email, API token, and project key are required.");
      return;
    }

    await handleJiraImport({
      base_url: jiraBaseUrl.trim(),
      email: jiraEmail.trim(),
      api_token: jiraApiToken.trim(),
      project_key: jiraProjectKey.trim(),
      // Single-issue import: backend will ignore project/JQL and return one story.
      issue_key: jiraIssueKey.trim() || undefined,
      issue_keys: parseListInput(jiraIssueKeys),
      jql: jiraIssueKey.trim() ? undefined : jiraJql.trim() || undefined,
    });
  };

  const canProceed = !loadingGeneration && (testCases || []).length > 0;

  return (
    <div className={styles.storyInputContainer}>
      <div className={styles.contentBox}>
        <h3 className={styles.title}>Import User Stories</h3>
        <p>Add user stories from Jira, Excel, or create them manually</p>

        <div className={styles.importOptions}>
          {/* Manual Entry */}
          <button
            onClick={() => {
              setSelectedFile(null);
              setJiraStoryObjects([]);
            }}
            className={`${styles.optionCard} ${styles.clickable}`}
          >
            <i className={`fa-solid fa-plus ${styles.optionIcon}`}></i>
            <h3 className={styles.optionTitle}>Manual Entry</h3>
            <p className={styles.optionDescription}>Add user stories manually</p>
          </button>

          {/* Jira Import */}
          <button
            onClick={() => setShowJiraModal(true)}
            disabled={loadingJira}
            className={`${styles.optionCard} ${styles.clickable}`}
          >
            <i className={`fa-solid fa-file-import ${styles.optionIcon}`}></i>
            <h3 className={styles.optionTitle}>
              {loadingJira ? <div className={styles.spinner}></div> : "Import from Jira"}
            </h3>
            <p className={styles.optionDescription}>Connect to Jira Instance</p>
          </button>

          {/* Excel Import */}
          <button
            onClick={handleExcelImport}
            disabled={loadingExcel}
            className={`${styles.optionCard} ${styles.clickable}`}
          >
            <i className={`fa-solid fa-file ${styles.optionIcon}`}></i>
            <h3 className={styles.optionTitle}>
              {loadingExcel ? (
                <div className={styles.spinner}></div>
              ) : (
                "Import Excel" + (selectedFile ? ` (${selectedFile.name})` : "")
              )}
            </h3>
            <p className={styles.optionDescription}>Import Excel file</p>
          </button>
        </div>

        {/* Textarea */}
        <textarea
          ref={storyInputRef}
          rows="5"
          cols="60"
          placeholder="Type your user story here... (use | to separate multiple)"
          value={userStoriesInput}
          onChange={(e) => {
            setUserStoriesInput(e.target.value);
            setSelectedFile(null);
            setJiraStoryObjects([]);
          }}
          className={styles.textArea}
        ></textarea>

        {error && <p className={styles.errorText}>{error}</p>}

        {impactedSummary?.count > 0 && (
          <div className={styles.impactPanel}>
            <div className={styles.impactHeader}>
              <div>
                <h4 className={styles.impactTitle}>Impacted Testcases</h4>
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
              <button type="button" className={styles.impactDismissButton} onClick={clearImpactedTestcases}>
                Dismiss
              </button>
            </div>
            <div className={styles.impactList}>
              {pagedImpactedItems.map((item) => (
                <div key={item.case_uuid || item.script_path} className={styles.impactRow}>
                  <div>
                    {item.script_path ? (
                      <button
                        type="button"
                        className={styles.impactNameLink}
                        onClick={() => handleOpenImpactedTestFile(item)}
                      >
                        {item.display_name || item.test_name || item.case_uuid}
                      </button>
                    ) : (
                      <div className={styles.impactName}>{item.display_name || item.test_name || item.case_uuid}</div>
                    )}
                    <div className={styles.impactMeta}>
                      {item.case_uuid || "No ID"}
                      {item.script_path ? ` • ${item.script_path}` : ""}
                      {item.test_type ? ` • ${item.test_type}` : ""}
                    </div>
                  </div>
                  <button
                    type="button"
                    className={styles.impactOpenButton}
                    onClick={() => handleOpenImpactedTestcase(item)}
                  >
                    Open Testcase
                  </button>
                </div>
              ))}
            </div>
            {impactPageCount > 1 && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  marginTop: "12px",
                  flexWrap: "wrap",
                }}
              >
                <div className={styles.pager}>
                  <button
                    type="button"
                    className={styles.pagerButton}
                    disabled={normalizedImpactPage <= 1}
                    onClick={() => setImpactPage((page) => Math.max(1, page - 1))}
                  >
                    Previous
                  </button>
                  {Array.from({ length: impactPageCount }, (_, index) => {
                    const pageNumber = index + 1;
                    const isActive = pageNumber === normalizedImpactPage;
                    return (
                      <button
                        key={pageNumber}
                        type="button"
                        className={`${styles.pagerButton} ${isActive ? styles.pagerButtonActive : ""}`}
                        onClick={() => setImpactPage(pageNumber)}
                      >
                        {pageNumber}
                      </button>
                    );
                  })}
                  <button
                    type="button"
                    className={styles.pagerButton}
                    disabled={normalizedImpactPage >= impactPageCount}
                    onClick={() => setImpactPage((page) => Math.min(impactPageCount, page + 1))}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}


        <div className={styles.testTypesContainer}>
          <h4 className={styles.testTypesTitle}>Select Test Types to Generate</h4>
          <p className={styles.testTypesHint}>
            No selection is prefilled. Choose only the test suites you currently need.
          </p>
          <div className={styles.checkboxGroup}>
            {TEST_TYPE_OPTIONS.map((option) => (
              <label key={option.value} className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  value={option.value}
                  checked={selectedTestTypes.includes(option.value)}
                  onChange={handleTestTypeChange}
                />
                {option.label}
              </label>
            ))}
          </div>
        </div>

        {/* Generate */}
        <div className={styles.generateButtonContainer}>
          <button onClick={fetchTestCases} className={styles.generateButton}>
            {loadingGeneration ? (
              <div className={styles.spinner}></div>
            ) : selectedTestCaseId ? (
              "Update Test Case"
            ) : (
              "Generate Test Cases"
            )}
          </button>
        </div>

        <div className={styles.testCaseListWrapper}>
        {listError && <p className={styles.listError}>{listError}</p>}
        {listLoading ? (
          <p className={styles.listStatus}>Loading test cases...</p>
        ) : storyGroups.length ? (
          <>
                        <div className={styles.storyAndCases}>
              <div className={styles.casesPanel}>
                {(() => {
                  let caseIndex = 0;
                  return storyGroups.map((group, groupIndex) => {
                    const casesByType = getCasesByType(group.cases || []);
                    return (
                    <div
                      key={`${group.story}-${groupIndex}`}
                      className={styles.storyGroupBlock}
                    >
                      <div className={styles.testCasesTableWrapper}>
                        <table className={styles.testCasesTable}>
                          <thead>
                            <tr>
                              <th>Test Case</th>
                            </tr>
                          </thead>
                          <tbody>
                            {TEST_TYPE_OPTIONS.map((option) => {
                              const cases = casesByType[option.value] || [];
                              if (!cases.length) {
                                return null;
                              }
                              caseIndex += 1;
                              const representative =
                                cases.find((candidate) => candidate.runner_script_path) || cases[0];
                              const identifier = representative.case_uuid || representative.id;
                              const rowSelected =
                                selectedTestCaseId === identifier &&
                                selectedTestCaseType === option.value;
                              const autoTestCase = cases
                                .map((tc, idx) => {
                                  const block = tc.auto_testcase || "";
                                  if (idx === 0) {
                                    return block;
                                  }
                                  const variantCaption = `# Variant ${idx + 1}: ${tc.test_name || tc.display_name || ""}`.trim();
                                  return [`${variantCaption}`, block].filter(Boolean).join("\n");
                                })
                                .filter(Boolean)
                                .join("\n\n");
                              const displayFromScriptPath = (() => {
                                const rawPath =
                                  representative.script_path ||
                                  representative.test_path ||
                                  representative.runner_script_path ||
                                  "";
                                if (!rawPath) {
                                  return "";
                                }
                                const parts = rawPath.split(/[\\/]/).filter(Boolean);
                                if (!parts.length) {
                                  return "";
                                }
                                return parts[parts.length - 1].replace(/\.py$/i, "");
                              })();
                              const labelText =
                                displayFromScriptPath ||
                                representative.display_name ||
                                representative.test_name ||
                                identifier;
                              const updatedLabel = representative.updated_at
                                ? new Date(representative.updated_at).toLocaleString()
                                : "—";
                              return (
                                <React.Fragment key={`${groupIndex}-${option.value}`}>
                                  <tr className={styles.testCaseSectionHeader}>
                                    <td colSpan="1">{option.label}</td>
                                  </tr>
                                  <tr
                                    className={rowSelected ? styles.testCaseRowSelected : ""}
                                    key={`${option.value}-${identifier}`}
                                  >
                                    <td>
                                      <div className={styles.testCaseRowHeader}>
                                        <strong>
                                          <span className={styles.testCaseCount}>#{caseIndex}</span>
                                          {labelText}
                                        </strong>
                                        <label className={styles.updateCheckbox}>
                                          <input
                                            type="checkbox"
                                            checked={rowSelected}
                                            onChange={() => handleSelectTestCaseRow(representative)}
                                          />
                                          Update this test case
                                        </label>
                                      </div>
                                      <div className={styles.subText}>
                                        Updated {updatedLabel}
                                        {cases.length > 1 && (
                                          <span>
                                            {" "}
                                            • {cases.length} variants ({cases
                                              .map((tc) => tc.test_type || tc.test_name || tc.display_name)
                                              .filter(Boolean)
                                              .join(", ")})
                                          </span>
                                        )}
                                      </div>
                                      <div className={styles.testCaseBodySplit}>
                                        <div className={styles.storyInline}>
                                          <div className={styles.storyInlineLabel}> Test case</div>
                                          <div className={styles.storyInlineText}>{group.story}</div>
                                        </div>
                                        <div className={styles.testCaseInline}>
                                          <div className={styles.storyInlineLabel}>Test Scripts</div>
                                          <pre className={styles.testCaseCode}>{autoTestCase}</pre>
                                        </div>
                                      </div>
                                    </td>
                                  </tr>
                                </React.Fragment>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                });
              })()}
              </div>
            </div>
          </>
        ) : (
          <p className={styles.testCaseEmpty}>No saved test cases yet. Generate one to get started.</p>
        )}
      </div>
      </div>

      {/* Git Modal */}
      {showGitModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h2>Push to Git</h2>
            <button onClick={handleGitModalClose} className={styles.closeModalButton}>
              <i className="fa-solid fa-xmark"></i>
            </button>
            <label>
              Repository URL:
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="e.g., https://github.com/user/repo.git"
              />
            </label>
            <label>
              Branch Name:
              <input
                type="text"
                value={branchName}
                onChange={(e) => setBranchName(e.target.value)}
                placeholder="e.g., main or feature/my-tests"
              />
            </label>
            <label>
              Commit Message:
              <textarea
                rows="3"
                value={commitMessage}
                onChange={(e) => setCommitMessage(e.target.value)}
                placeholder="Enter commit message"
              ></textarea>
            </label>
            <div className={styles.modalActions}>
              <button onClick={handleGitModalClose} className={styles.modalCancelButton} disabled={isPushingToGit}>
                Cancel
              </button>
              <button onClick={handleGitModalSubmit} className={styles.modalSubmitButton} disabled={isPushingToGit}>
                {isPushingToGit ? <div className={styles.spinner}></div> : "Push"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Jira Modal */}
      {showJiraModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <h2>Import from Jira</h2>
            <button onClick={handleJiraModalClose} className={styles.closeModalButton}>
              <i className="fa-solid fa-xmark"></i>
            </button>
            <label>
              Jira Base URL:
              <input
                type="text"
                value={jiraBaseUrl}
                onChange={(e) => setJiraBaseUrl(e.target.value)}
                placeholder="e.g., https://your-domain.atlassian.net"
              />
            </label>
            <label>
              Email or Username:
              <input
                type="text"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
                placeholder="jira-user@example.com"
              />
            </label>
            <label>
              API Token:
              <input
                type="password"
                value={jiraApiToken}
                onChange={(e) => setJiraApiToken(e.target.value)}
                placeholder="Jira API token"
              />
            </label>
            <label>
              Project Key:
              <input
                type="text"
                value={jiraProjectKey}
                onChange={(e) => setJiraProjectKey(e.target.value)}
                placeholder="e.g., TEST"
              />
            </label>
            <label>
              Jira Issue Key (optional):
              <input
                type="text"
                value={jiraIssueKey}
                onChange={(e) => setJiraIssueKey(e.target.value)}
                placeholder="e.g., BAN-12"
              />
            </label>
            <label>
              JQL (optional):
              <textarea
                rows="3"
                value={jiraJql}
                onChange={(e) => setJiraJql(e.target.value)}
                disabled={Boolean(jiraIssueKey.trim())}
                placeholder='e.g., project = TEST AND issuetype = "Story"'
              ></textarea>
            </label>
            <div className={styles.modalActions}>
              <button onClick={handleJiraModalClose} className={styles.modalCancelButton} disabled={loadingJira}>
                Cancel
              </button>
              <button onClick={handleJiraModalSubmit} className={styles.modalSubmitButton} disabled={loadingJira}>
                {loadingJira ? <div className={styles.spinner}></div> : "Import"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Nav */}
      <div className={styles.navigationButtons}>
        <button onClick={onBack} className={styles.navButton}>
          <i className="fa-solid fa-angle-left"></i>
          Previous
        </button>

        <button onClick={onNext} disabled={!canProceed} className={`${styles.navButton} ${styles.next}`}>
          Next <i className="fa-solid fa-angle-right"></i>
        </button>
      </div>
    </div>
  );
};

export default StoryInput;

