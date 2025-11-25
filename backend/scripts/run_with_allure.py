#!/usr/bin/env python3
"""
Run pytest to produce Allure results, generate Allure HTML and open it in the browser.

Usage:
  python run_with_allure.py [--src SRC_DIR] [--test TEST_PATH]

Defaults:
  SRC_DIR: generated_runs/src
  TEST_PATH: tests (runs all tests under `tests`)

This script uses the same Python interpreter you're running it with (so activate your venv first).
It requires `allure-pytest` to be installed in the environment and the `allure` CLI to be on PATH.
"""
import argparse
import subprocess
import sys
from pathlib import Path
import shutil
import webbrowser


def main():
    parser = argparse.ArgumentParser(description="Run pytest + Allure and open generated report")
    parser.add_argument("--src", default="generated_runs/src", help="Source directory containing tests (default: generated_runs/src)")
    parser.add_argument("--test", default="tests", help="Test path to pass to pytest (file or folder). Default: 'tests'")
    parser.add_argument("--no-open", action="store_true", help="Do not open the generated report in a browser")
    args = parser.parse_args()

    src_dir = Path(args.src).resolve()
    if not src_dir.exists():
        print(f"Error: src dir does not exist: {src_dir}")
        sys.exit(2)

    # Allow passing either the containing `src` directory or the `tests` directory itself.
    # If user passed the tests dir, use its parent as the working src root but
    # adjust the default test path accordingly.
    if src_dir.name == "tests":
        cwd = src_dir.parent
        default_test = src_dir.name
    else:
        cwd = src_dir
        default_test = "tests"

    allure_results = cwd / "allure-results"
    allure_report = cwd / "allure-report"
    allure_results.mkdir(parents=True, exist_ok=True)

    test_path = args.test or default_test
    pytest_cmd = [sys.executable, "-m", "pytest", test_path, f"--alluredir={allure_results}"]
    print("Running pytest:", " ".join(str(p) for p in pytest_cmd))

    try:
        p = subprocess.run(pytest_cmd, cwd=cwd, check=False)
        if p.returncode != 0:
            print(f"pytest finished with exit code {p.returncode} (tests may have failed). Continuing to generate report if results exist.")
    except Exception as e:
        print("Failed to run pytest:", e)
        sys.exit(3)

    # Check for Allure CLI
    allure_exe = shutil.which("allure")
    if not allure_exe:
        print("Allure CLI not found on PATH. Please install it (choco/scoop/manual) and ensure `allure` is available in your PATH.")
        print("Falling back: no Allure HTML will be generated. You can still inspect files in:", allure_results)
        sys.exit(4)

    # Generate HTML
    gen_cmd = [allure_exe, "generate", str(allure_results), "-o", str(allure_report), "--clean"]
    print("Generating Allure HTML:", " ".join(gen_cmd))
    try:
        subprocess.run(gen_cmd, cwd=cwd, check=True)
    except subprocess.CalledProcessError as e:
        print("Allure generate failed:", e)
        sys.exit(5)

    index = allure_report / "index.html"
    if not index.exists():
        print("Allure generation finished but index.html not found at:", index)
        sys.exit(6)

    print("Allure report generated:", index)

    if not args.no_open:
        try:
            url = index.as_uri()
            print("Opening report in browser:", url)
            webbrowser.open(url)
        except Exception as e:
            print("Failed to open browser:", e)


if __name__ == "__main__":
    main()
