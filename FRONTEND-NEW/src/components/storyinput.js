import React, { useState } from "react";
import axios from "axios";
import { toast, ToastContainer } from "react-toastify";

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
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        minHeight: "60vh",
        backgroundColor: "#f2f7fe",
        paddingTop: "2rem",
        paddingBottom: "30px",
      }}
    >
      <ToastContainer/>
      <div
        style={{
          padding: "1rem 3rem",
          border: "1px solid #ccc",
          minHeight: "45vh",
          width: "70vw",
          backgroundColor: "white",
          borderRadius: "10px",
          boxShadow: "0 2px 10px rgba(0, 0, 0, 0.05)",
        }}
      >
        <h3 style={{ fontSize: "30px" }}>Import User Stories</h3>
        <p>Add user stories from Jira, Excel, or create them manually</p>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            margin: "1px",
            gap: "20px",
            flexWrap: "nowrap",
            overflowX: "auto",
          }}
        >
          <div
            style={{
              border: "1px solid grey",
              minWidth: "340px",
              padding: "1rem",
              borderRadius: "8px",
              textAlign: "center",
              backgroundColor: "#fff",
              flexShrink: 0,
            }}
          >
            <i className="fa-solid fa-plus" style={{ fontSize: "30px", color: "blue" }}></i>
            <h3>Manual Entry</h3>
            <p>Add user stories manually</p>
          </div>

          <button
            onClick={handleJiraImport}
            style={{
              border: "1px solid grey",
              minWidth: "340px",
              padding: "1rem",
              borderRadius: "8px",
              textAlign: "center",
              backgroundColor: "#fff",
              flexShrink: 0,
              cursor: "pointer",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "0.5rem",
            }}
          >
            <i className="fa-solid fa-file-import" style={{ fontSize: "30px", color: "green" }}></i>
            <h3 style={{ margin: 0 , fontSize:"20px" }}>Import from Jira</h3>
            <p style={{ margin: 0 , fontSize:"17px"}}>Connect to Jira Instance</p>
          </button>

          <div
            style={{
              border: "1px solid grey",
              minWidth: "340px",
              padding: "1rem",
              borderRadius: "8px",
              textAlign: "center",
              backgroundColor: "#fff",
              flexShrink: 0,
            }}
          >
            <i className="fa-solid fa-file" style={{ fontSize: "30px", color: "purple" }}></i>
            <h3>Upload Excel</h3>
            <p>Upload Excel File</p>
          </div>
        </div>

        <textarea
          rows="5"
          cols="60"
          placeholder="Type your user story here..."
          value={userStoriesInput}
          onChange={(e) => setUserStoriesInput(e.target.value)}
          style={{
            padding: "1rem",
            borderRadius: "8px",
            border: "1px solid #ccc",
            fontSize: "16px",
            width: "97%",
            marginTop: "20px",
          }}
        ></textarea>

        {error && <p style={{ color: "red", marginTop: "10px" }}>{error}</p>}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "30px" }}>
          <button
            onClick={fetchTestCases}
            style={{
              padding: "0.7rem 1.5rem",
              fontSize: "18px",
              background: "linear-gradient(90deg, #4c3ecb, #5748de, #e353ed)",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            {loadingGeneration ? "Generating..." : "Generate Test Cases"}
          </button>
        </div>

        {Array.isArray(testCasesGeneratedFromStory) &&
          testCasesGeneratedFromStory.map((tc, idx) => (
            <div
              key={idx}
              style={{
                marginTop: "20px",
                padding: "15px",
                border: "1px solid #ccc",
                borderRadius: "10px",
                backgroundColor: "#fafafa",
                boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
              }}
            >
              <h4 style={{ marginBottom: "15px", color: "#333" }}>
                Generated Test Case : {idx + 1}
              </h4>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                  fontSize: "14px",
                  color: "#444",
                }}
              >
                <thead>
                  <tr>
                    <th
                      style={{
                        border: "1px solid #ccc",
                        padding: "12px",
                        textAlign: "left",
                        backgroundColor: "#e8e8e8",
                        fontWeight: "600",
                        width: "50%",
                      }}
                    >
                      Prompt
                    </th>
                    <th
                      style={{
                        border: "1px solid #ccc",
                        padding: "12px",
                        textAlign: "left",
                        backgroundColor: "#e8e8e8",
                        fontWeight: "600",
                        width: "50%",
                      }}
                    >
                      Automated Test Cases
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td
                      style={{
                        border: "1px solid #ccc",
                        padding: "12px",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        verticalAlign: "top",
                        backgroundColor: "#fff",
                      }}
                    >
                      {tc.manual_testcase}
                    </td>
                    <td
                      style={{
                        border: "1px solid #ccc",
                        padding: "12px",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        fontFamily: "Consolas, monospace",
                        fontSize: "13px",
                        backgroundColor: "#f7f7f7",
                        verticalAlign: "top",
                      }}
                    >
                      {tc.auto_testcase}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          ))}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: "30px",
          width: "70vw",
        }}
      >
        <button
          onClick={onBack}
          style={{
            padding: "0.7rem 2rem",
            fontSize: "18px",
            background: "lightgray",
            color: "black",
            border: "1px solid #ccc",
            borderRadius: "6px",
            cursor: "pointer",
          }}
        >
          <i className="fa-solid fa-angle-left" style={{ marginRight: "10px" }}></i>
          Previous
        </button>

        <button
          onClick={onNext}
          style={{
            padding: "0.7rem 2rem",
            fontSize: "18px",
            backgroundColor:"lightgray",
            color: "black",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
          }}
        >
          Next <i className="fa-solid fa-angle-right" style={{ marginLeft: "10px" }}></i>
        </button>
      </div>
    </div>
  );
};

export default StoryInput;
