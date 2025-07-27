import os


def flatten_selected_files(file_paths, output_file):
    """
    Reads only the specified files and writes their content to a single file.
    """
    with open(output_file, "w", encoding="utf-8") as out_f:
        for file_path in file_paths:
            # Skip non-existent files
            if not os.path.isfile(file_path):
                print(f"⚠️ Skipping (not found): {file_path}")
                continue

            # Skip binary files
            if not file_path.endswith((".py", ".txt", ".json", ".md", ".js", ".ts", ".html", ".css")):
                print(f"⚠️ Skipping (unsupported type): {file_path}")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as in_f:
                    rel_path = os.path.relpath(
                        file_path, os.path.commonpath(file_paths))
                    out_f.write(f"\n\n# === FILE: {rel_path} ===\n")
                    out_f.write(in_f.read())
                    out_f.write("\n")
            except Exception as e:
                print(f"⚠️ Error reading {file_path}: {e}")

    print(f"\n✅ Selected content written to: {output_file}")


# === Usage Example ===
if __name__ == "__main__":
    files_to_read = [
        r"C:/Users/Suchandan/Desktop/VNC/testify-automator-ai/backend/main.py",
        r"C:/Users/Suchandan/Desktop/VNC/testify-automator-ai/FRONTEND-NEW/src/App.js"
    ]
    output_file_path = "Output_selected_files.py"
    flatten_selected_files(files_to_read, output_file_path)
