from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List


def _build_java_cmd(dist_dir: Path, results_dir: Path, report_dir: Path) -> List[str]:
    lib_dir = dist_dir / "lib"
    classpath = f"{lib_dir}\\*;{lib_dir}\\config"
    return [
        "java",
        "-classpath",
        classpath,
        "io.qameta.allure.CommandLine",
        "generate",
        str(results_dir),
        "-o",
        str(report_dir),
        "--clean",
    ]


def build_allure_generate_cmd(results_dir: Path, report_dir: Path) -> List[str]:
    """
    Build a safe Allure generate command that works on Windows paths with spaces.
    Prefer the PowerShell wrapper if present (npm-installed allure), otherwise fall back to the binary.
    """
    override = (os.getenv("ALLURE_CLI") or "").strip()
    allure_exe = override or shutil.which("allure")
    if not allure_exe:
        raise FileNotFoundError("Allure CLI not found on PATH.")

    exe_path = Path(allure_exe)
    suffix = exe_path.suffix.lower()
    name_lower = exe_path.name.lower()

    # Prefer the npm-installed JS entrypoint when available to avoid .cmd argument parsing issues.
    def _node_entrypoint_for(exe: Path) -> Path | None:
        base_dir = exe.parent
        candidate = base_dir / "node_modules" / "allure-commandline" / "bin" / "allure"
        if candidate.exists():
            return candidate
        return None

    node_entry = _node_entrypoint_for(exe_path)
    if node_entry is not None and (suffix in {".cmd", ".bat", ".ps1"} or name_lower in {"allure", "allure.cmd", "allure.ps1"}):
        dist_dir = node_entry.parent.parent / "dist"
        if sys.platform.startswith("win") and dist_dir.exists():
            return _build_java_cmd(dist_dir, results_dir, report_dir)
        return [
            "node",
            str(node_entry),
            "generate",
            str(results_dir),
            "-o",
            str(report_dir),
            "--clean",
        ]
    if suffix == ".ps1":
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(exe_path),
            "generate",
            str(results_dir),
            "-o",
            str(report_dir),
            "--clean",
        ]

    if suffix in {".cmd", ".bat"}:
        # Prefer sibling PowerShell wrapper if present (npm install on Windows).
        ps1 = exe_path.with_suffix(".ps1")
        if ps1.exists():
            return [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
                "generate",
                str(results_dir),
                "-o",
                str(report_dir),
                "--clean",
            ]
        if sys.platform.startswith("win"):
            dist_dir = exe_path.parent / "node_modules" / "allure-commandline" / "dist"
            if dist_dir.exists():
                return _build_java_cmd(dist_dir, results_dir, report_dir)
        return [
            "cmd.exe",
            "/c",
            str(exe_path),
            "generate",
            str(results_dir),
            "-o",
            str(report_dir),
            "--clean",
        ]

    return [
        str(exe_path),
        "generate",
        str(results_dir),
        "-o",
        str(report_dir),
        "--clean",
    ]
