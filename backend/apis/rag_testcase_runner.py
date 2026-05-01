from fastapi import APIRouter, HTTPException, Depends
import logging
import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4
import shutil
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
import ast

from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_


from .projects_api import _ensure_project_structure, get_current_user, get_user_project
from utils.smart_ai_utils import ensure_smart_ai_module
from metrics.collector import collect_run_summary
from metrics.store import MetricsStore
from utils.allure_db import store_allure_results
from database.project_storage import DatabaseBackedProjectStorage
from database.session import get_db
from database.models import Project, User, ProjectFile
from utils.request_context import get_project_id as get_request_project_id
from utils.request_context import set_request_context, reset_request_context
from utils.project_paths import build_project_context, ProjectContext
from utils.allure_cli import build_allure_generate_cmd
from services.ac_evaluator import evaluate_acceptance_criteria

router = APIRouter()
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_MAX_CONCURRENCY = 4


def _reset_dir(directory: Path) -> None:
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=True)


def _generate_allure_report(
    results_dir: Path, report_dir: Path, cwd: Path, env: dict[str, str]
) -> None:
    try:
        cmd = build_allure_generate_cmd(results_dir, report_dir)
    except FileNotFoundError:
        raise HTTPException(
            status_code=501,
            detail="Allure CLI is not installed. Please install it so the report can be generated.",
        )
    result = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, capture_output=True)
    if result.returncode != 0:
        detail = result.stdout or result.stderr or "see server logs for details"
        raise HTTPException(
            status_code=500, detail=f"Allure report generation failed: {detail.strip()}"
        )


def _run_script_once(
    script_to_run: Path, src_dir: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script_to_run)],
        cwd=src_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _ui_script_requires_serial_execution(
    script_path: Path, planned_tests: list[str]
) -> bool:
    if len(planned_tests) <= 1:
        return False
    try:
        source = script_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        source = ""
    markers = (
        "playwright.sync_api",
        "playwright.async_api",
        "sync_playwright",
        "async_playwright",
        ".chromium.launch(",
        ".firefox.launch(",
        ".webkit.launch(",
        "browser.new_context(",
    )
    return any(marker in source for marker in markers)


