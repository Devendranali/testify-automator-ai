import os


def flatten_project_to_single_file(project_root, output_file):
    with open(output_file, "w", encoding="utf-8") as out_f:
        for root, dirs, files in os.walk(project_root):
            for file in files:
                file_path = os.path.join(root, file)

                # Skip binary files
                if not file_path.endswith((".py", ".txt", ".json", ".md", ".js", ".ts", ".html", ".css")):
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as in_f:
                        rel_path = os.path.relpath(file_path, project_root)
                        out_f.write(f"\n\n# === FILE: {rel_path} ===\n")
                        out_f.write(in_f.read())
                        out_f.write("\n")
                except Exception as e:
                    print(f"⚠️ Skipping {file_path}: {e}")

    print(f"\n✅ All content written to: {output_file}")


# === Usage Example ===
if __name__ == "__main__":
    project_folder = "C:/Users/Suchandan/Desktop/VNC/testify-automator-ai/backend"
    output_file_path = "flattened_code_dump.py"
    flatten_project_to_single_file(project_folder, output_file_path)
