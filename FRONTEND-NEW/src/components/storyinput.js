import React, { useState } from "react";
import axios from "axios";
import { toast, ToastContainer } from "react-toastify";
import styles from "./StoryInput.module.css";

const StoryInput = ({ onBack, onNext }) => {
  const [userStoriesInput, setUserStoriesInput] = useState("");
  const [userStoriesPrompt, setUserStoriesPrompt] = useState("generate test cases");
  const [testCasesGeneratedFromStory, setTestCasesGeneratedFromStory] = useState([]);
  const [loadingGeneration, setLoadingGeneration] = useState(false);
  const [error, setError] = useState("");
  const [generationSuccess, setGenerationSuccess] = useState(false);
  const [generationError, setGenerationError] = useState(false);

  const fetchTestCases = async () => {
    if (!userStoriesInput || userStoriesInput.trim() === "") {
      setError("Please enter at least one user story.");
      return;
    }

    try {
      setLoadingGeneration(true);
      setError("");
      setGenerationSuccess(false); 
      setGenerationError(false);   

      const stories = userStoriesInput
        .split("|")
        .map(s => s.trim())
        .filter(s => s.length > 0);

      if (stories.length === 0) {
        setError("Please enter at least one valid user story separated by | ");
        setLoadingGeneration(false);
        return;
      }

      const response = await axios.post("http://localhost:8001/rag/generate-from-story", {
        prompt: userStoriesPrompt,
        user_story: stories,
      });

      setTestCasesGeneratedFromStory(response.data.results);
      toast.success("Test cases generated successfully.");
      setGenerationSuccess(true);  
      setGenerationError(false);  
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.message || "Error generating test cases.");
      setGenerationError(true); 
      setGenerationSuccess(false);
    } finally {
      setLoadingGeneration(false);
    }

    console.log("Prompt:", userStoriesPrompt);
    console.log("User Stories:", userStoriesInput);
  };

  const handleJiraImport = async () => {
    try {
      const response = await axios.get("http://localhost:8001/jira/import"); 
      const importedStories = response.data?.stories || [];

      if (importedStories.length > 0) {
        setUserStoriesInput(importedStories.join(" |\n"));
        toast.success("User stories imported from Jira.");
      } else {
        toast.info("No stories found in Jira.");
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to import stories from Jira.");
    }
  };

  return (
    <div className={styles.storyInputContainer}>
      <ToastContainer/>
      <div className={styles.contentBox}>
        <h3 className={styles.title}>Import User Stories</h3>
        <p>Add user stories from Jira, Excel, or create them manually</p>

        <div className={styles.importOptions}>
          <button className={`${styles.optionCard} ${styles.clickable}`}>
            <i className={`fa-solid fa-plus ${styles.optionIcon}`} style={{ color: "blue" }}></i>
            <h3 className={styles.optionTitle}>Manual Entry</h3>
            <p className={styles.optionDescription}>Add user stories manually</p>
          </button>

          <button
            onClick={handleJiraImport}
            className={`${styles.optionCard} ${styles.clickable}`}
          >
            <i className={`fa-solid fa-file-import ${styles.optionIcon}`} style={{ color: "green" }}></i>
            <h3 className={styles.optionTitle}>Import from Jira</h3>
            <p className={styles.optionDescription}>Connect to Jira Instance</p>
          </button>

          <button className={`${styles.optionCard} ${styles.clickable}`}>
            <i className={`fa-solid fa-file ${styles.optionIcon}`} style={{ color: "purple" }}></i>
            <h3 className={styles.optionTitle}>Upload Excel</h3>
            <p className={styles.optionDescription}>Upload Excel File</p>
          </button>
        </div>

        <textarea
          rows="5"
          cols="60"
          placeholder="Type your user story here..."
          value={userStoriesInput}
          onChange={(e) => setUserStoriesInput(e.target.value)}
          className={styles.textArea}
        ></textarea>

        {error && <p className={styles.errorText}>{error}</p>}

        <div className={styles.generateButtonContainer}>
          <button
            onClick={fetchTestCases}
            className={styles.generateButton}
          >
            {loadingGeneration ? "Generating..." : "Generate Test Cases"}
          </button>
        </div>

        {Array.isArray(testCasesGeneratedFromStory) &&
          testCasesGeneratedFromStory.map((tc, idx) => (
            <div
              key={idx}
              className={styles.testCaseCard}
            >
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
                    <td className={`${styles.testCaseTableTd} ${styles.code}`}>
                      {tc.auto_testcase}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
      </div>

      <div className={styles.navigationButtons}>
        <button
          onClick={onBack}
          className={styles.navButton}
        >
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