def _run_script_parallel(
    script_to_run: Path,
    src_dir: Path,
    base_env: dict[str, str],
    test_names: list[str],
    max_workers: int,
    results_dir: Path,
) -> list[tuple[str, subprocess.CompletedProcess[str]]]:
    if not test_names:
        return []

    results: dict[str, subprocess.CompletedProcess[str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for test_name in test_names:
            env = base_env.copy()
            env.pop("SMARTAI_RUN_TAGS", None)
            env["SMARTAI_RUN_FUNCTIONS"] = test_name
            tmp_results = results_dir / f"tmp_{uuid4().hex}"
            tmp_results.mkdir(parents=True, exist_ok=True)
            env["ALLURE_RESULTS_DIR"] = str(tmp_results)
            future_map[executor.submit(_run_script_once, script_to_run, src_dir, env)] = (test_name, tmp_results)

        for future in as_completed(future_map):
            name, tmp_results = future_map[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = subprocess.CompletedProcess(
                    args=[sys.executable, str(script_to_run)],
                    returncode=1,
                    stdout="",
                    stderr=str(exc),
                )
            _merge_allure_results(tmp_results, results_dir)

    return [(name, results[name]) for name in test_names if name in results]


def _merge_allure_results(src_dir: Path, dest_dir: Path) -> None:
    try:
        if not src_dir.exists():
            return
        dest_dir.mkdir(parents=True, exist_ok=True)
        for item in src_dir.iterdir():
            if item.is_dir():
                shutil.copytree(item, dest_dir / item.name, dirs_exist_ok=True)
                continue
            target = dest_dir / item.name
            if target.exists():
                target = dest_dir / f"{item.stem}_{uuid4().hex}{item.suffix}"
            shutil.copy2(item, target)
    except Exception:
        pass
    finally:
        try:
            shutil.rmtree(src_dir, ignore_errors=True)
        except Exception:
            pass


class RunStoryTestRequest(BaseModel):
    project_id: Optional[int] = None
    tags: Optional[Union[list[str], dict[str, list[str]]]] = None
    tests_to_run: Optional[list[str]] = None
    test_plan: Optional[dict] = None
    change_set: Optional[dict] = None
    impact: Optional[dict] = None
    use_test_plan: Optional[Union[bool, dict[str, bool]]] = False
    parallel_execution: Optional[bool] = None


def _org_slug(name: str) -> str:
    normalized = (name or "").strip().lower()
    return re.sub(r"[^a-z0-9_-]+", "-", normalized) or "default"


def _project_dir_segment(project: Project) -> str:
    base_slug = (
        getattr(project, "slug", None) or Project.normalized_key(project.project_name)
    ).strip()
    base_slug = re.sub(r"[^a-z0-9_-]+", "-", base_slug.lower()) or "project"
    if project.id:
        return f"{project.id}-{base_slug}"
    return base_slug


def _project_root_dir(project: Project) -> Path:
    backend_root = Path(__file__).resolve().parents[1]
    org_segment = _org_slug(project.organization)
    org_root = backend_root / "organizations" / org_segment
    desired = org_root / _project_dir_segment(project)
    legacy = org_root / (project.project_name or "project")
    if desired.exists() or not legacy.exists():
        return desired
    return legacy


def _ensure_project_dirs(project: Project) -> dict[str, Path]:
    root = _project_root_dir(project)
    data_dir = root / "data"
    runs_dir = root / "generated_runs"
    src_dir = runs_dir / "src"
    root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "metadata").mkdir(parents=True, exist_ok=True)
    (src_dir / "ocr-dom-metadata").mkdir(parents=True, exist_ok=True)
    (src_dir / "pages").mkdir(parents=True, exist_ok=True)
    (src_dir / "tests").mkdir(parents=True, exist_ok=True)
    chroma_path = data_dir / "chroma_db"
    chroma_path.mkdir(parents=True, exist_ok=True)
    return {
        "project_root": root,
        "src_dir": src_dir,
        "chroma_path": chroma_path,
    }


def _activate_project_context(project_context: ProjectContext) -> dict:
    return set_request_context(project_context=project_context)


def _project_src_dir(project: Project) -> Path:
    return _project_root_dir(project) / "generated_runs" / "src"


def _candidate_src_dirs(project: Optional[Project] = None) -> list[Path]:
    dirs: list[Path] = []
    if project:
        try:
            proj_dirs = _ensure_project_dirs(project)
            dirs.append(proj_dirs["src_dir"])
        except Exception:
            pass
    # env_src = os.environ.get("SMARTAI_SRC_DIR")
    # if env_src:
    #     p = Path(env_src)
    #     if p.exists():
    #         dirs.append(p)
    #         print("dir from Project env" , dirs)
    # backend_root = Path(__file__).resolve().parents[1]
    # print("Backend Root" , backend_root)
    # for child in backend_root.iterdir():
    #     try:
    #         cand = child / "generated_runs" / "src"
    #         if cand.exists():
    #             dirs.append(cand)
    #             print("dir from Project csn" , dirs)
    #     except Exception:
    #         continue
    # org_root = backend_root / "organizations"
    # if org_root.exists():
    #     for sub in org_root.rglob("generated_runs"):
    #         try:
    #             src_dir = sub / "src"
    #             if src_dir.exists():
    #                 dirs.append(src_dir)
    #                 print("dir from Project env" , dirs)
    #         except Exception:
    #             continue
    # legacy = backend_root / "generated_runs" / "src"
    # print("legacy" , legacy)
    # if legacy.exists():
    #     dirs.append(legacy)
    seen = set()
    uniq: list[Path] = []
    for d in dirs:
        resolved = d.resolve()
        if resolved not in seen:
            uniq.append(d)
            seen.add(resolved)
    return uniq


def _script_category(path: Path) -> str:
    lowered = str(path).lower()
    if "accessibility" in lowered:
        return "accessibility"
    if "security" in lowered:
        return "security"
    return "ui"


def _extract_run_tags(script_path: Path) -> dict[str, list[str]]:
    try:
        text = script_path.read_text(encoding="utf-8")
    except Exception:
        return {}
    try:
        tree = ast.parse(text)
    except Exception:
        return {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "RUN_TAGS":
                try:
                    value = ast.literal_eval(node.value)
                except Exception:
                    return {}
                if isinstance(value, dict):
                    cleaned: dict[str, list[str]] = {}
                    for key, tags in value.items():
                        if not isinstance(key, str):
                            continue
                        tag_list = []
                        if isinstance(tags, (list, tuple)):
                            tag_list = [str(t).strip() for t in tags if str(t).strip()]
                        cleaned[key] = tag_list
                    return cleaned
    return {}


def _extract_run_functions(script_path: Path) -> list[str]:
    try:
        text = script_path.read_text(encoding="utf-8")
    except Exception:
        return []
    try:
        tree = ast.parse(text)
    except Exception:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("run_"):
            names.append(node.name)
    return names


def _normalize_run_names(items: list[str]) -> list[str]:
    names = []
    for item in items or []:
        raw = str(item or "").strip()
        if not raw:
            continue
        if raw.startswith("run_"):
            names.append(raw)
        elif raw.startswith("test_"):
            names.append("run_" + raw[len("test_") :])
        else:
            names.append(raw)
    return list(dict.fromkeys(names))


def _planned_tests_for_script(
    script_path: Path,
    selected_tags: list[str],
    allowed_run_names: Optional[list[str]] = None,
) -> list[str]:
    tags = {str(t).strip().lower() for t in (selected_tags or []) if str(t).strip()}
    run_tags = _extract_run_tags(script_path)
    run_names = (
        list(run_tags.keys()) if run_tags else _extract_run_functions(script_path)
    )
    if not run_names:
        return []
    if allowed_run_names:
        allowed_set = {name for name in allowed_run_names if name}
        return sorted([name for name in run_names if name in allowed_set])
    if "__all__" in tags:
        return sorted(run_names)
    if not tags:
        return sorted(run_names)
    planned = []
    for name in run_names:
        tag_list = [str(t).strip().lower() for t in run_tags.get(name, [])]
        if any(tag in tags for tag in tag_list):
            planned.append(name)
    return sorted(planned)


def _category_tests_dir(src_dir: Path, category_key: str) -> Path:
    tests_dir = src_dir / "tests"
    if category_key == "security":
        return tests_dir / "security_tests"
    if category_key == "accessibility":
        return tests_dir / "accessibility_tests"
    return tests_dir / "ui_scripts"


def _find_test_file_for_name(test_dir: Path, test_name: str) -> Optional[Path]:
    if not test_dir.exists():
        return None
    pattern = re.compile(
        rf"^def\s+{re.escape(test_name)}\s*\(\s*page\s*\)\s*:",
        re.MULTILINE,
    )
    for candidate in sorted(test_dir.rglob("test_*.py")):
        try:
            text = candidate.read_text(encoding="utf-8")
        except Exception:
            continue
        if pattern.search(text):
            return candidate
    return None


def _extract_run_index(script_path: Path) -> Optional[int]:
    for parent in script_path.parents:
        match = re.match(r"run_(\d+)$", parent.name)
        if match:
            return int(match.group(1))
    return None


def _filter_latest_run_scripts(
    scripts: list[tuple[Path, Path, str]],
) -> list[tuple[Path, Path, str]]:
    by_category: dict[str, list[tuple[Path, Path, str]]] = {}
    for entry in scripts:
        by_category.setdefault(entry[2], []).append(entry)
    filtered: list[tuple[Path, Path, str]] = []
    for category, items in by_category.items():
        run_indices = [
            idx
            for idx in (_extract_run_index(p) for _, p, _ in items)
            if idx is not None
        ]
        if not run_indices:
            filtered.extend(items)
            continue
        latest = max(run_indices)
        filtered.extend(
            [item for item in items if _extract_run_index(item[1]) == latest]
        )
    return filtered


def _find_backend_root(src_dir: Path) -> Optional[Path]:
    for parent in src_dir.resolve().parents:
        if parent.name == "backend":
            return parent
    return None


def _restore_project_test_files(project: Project, src_dir: Path, db: Session) -> int:
    """Restore test/page/lib python files from DB storage into the src dir."""
    if not project or not db:
        return 0
    prefixes = ("tests/", "pages/", "lib/")
    try:
        filters = [ProjectFile.path.like(f"{p}%") for p in prefixes]
        records = (
            db.query(ProjectFile)
            .filter(ProjectFile.project_id == project.id)
            .filter(or_(*filters))
            .all()
        )
    except Exception:
        return 0
    restored = 0
    for record in records:
        rel_path = (record.path or "").strip()
        if not rel_path or not rel_path.endswith(".py"):
            continue
        target = src_dir / rel_path
        if target.exists():
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            continue
        encoding = (record.encoding or "utf-8").lower()
        content = record.content or ""
        if encoding.startswith("base64"):
            try:
                import base64

                target.write_bytes(base64.b64decode(content))
                restored += 1
                continue
            except Exception:
                pass
        try:
            target.write_text(content, encoding=record.encoding or "utf-8")
            restored += 1
        except Exception:
            try:
                target.write_text(content, encoding="utf-8", errors="replace")
                restored += 1
            except Exception:
                continue
    return restored


def _scan_for_scripts(candidates: list[Path]) -> list[tuple[Path, Path]]:
    found: list[tuple[Path, Path]] = []
    for src in candidates:
        tdir = src / "tests"
        if not tdir.exists():
            continue
        for pattern in ("*_script_*.py", "*_script.py"):
            for f in tdir.rglob(pattern):
                if f.is_file():
                    found.append((src, f))
    if not found:
        for src in candidates:
            tdir = src / "tests"
            if not tdir.exists():
                continue
            for f in sorted(tdir.rglob("test_*.py")):
                if f.is_file():
                    found.append((src, f))
    return found


def _collect_scripts_to_run(
    project: Project,
    requested_tags: Optional[Union[list[str], dict[str, list[str]]]],
    use_test_plan: Union[bool, dict[str, bool]],
    db: Session | None = None,
) -> tuple[list[tuple[Path, Path, str]], dict[str, list[str]]]:
    candidates = _candidate_src_dirs(project)
    try:
        project_src = _project_src_dir(project).resolve()
    except Exception:
        project_src = None
    if project_src is not None:
        candidates = [c for c in candidates if c.resolve() == project_src]

    found = _scan_for_scripts(candidates)
    if not found and db is not None:
        try:
            _restore_project_test_files(project, _project_src_dir(project), db)
        except Exception:
            pass
        found = _scan_for_scripts(candidates)
    if not found:
        searched = (
            ", ".join(str((d / "tests").resolve()) for d in candidates)
            or "(no candidates)"
        )
        raise HTTPException(
            status_code=404,
            detail=f"No generated script files (*_script_*.py, test_*.py) found. Searched: {searched}",
        )

    scripts_to_run: list[tuple[Path, Path, str]] = []
    selected_by_category: dict[str, list[str]] = {}
    any_selected = False
    if isinstance(requested_tags, dict):
        for category, tags in requested_tags.items():
            tag_list = [str(t).strip() for t in (tags or []) if str(t).strip()]
            selected_by_category[category] = tag_list
            if tag_list:
                any_selected = True
    if any_selected:
        plan_scripts: list[tuple[Path, Path, str]] = []
        for src_dir, script_path in found:
            category_key = _script_category(script_path)
            if not selected_by_category.get(category_key):
                continue
            if _use_plan_for_category(use_test_plan, category_key):
                plan_scripts.append((src_dir, script_path, category_key))
                continue
            scripts_to_run.append((src_dir, script_path, category_key))
        if plan_scripts:
            scripts_to_run.extend(_filter_latest_run_scripts(plan_scripts))
    else:
        if (
            _use_plan_for_category(use_test_plan, "ui")
            or _use_plan_for_category(use_test_plan, "accessibility")
            or _use_plan_for_category(use_test_plan, "security")
        ):
            allowed_categories = {
                category
                for category in ("ui", "accessibility", "security")
                if _use_plan_for_category(use_test_plan, category)
            }
            plan_scripts = [
                (src_dir, script_path, category_key)
                for src_dir, script_path in found
                for category_key in (_script_category(script_path),)
                if category_key in allowed_categories
            ]
            scripts_to_run.extend(_filter_latest_run_scripts(plan_scripts))
        else:
            src_dir, latest_ui_script = sorted(
                found, key=lambda p: p[1].stat().st_mtime, reverse=True
            )[0]
            scripts_to_run.append(
                (src_dir, latest_ui_script, _script_category(latest_ui_script))
            )

    if not scripts_to_run:
        raise HTTPException(
            status_code=404, detail="No scripts matched the selected tag filters."
        )

    return scripts_to_run, selected_by_category


def _rotate_metadata_snapshots(meta_dir: Path) -> None:
    current_path = meta_dir / "new_snapshot.json"
    previous_path = meta_dir / "snapshot.json"
    if not current_path.exists():
        return
    try:
        payload = current_path.read_text(encoding="utf-8")
    except Exception:
        return
    try:
        previous_path.write_text(payload, encoding="utf-8")
    except Exception:
        return


def _load_test_plan(meta_dir: Path) -> Optional[dict]:
    path = meta_dir / "test_plan.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _resolve_plan_tests(
    requested_tests: Optional[list[str]],
    requested_plan: Optional[dict],
    meta_dir: Path,
    use_test_plan: bool,
) -> list[str]:
    if isinstance(requested_tests, list) and requested_tests:
        return requested_tests
    if isinstance(requested_plan, dict):
        plan_tests = requested_plan.get("tests_to_run") or []
        updated_tests = requested_plan.get("updated_tests") or []
        if plan_tests or updated_tests:
            return list(dict.fromkeys([*plan_tests, *updated_tests]))
    if not use_test_plan:
        return []
    plan_file = _load_test_plan(meta_dir)
    if isinstance(plan_file, dict):
        plan_tests = plan_file.get("tests_to_run") or []
        updated_tests = plan_file.get("updated_tests") or []
        if plan_tests or updated_tests:
            return list(dict.fromkeys([*plan_tests, *updated_tests]))
    return []


def _use_plan_for_category(
    use_test_plan: Union[bool, dict[str, bool]], category_key: str
) -> bool:
    if isinstance(use_test_plan, dict):
        return bool(use_test_plan.get(category_key))
    return bool(use_test_plan)


def _get_active_project(
    db: Session,
    requested_project_id: Optional[int] = None,
    current_user: Optional[User] = None,
) -> Project:
    if requested_project_id:
        if current_user is None:
            raise HTTPException(status_code=403, detail="Organization membership required")
        project = get_user_project(db, requested_project_id, current_user)
        if not project:
            raise HTTPException(
                status_code=404, detail=f"Project id {requested_project_id} not found"
            )
        return project

    request_pid = get_request_project_id()
    if request_pid is not None:
        if current_user is None:
            raise HTTPException(status_code=403, detail="Organization membership required")
        project = get_user_project(db, int(request_pid), current_user)
        if project:
            return project

    raise HTTPException(
        status_code=400,
        detail="project_id is required. Activate a project before running tests.",
    )


def _build_project_src_map(db: Session) -> dict[Path, Project]:
    mapping: dict[Path, Project] = {}
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    for project in projects:
        candidate = _project_src_dir(project)
        if not candidate.exists():
            continue
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if resolved not in mapping:
            mapping[resolved] = project
    return mapping


def _write_with_storage(
    path: Path,
    content: str,
    storage: Optional[DatabaseBackedProjectStorage],
    encoding: str = "utf-8",
) -> None:
    path.write_text(content, encoding=encoding)
    if not storage:
        return
    try:
        relative = path.relative_to(storage.base_dir)
    except ValueError:
        return
    storage.write_file(relative.as_posix(), content, encoding)


def _load_ac_inputs(meta_dir: Path) -> dict:
    inputs_path = meta_dir / "inputs.json"
    if not inputs_path.exists():
        return {}
    try:
        payload = json.loads(inputs_path.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}
    if isinstance(payload, list) and payload:
        return payload[0] if isinstance(payload[0], dict) else {}
    return payload if isinstance(payload, dict) else {}


def _extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s\"'<>]+", text or "")
    if not match:
        return ""
    return match.group(0).rstrip(").,")


def _infer_site_url(inputs: dict) -> str:
    site_url = (inputs.get("site_url") or "").strip()
    if site_url:
        return site_url
    story = str(inputs.get("user_story") or "")
    return _extract_first_url(story)


def _flatten_planned_tests(planned: list[dict]) -> list[str]:
    tests: list[str] = []
    for item in planned or []:
        if isinstance(item, dict):
            tests.extend(
                [str(name) for name in (item.get("tests") or []) if str(name).strip()]
            )
    return tests


def _evaluate_ac_from_metadata(
    meta_dir: Path, executed_tests: Optional[list[str]] = None
) -> dict:
    inputs = _load_ac_inputs(meta_dir)
    acceptance_criteria = inputs.get("acceptance_criteria") or []
    if not acceptance_criteria:
        return {"overall_status": "NO_AC", "details": []}

    site_url = _infer_site_url(inputs)
    if not site_url:
        return {
            "overall_status": "PARTIAL",
            "details": [
                {
                    "ac": str(item),
                    "status": "NOT_EVALUATED",
                    "reason": "Missing site_url for evaluation.",
                }
                for item in acceptance_criteria
            ],
        }

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(site_url)
            result = evaluate_acceptance_criteria(
                page, acceptance_criteria, executed_tests=executed_tests
            )
            browser.close()
        return result
    except Exception as exc:
        return {
            "overall_status": "PARTIAL",
            "details": [
                {
                    "ac": str(item),
                    "status": "NOT_EVALUATED",
                    "reason": f"AC evaluation failed: {exc}",
                }
                for item in acceptance_criteria
            ],
        }


@router.post("/{project_id}/rag/run-generated-story-test")
def run_latest_generated_story_test(
    project_id: int,
    payload: Optional[RunStoryTestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    projectDir = project_paths["project_root"]
    projectSrcDir = project_paths["src_dir"]
    projectChromaPath = project_paths["chroma_path"]
    project_context = build_project_context(current_user, project.id, db)
    tokens = set_request_context(project_context=project_context)
    try:
        requested_project_id = payload.project_id if payload else None
        requested_tags = payload.tags if payload else None
        requested_tests = payload.tests_to_run if payload else None
        requested_plan = payload.test_plan if payload else None
        requested_change_set = payload.change_set if payload else None
        requested_impact = payload.impact if payload else None
        use_test_plan = payload.use_test_plan if payload else False
        parallel_enabled = bool(payload.parallel_execution) if payload else False
        # project = _get_active_project(db, requested_project_id=requested_project_id)

        scripts_to_run, selected_by_category = _collect_scripts_to_run(
            project=project,
            requested_tags=requested_tags,
            use_test_plan=use_test_plan,
            db=db,
        )
        overall_logs = []
        results = []
        overall_status = "PASS"
        src_dirs: dict[Path, dict[str, Path]] = {}
        planned_tests = []
        planned_tests_to_run = []
        used_test_plan = requested_plan if isinstance(requested_plan, dict) else None
        ac_result = None
        first_meta_dir: Optional[Path] = None
        first_storage: Optional[DatabaseBackedProjectStorage] = None
        ui_parallel_jobs: list[dict] = []
        ui_parallel_across_scripts = False
        if parallel_enabled:
            ui_parallel_across_scripts = bool(requested_tags)
            if isinstance(requested_tests, list) and requested_tests:
                ui_parallel_across_scripts = len(requested_tests) > 1
        for src_dir, latest_ui_script, category_key in scripts_to_run:
            if src_dir not in src_dirs:
                results_dir = src_dir / "allure-results"
                report_dir = src_dir / "allure-report"
                _reset_dir(results_dir)
                _reset_dir(report_dir)
                src_dirs[src_dir] = {
                    "results_dir": results_dir,
                    "report_dir": report_dir,
                }
            storage = DatabaseBackedProjectStorage(project, src_dir, db)

            logs_dir = src_dir / "logs"
            meta_dir = src_dir / "metadata"
            logs_dir.mkdir(parents=True, exist_ok=True)
            meta_dir.mkdir(parents=True, exist_ok=True)
            if first_meta_dir is None:
                first_meta_dir = meta_dir
                first_storage = storage
            log_file = logs_dir / f"test_output_{latest_ui_script.stem}.log"
            meta_file = meta_dir / f"execution_metadata_{latest_ui_script.stem}.json"
            use_plan_for_category = _use_plan_for_category(use_test_plan, category_key)
            if use_plan_for_category and used_test_plan is None:
                plan_file = _load_test_plan(meta_dir)
                if isinstance(plan_file, dict):
                    used_test_plan = plan_file

            try:
                ensure_smart_ai_module(storage)
            except Exception:
                pass

            try:
                after_meta = meta_dir / "after_enrichment.json"
                before_meta = meta_dir / "before_enrichment.json"
                if not after_meta.exists():
                    content_to_write = "[]"
                    if before_meta.exists():
                        try:
                            content_to_write = before_meta.read_text(encoding="utf-8")
                        except Exception:
                            content_to_write = "[]"
                    _write_with_storage(after_meta, content_to_write, storage)
            except Exception:
                pass

            env = os.environ.copy()
            env.pop("SMARTAI_RUN_TAGS", None)
            env.pop("SMARTAI_RUN_FUNCTIONS", None)
            env["PYTHONPATH"] = str(src_dir)
            env["SMARTAI_SRC_DIR"] = str(src_dir)
            env["ALLURE_RESULTS_DIR"] = str(src_dirs[src_dir]["results_dir"])
            backend_root = _find_backend_root(src_dir)
            if backend_root:
                env["SMARTAI_BACKEND_ROOT"] = str(backend_root)
            selected = []
            if requested_tags and not (
                isinstance(requested_tests, list) and requested_tests
            ):
                if isinstance(requested_tags, dict):
                    selected = selected_by_category.get(category_key, []) or []
                elif isinstance(requested_tags, list):
                    selected = requested_tags
                selected = [str(tag).strip() for tag in selected if str(tag).strip()]
                if any(tag.lower() == "__all__" for tag in selected):
                    selected = []
                if selected:
                    env["SMARTAI_RUN_TAGS"] = ",".join(selected)

            plan_tests = _resolve_plan_tests(
                requested_tests, requested_plan, meta_dir, use_plan_for_category
            )
            normalized_plan = _normalize_run_names(plan_tests)
            if normalized_plan:
                planned_tests_to_run.extend(normalized_plan)
            if normalized_plan:
                env["SMARTAI_RUN_FUNCTIONS"] = ",".join(normalized_plan)

            planned = _planned_tests_for_script(
                latest_ui_script, selected, normalized_plan or None
            )
            test_dir = _category_tests_dir(src_dir, category_key)
            test_files = []
            for test_name in planned:
                lookup_name = test_name
                if lookup_name.startswith("run_"):
                    lookup_name = "test_" + lookup_name[len("run_") :]
                test_path = _find_test_file_for_name(test_dir, lookup_name)
                rel_path = None
                if test_path:
                    try:
                        rel_path = test_path.relative_to(src_dir).as_posix()
                    except ValueError:
                        rel_path = test_path.as_posix()
                test_files.append({"name": test_name, "path": rel_path})
            script_path = None
            try:
                script_path = latest_ui_script.relative_to(src_dir).as_posix()
            except ValueError:
                script_path = str(latest_ui_script)
            planned_tests.append(
                {
                    "category": category_key,
                    "script": str(latest_ui_script),
                    "script_path": script_path,
                    "tests": planned,
                    "test_files": test_files,
                }
            )
            if use_plan_for_category and not normalized_plan:
                overall_logs.append(
                    f"[{category_key}] Skipping {latest_ui_script} (no planned tests for run-only-updated)"
                )
                continue

            # Correctly determine the relative path of the script for execution
            script_to_run = latest_ui_script.relative_to(src_dir)
            force_serial_ui = (
                category_key == "ui"
                and _ui_script_requires_serial_execution(latest_ui_script, planned)
            )
            run_parallel_ui = (
                parallel_enabled
                and category_key == "ui"
                and planned
                and len(planned) > 1
                and not force_serial_ui
                and not ui_parallel_across_scripts
            )

            if (
                parallel_enabled
                and category_key == "ui"
                and ui_parallel_across_scripts
                and not force_serial_ui
            ):
                ui_parallel_jobs.append(
                    {
                        "src_dir": src_dir,
                        "script_path": latest_ui_script,
                        "script_to_run": script_to_run,
                        "category_key": category_key,
                        "env": env,
                        "planned": planned,
                        "log_file": log_file,
                        "meta_file": meta_file,
                        "storage": storage,
                        "results_dir": src_dirs[src_dir]["results_dir"],
                    }
                )
                continue

            if run_parallel_ui:
                parallel_results = _run_script_parallel(
                    script_to_run=script_to_run,
                    src_dir=src_dir,
                    base_env=env,
                    test_names=planned,
                    max_workers=UI_MAX_CONCURRENCY,
                    results_dir=src_dirs[src_dir]["results_dir"],
                )
                output_parts = []
                failures = 0
                for test_name, result in parallel_results:
                    output_parts.append(
                        "\n".join(
                            [
                                f"[{category_key}_runner] Parallel test: {test_name} (exit {result.returncode})",
                                result.stdout or "",
                                result.stderr or "",
                            ]
                        )
                    )
                    if result.returncode != 0:
                        failures += 1
                output = "\n\n".join(output_parts)
                status = "PASS" if failures == 0 else "FAIL"
            else:
                if force_serial_ui and parallel_enabled and len(planned) > 1:
                    overall_logs.append(
                        f"[{category_key}] Running {latest_ui_script.name} in serial mode because it launches a browser per testcase."
                    )
                result = _run_script_once(script_to_run, src_dir, env)
                output = result.stdout + "\n" + result.stderr
                status = "PASS" if result.returncode == 0 else "FAIL"

            _write_with_storage(log_file, output, storage)

            error_lines = []
            in_summary = False
            for line in output.splitlines():
                if "Summary of failures:" in line:
                    in_summary = True
                    continue
                if in_summary:
                    if line.strip().startswith("- "):
                        error_lines.append(line.strip())
                    if not line.strip():
                        break

            meta_payload = json.dumps(
                {"status": status, "timestamp": datetime.now().isoformat()},
                indent=2,
            )
            _write_with_storage(meta_file, meta_payload, storage)

            results.append(
                {
                    "status": status,
                    "log": output,
                    "errors": error_lines,
                    "executed_from": str(latest_ui_script),
                    "log_file": str(log_file),
                    "meta_file": str(meta_file),
                    "planned_tests": planned,
                }
            )
            overall_logs.append(f"[{category_key}] {latest_ui_script}\n{output}")
            if status != "PASS":
                overall_status = "FAIL"

        combined_log = "\n\n".join(overall_logs)
        executed_from = ", ".join(
            item.get("executed_from", "")
            for item in results
            if item.get("executed_from")
        )
        if ac_result is None and first_meta_dir is not None:
            executed_tests = sorted(set(planned_tests_to_run))
            if not executed_tests:
                executed_tests = sorted(set(_flatten_planned_tests(planned_tests)))
            ac_result = _evaluate_ac_from_metadata(
                first_meta_dir, executed_tests=executed_tests
            )
            if first_storage is not None:
                ac_path = first_meta_dir / "ac_results.json"
                _write_with_storage(
                    ac_path, json.dumps(ac_result, indent=2), first_storage
                )
        if parallel_enabled and ui_parallel_jobs:
            with ThreadPoolExecutor(max_workers=UI_MAX_CONCURRENCY) as executor:
                future_map = {}
                for job in ui_parallel_jobs:
                    if not job["planned"]:
                        continue
                    tmp_results = job["results_dir"] / f"tmp_{uuid4().hex}"
                    tmp_results.mkdir(parents=True, exist_ok=True)
                    env = job["env"].copy()
                    env["ALLURE_RESULTS_DIR"] = str(tmp_results)
                    future_map[
                        executor.submit(
                            _run_script_once,
                            job["script_to_run"],
                            job["src_dir"],
                            env,
                        )
                    ] = (job, tmp_results)

                job_outputs: dict[int, list[str]] = {}
                job_failures: dict[int, int] = {}
                for future in as_completed(future_map):
                    job, tmp_results = future_map[future]
                    job_id = id(job)
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = subprocess.CompletedProcess(
                            args=[sys.executable, str(job["script_path"])],
                            returncode=1,
                            stdout="",
                            stderr=str(exc),
                        )
                    _merge_allure_results(tmp_results, job["results_dir"])
                    output = "\n".join(
                        [
                            f"[{job['category_key']}_runner] Parallel script: {job['script_path'].name} (exit {result.returncode})",
                            result.stdout or "",
                            result.stderr or "",
                        ]
                    )
                    job_outputs.setdefault(job_id, []).append(output)
                    if result.returncode != 0:
                        job_failures[job_id] = job_failures.get(job_id, 0) + 1

                for job in ui_parallel_jobs:
                    if not job["planned"]:
                        continue
                    job_id = id(job)
                    output = "\n\n".join(job_outputs.get(job_id, []))
                    failures = job_failures.get(job_id, 0)
                    status = "PASS" if failures == 0 else "FAIL"

                    _write_with_storage(job["log_file"], output, job["storage"])

                    error_lines = []
                    in_summary = False
                    for line in output.splitlines():
                        if "Summary of failures:" in line:
                            in_summary = True
                            continue
                        if in_summary:
                            if line.strip().startswith("- "):
                                error_lines.append(line.strip())
                            if not line.strip():
                                break

                    meta_payload = json.dumps(
                        {"status": status, "timestamp": datetime.now().isoformat()},
                        indent=2,
                    )
                    _write_with_storage(job["meta_file"], meta_payload, job["storage"])

                    results.append(
                        {
                            "status": status,
                            "log": output,
                            "errors": error_lines,
                            "executed_from": str(job["script_path"]),
                            "log_file": str(job["log_file"]),
                            "meta_file": str(job["meta_file"]),
                            "planned_tests": job["planned"],
                        }
                    )
                    overall_logs.append(f"[{job['category_key']}] {job['script_path']}\n{output}")
                    if status != "PASS":
                        overall_status = "FAIL"
        if overall_status == "PASS":
            for src_dir, _, _ in scripts_to_run:
                _rotate_metadata_snapshots(src_dir / "metadata")
        for src_dir, paths in src_dirs.items():
            _generate_allure_report(
                results_dir=paths["results_dir"],
                report_dir=paths["report_dir"],
                cwd=src_dir,
                env=os.environ.copy(),
            )
            try:
                store_allure_results(db, project.id, paths["results_dir"])
            except Exception:
                logger.warning("Failed to store Allure results in DB for %s", src_dir)
            try:
                summary = collect_run_summary(paths["results_dir"])
                if summary:
                    history_path = src_dir / "history.json"
                    store = MetricsStore(project_id=project.id, history_path=history_path)
                    store.record_run(summary)
            except Exception:
                logger.warning("Failed to update metrics history for %s", src_dir)
        message = f"Execution {overall_status}"

        response = {
            "status": overall_status,
            "log": combined_log,
            "errors": [err for item in results for err in item.get("errors", [])],
            "executed_from": executed_from,
            "planned_tests": planned_tests,
            "planned_tests_to_run": sorted(set(planned_tests_to_run)),
            "project_id": project.id,
            "project_name": project.project_name,
            "results": results,
            "change_set": requested_change_set,
            "impact": requested_impact,
            "test_plan": used_test_plan,
            "ac": ac_result,
            "message": message,
        }
        return response

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        reset_request_context(tokens)


@router.post("/{project_id}/rag/preview-tests")
def preview_planned_tests(
    project_id: int,
    payload: Optional[RunStoryTestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_user_project(db, project_id, current_user)
    project_paths = _ensure_project_structure(project)
    projectDir = project_paths["project_root"]
    projectSrcDir = project_paths["src_dir"]
    projectChromaPath = project_paths["chroma_path"]
    project_context = build_project_context(current_user, project.id, db)
    tokens = set_request_context(project_context=project_context)
    try:
        requested_project_id = payload.project_id if payload else None
        requested_tags = payload.tags if payload else None
        requested_tests = payload.tests_to_run if payload else None
        requested_plan = payload.test_plan if payload else None
        use_test_plan = payload.use_test_plan if payload else False
        # project = _get_active_project(db, requested_project_id=requested_project_id)

        scripts_to_run, selected_by_category = _collect_scripts_to_run(
            project=project,
            requested_tags=requested_tags,
            use_test_plan=use_test_plan,
            db=db,
        )

        planned_tests = []
        planned_tests_to_run = []
        used_test_plan = requested_plan if isinstance(requested_plan, dict) else None
        tag_sets: dict[str, dict[str, set[str]]] = {}

        for src_dir, script_path, category_key in scripts_to_run:
            meta_dir = src_dir / "metadata"
            use_plan_for_category = _use_plan_for_category(use_test_plan, category_key)
            if use_plan_for_category and used_test_plan is None:
                plan_file = _load_test_plan(meta_dir)
                if isinstance(plan_file, dict):
                    used_test_plan = plan_file

            selected = []
            if requested_tags:
                if isinstance(requested_tags, dict):
                    selected = selected_by_category.get(category_key, []) or []
                elif isinstance(requested_tags, list):
                    selected = requested_tags
            selected = [str(tag).strip() for tag in selected if str(tag).strip()]

            plan_tests = _resolve_plan_tests(
                requested_tests, requested_plan, meta_dir, use_plan_for_category
            )
            normalized_plan = _normalize_run_names(plan_tests)
            if normalized_plan:
                planned_tests_to_run.extend(normalized_plan)

            planned = _planned_tests_for_script(
                script_path, selected, normalized_plan or None
            )
            test_dir = _category_tests_dir(src_dir, category_key)
            test_files = []
            for test_name in planned:
                lookup_name = test_name
                if lookup_name.startswith("run_"):
                    lookup_name = "test_" + lookup_name[len("run_") :]
                test_path = _find_test_file_for_name(test_dir, lookup_name)
                rel_path = None
                if test_path:
                    try:
                        rel_path = test_path.relative_to(src_dir).as_posix()
                    except ValueError:
                        rel_path = test_path.as_posix()
                test_files.append({"name": test_name, "path": rel_path})

            script_path_rel = None
            try:
                script_path_rel = script_path.relative_to(src_dir).as_posix()
            except ValueError:
                script_path_rel = str(script_path)

            planned_tests.append(
                {
                    "category": category_key,
                    "script": str(script_path),
                    "script_path": script_path_rel,
                    "tests": planned,
                    "test_files": test_files,
                }
            )

            run_tags = _extract_run_tags(script_path)
            if run_tags and planned:
                for run_name in planned:
                    for tag in run_tags.get(run_name, []) or []:
                        tag_sets.setdefault(category_key, {})
                        tag_sets[category_key].setdefault(tag, set()).add(run_name)

        tag_counts: dict[str, dict[str, int]] = {}
        for category, tags in tag_sets.items():
            tag_counts[category] = {tag: len(names) for tag, names in tags.items()}

        response = {
            "status": "OK",
            "planned_tests": planned_tests,
            "planned_tests_to_run": sorted(set(planned_tests_to_run)),
            "project_id": project.id,
            "project_name": project.project_name,
            "test_plan": used_test_plan,
            "tag_counts": tag_counts,
        }
        return response
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        reset_request_context(tokens)

