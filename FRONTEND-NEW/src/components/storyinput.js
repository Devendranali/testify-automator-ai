import React, { useState } from "react";
import axios from "axios";
import * as XLSX from "xlsx";
import { toast, ToastContainer } from "react-toastify";
import styles from "./StoryInput.module.css";

const StoryInput = ({ onBack, onNext, testCases, setTestCases }) => {
    const [userStoriesInput, setUserStoriesInput] = useState("");
    const [selectedFile, setSelectedFile] = useState(null);

    const [loadingGeneration, setLoadingGeneration] = useState(false);
    const [loadingJira, setLoadingJira] = useState(false);
    const [loadingExcel, setLoadingExcel] = useState(false);
    const [error, setError] = useState("");
    const [generationSuccess, setGenerationSuccess] = useState(false);
    const [generationError, setGenerationError] = useState(false);

    // Fetch test cases from backend
    const fetchTestCases = async () => {
        if (
            (!userStoriesInput || userStoriesInput.trim() === "") &&
            !selectedFile
        ) {
            setError("Please enter at least one user story or upload a file.");
            return;
        }

        try {
            setLoadingGeneration(true);
            setError("");
            setGenerationSuccess(false);
            setGenerationError(false);

            let response;

            // If a file was selected (Excel/CSV)
            if (selectedFile) {
                const formData = new FormData();
                formData.append("file", selectedFile);
                formData.append("site_url", "https://www.saucedemo.com");

                response = await axios.post(
                    "http://localhost:8001/rag/generate-from-story",
                    formData,
                    {
                        headers: { "Content-Type": "multipart/form-data" },
                    }
                );
            } else {
                // Use stories entered in the textarea
                const stories = userStoriesInput
                    .split("|")
                    .map((s) => s.trim())
                    .filter((s) => s.length > 0);

                if (stories.length === 0) {
                    setError(
                        "Please enter at least one valid user story separated by | "
                    );
                    setLoadingGeneration(false);
                    return;
                }

                response = await axios.post(
                    "http://localhost:8001/rag/generate-from-story",
                    new URLSearchParams({
                        user_story: stories.join("\n"),
                        site_url: "https://www.saucedemo.com",
                    })
                );
            }

            setTestCases(response.data.results);
            toast.success("Test cases generated successfully.");
            setGenerationSuccess(true);
            setGenerationError(false);
        } catch (err) {
            console.error(err);
            setError(
                err.response?.data?.detail || "Error generating test cases."
            );
            setGenerationError(true);
            setGenerationSuccess(false);
        } finally {
            setLoadingGeneration(false);
        }
    };

    // Import from Jira
    const handleJiraImport = async () => {
        setLoadingJira(true);
        try {
            const response = await axios.get(
                "http://localhost:8001/jira/import"
            );
            const importedStories = response.data?.stories || [];

            if (importedStories.length > 0) {
                setUserStoriesInput(importedStories.join(" |\n"));
                setSelectedFile(null); // clear any file
                toast.success("User stories imported from Jira.");
            } else {
                toast.info("No stories found in Jira.");
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to import stories from Jira.");
        } finally {
            setLoadingJira(false);
        }
    };

    // Import from Excel, extract 'User Story' column from 'User Stories' sheet
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

                    // Always pick "User Stories" sheet
                    const userStoriesSheet = workbook.Sheets["User Stories"];
                    if (!userStoriesSheet) {
                        toast.error("Sheet named 'User Stories' not found.");
                        setLoadingExcel(false);
                        return;
                    }

                    // Parse sheet as array of objects
                    const jsonSheet = XLSX.utils.sheet_to_json(
                        userStoriesSheet,
                        { defval: "" }
                    );

                    // Find the correct "User Story" column (case-insensitive)
                    const userStoryColKey = jsonSheet.length
                        ? Object.keys(jsonSheet[0]).find(
                              (k) => k.trim().toLowerCase() === "user story"
                          )
                        : null;

                    if (!userStoryColKey) {
                        toast.error(
                            "Column 'User Story' not found in 'User Stories' sheet."
                        );
                        setLoadingExcel(false);
                        return;
                    }

                    // Extract all values in the column (ignore empty)
                    const stories = jsonSheet
                        .map((row) => row[userStoryColKey])
                        .filter(
                            (val) =>
                                typeof val === "string" && val.trim().length > 0
                        );

                    setUserStoriesInput(stories.join(" |\n"));
                    setSelectedFile(file); // set the file, so the name will show in UI
                    toast.success("User stories imported from Excel.");
                } catch (err) {
                    console.error(err);
                    toast.error("Failed to import user stories from Excel.");
                }
                setLoadingExcel(false);
            };

            reader.readAsArrayBuffer(file);
        };

        input.click();
    };

    return (
        <div className={styles.storyInputContainer}>
            <ToastContainer />
            <div className={styles.contentBox}>
                <h3 className={styles.title}>Import User Stories</h3>
                <p>
                    Add user stories from Jira, Excel, or create them manually
                </p>

                <div className={styles.importOptions}>
                    {/* Manual Entry Button */}
                    <button
                        onClick={() => {
                            setSelectedFile(null); // clear file when manually entering
                        }}
                        className={`${styles.optionCard} ${styles.clickable}`}
                    >
                        <i
                            className={`fa-solid fa-plus ${styles.optionIcon}`}
                            style={{ color: "blue" }}
                        ></i>
                        <h3 className={styles.optionTitle}>Manual Entry</h3>
                        <p className={styles.optionDescription}>
                            Add user stories manually
                        </p>
                    </button>

                    {/* Jira Import Button */}
                    <button
                        onClick={handleJiraImport}
                        disabled={loadingJira}
                        className={`${styles.optionCard} ${styles.clickable}`}
                    >
                        <i
                            className={`fa-solid fa-file-import ${styles.optionIcon}`}
                            style={{ color: "green" }}
                        ></i>
                        <h3 className={styles.optionTitle}>
                            {loadingJira ? (
                                <div className={styles.spinner}></div>
                            ) : (
                                "Import from Jira"
                            )}
                        </h3>
                        <p className={styles.optionDescription}>
                            Connect to Jira Instance
                        </p>
                    </button>

                    {/* Excel Import Button: always renders, file name shows only if selected */}
                    <button
                        onClick={handleExcelImport}
                        disabled={loadingExcel}
                        className={`${styles.optionCard} ${styles.clickable}`}
                    >
                        <i
                            className={`fa-solid fa-file ${styles.optionIcon}`}
                            style={{ color: "red" }}
                        ></i>
                        <h3 className={styles.optionTitle}>
                            {loadingExcel ? (
                                <div className={styles.spinner}></div>
                            ) : (
                                "Import Excel"
                            )}
                        </h3>
                        <p className={styles.optionDescription}>
                            Import Excel file
                        </p>
                        {/* Show file name if selected */}
                        {selectedFile && (
                            <div className={styles.selectedFileName}>
                                {selectedFile.name}
                            </div>
                        )}
                    </button>
                </div>

                {/* Textarea for user stories */}
                <textarea
                    rows="5"
                    cols="60"
                    placeholder="Type your user story here..."
                    value={userStoriesInput}
                    onChange={(e) => {
                        setUserStoriesInput(e.target.value);
                        setSelectedFile(null); // clear file when typing manually
                    }}
                    className={styles.textArea}
                ></textarea>

                {error && <p className={styles.errorText}>{error}</p>}

                {/* Generate Button */}
                <div className={styles.generateButtonContainer}>
                    <button
                        onClick={fetchTestCases}
                        className={styles.generateButton}
                    >
                        {loadingGeneration ? (
                            <div className={styles.spinner}></div>
                        ) : (
                            "Generate Test Cases"
                        )}
                    </button>
                </div>

                {/* Render test cases if available */}
                {Array.isArray(testCases) &&
                    testCases.map((tc, idx) => (
                        <div key={idx} className={styles.testCaseCard}>
                            <h4 className={styles.testCaseTitle}>
                                Generated Test Case : {idx + 1}
                            </h4>
                            <table className={styles.testCaseTable}>
                                <thead>
                                    <tr>
                                        <th>Prompt</th>
                                        <th>Automated Test Cases</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td className={styles.testCaseTableTd}>
                                            {tc.manual_testcase}
                                        </td>
                                        <td
                                            className={`${styles.testCaseTableTd} ${styles.code}`}
                                        >
                                            {tc.auto_testcase}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    ))}
            </div>

            {/* Navigation buttons */}
            <div className={styles.navigationButtons}>
                <button onClick={onBack} className={styles.navButton}>
                    <i className="fa-solid fa-angle-left"></i>
                    Previous
                </button>

                <button
                    onClick={onNext}
                    className={`${styles.navButton} ${styles.next}`}
                >
                    Next <i className="fa-solid fa-angle-right"></i>
                </button>
            </div>
        </div>
    );
};

export default StoryInput;
