# backend/services/accessibility_test_utils.py
import json
from pathlib import Path

from playwright.sync_api import Page
from axe_playwright_python.sync_playwright import Axe


def _unwrap_page(page: Page):
    """
    Returns the underlying Playwright page implementation if the page was patched.
    """
    return getattr(page, "_locator", page)


def _results_to_dict(results) -> dict:
    """
    Normalize AxeResults into a serializable dict shape.
    The axe_playwright_python library stores raw data on `.response`.
    """
    if isinstance(results, dict):
        return results
    response = getattr(results, "response", None)
    if isinstance(response, dict):
        return response
    return {}


def run_accessibility_scan(
    page: Page,
    file_path: Path | str | None = None,
):
    """
    Runs an Axe accessibility scan on the current page and saves the results to a file.
    Returns the raw AxeResults object, with convenience attributes patched in.
    """
    axe = Axe()
    actual_page = _unwrap_page(page)

    target_path = Path(file_path) if file_path else Path.cwd() / "accessibility_results.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)

    results = axe.run(actual_page)
    results_dict = _results_to_dict(results)

    violations = results_dict.get("violations", []) or []
    passes = results_dict.get("passes", []) or []
    incomplete = results_dict.get("incomplete", []) or []
    inapplicable = results_dict.get("inapplicable", []) or []

    # Patch convenience attributes for older call sites/tests.
    for name, value in (
        ("violations", violations),
        ("passes", passes),
        ("incomplete", incomplete),
        ("inapplicable", inapplicable),
        ("timestamp", results_dict.get("timestamp")),
        ("url", results_dict.get("url")),
    ):
        try:
            setattr(results, name, value)
        except Exception:
            pass

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "violations": violations,
                "passes": passes,
                "incomplete": incomplete,
                "inapplicable": inapplicable,
                "timestamp": results_dict.get("timestamp"),
                "url": results_dict.get("url"),
            },
            f,
            indent=2,
        )

    if violations:
        print(
            f"Accessibility violations found on page {actual_page.url} "
            f"and saved to {target_path}"
        )
    else:
        print(f"No accessibility violations found on page {actual_page.url}")

    return results
