# # UI runner with per-run trace folders + deep diagnostics (Windows-safe)

# import os
# import json
# import time
# from datetime import datetime
# from pathlib import Path
# from playwright.sync_api import sync_playwright

# # === Your Page Objects & SmartAI hook ===
# from pages.customer_page_methods import *
# from pages.dashboard_page_methods import *
# from lib.smart_ai import patch_page_with_smartai

# # =========================
# # Config & Paths
# # =========================
# SLOWMO = int(os.getenv("UI_RUNNER_SLOWMO", "75"))                # medium pace
# ENABLE_TRACE = os.getenv("UI_RUNNER_ENABLE_TRACE", "1").lower() in ("1", "true", "yes")
# HOLD_SECS = int(os.getenv("UI_RUNNER_HOLD_AFTER", "0"))          # optionally hold page open
# # Allow overriding the trace root via env:
# TRACE_ROOT_ENV = os.getenv("UI_RUNNER_TRACE_ROOT", "").strip()

# # __file__ should point to tests/ui_script_*.py inside .../generated_runs/src/tests
# THIS_FILE = Path(__file__).resolve()
# TESTS_DIR = THIS_FILE.parent                     # .../generated_runs/src/tests
# SRC_ROOT = TESTS_DIR.parent                      # .../generated_runs/src
# REPO_ROOT = SRC_ROOT.parent                      # .../generated_runs
# META_PATH = SRC_ROOT / "metadata" / "after_enrichment.json"

# # Per-run folder (timestamp based)
# RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
# BASE_TRACE_DIR = Path(TRACE_ROOT_ENV).resolve() if TRACE_ROOT_ENV else (SRC_ROOT / "traces" / RUN_ID).resolve()
# BASE_TRACE_DIR.mkdir(parents=True, exist_ok=True)

# def scenario_dir(name: str) -> Path:
#     d = (BASE_TRACE_DIR / name).resolve()
#     d.mkdir(parents=True, exist_ok=True)
#     return d

# def debug_banner():
#     print("\n==================== DEBUG PATHS ====================")
#     print(f"__file__           : {THIS_FILE}")
#     print(f"cwd                : {Path.cwd().resolve()}")
#     print(f"SRC_ROOT           : {SRC_ROOT}")
#     print(f"TESTS_DIR          : {TESTS_DIR}")
#     print(f"REPO_ROOT          : {REPO_ROOT}")
#     print(f"META_PATH exists?  : {META_PATH.exists()}")
#     print(f"TRACE_ROOT_ENV     : {TRACE_ROOT_ENV or '(not set)'}")
#     print(f"BASE_TRACE_DIR     : {BASE_TRACE_DIR}")
#     print("=====================================================\n")

# def ls(path: Path, label: str):
#     try:
#         p = path.resolve()
#         print(f"[ls] {label} -> {p}")
#         if not p.exists():
#             print("     (path does not exist)")
#             return
#         for child in sorted(p.iterdir()):
#             kind = "DIR " if child.is_dir() else "FILE"
#             try:
#                 size = child.stat().st_size if child.is_file() else "-"
#             except Exception:
#                 size = "?"
#             print(f"     - {kind:4} {child.name:<40} size={size}")
#     except Exception as e:
#         print(f"[ls] {label} -> error: {e!r}")

# def patch_smartai(page):
#     try:
#         data = json.loads(META_PATH.read_text(encoding="utf-8"))
#         patch_page_with_smartai(page, data)
#         print(f"[SmartAI] applied from: {META_PATH}")
#     except Exception as e:
#         print(f"[SmartAI] skipped: {e!r}")

# def tracing_start(context):
#     if not ENABLE_TRACE:
#         print("[Trace] disabled via UI_RUNNER_ENABLE_TRACE=0")
#         return False
#     try:
#         context.tracing.start(screenshots=True, snapshots=True, sources=True)
#         print("[Trace] started")
#         return True
#     except Exception as e:
#         print(f"[Trace] start failed: {e!r}")
#         return False

# def tracing_stop(context, out_zip: Path):
#     out_zip = out_zip.resolve()
#     out_zip.parent.mkdir(parents=True, exist_ok=True)

#     # Write a sanity file so you can see the folder was writable
#     sanity = out_zip.parent / "_write_sanity.txt"
#     try:
#         sanity.write_text(f"sanity @ {time.time()}", encoding="utf-8")
#         print(f"[Sanity] wrote: {sanity}")
#     except Exception as e:
#         print(f"[Sanity] write failed in {out_zip.parent}: {e!r}")

#     try:
#         context.tracing.stop(path=str(out_zip))
#         time.sleep(0.3)  # small tick for FS flush on Windows
#         exists = out_zip.exists()
#         size = out_zip.stat().st_size if exists else 0
#         print(f"[Trace] stop -> {out_zip}  exists={exists} size={size}")
#         ls(out_zip.parent, "trace folder after stop")
#         if exists and size > 0:
#             print(f'[Trace] ✅ open with:\nplaywright show-trace "{out_zip}"')
#         else:
#             print("[Trace] ❌ zip not present/empty after stop()")
#     except Exception as e:
#         print(f"[Trace] stop failed: {e!r}")

# def run_scenario(label: str, steps_fn):
#     print(f"\n===== RUN {label} =====")
#     scen_dir = scenario_dir(label)
#     out_zip = scen_dir / "trace.zip"

#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=False, slow_mo=SLOWMO)
#         # video/screenshots optional: uncomment if you also want videos in same folder
#         # context = browser.new_context(record_video_dir=str(scen_dir))
#         context = browser.new_context()
#         started = tracing_start(context)
#         page = None
#         try:
#             page = context.new_page()
#             patch_smartai(page)
#             steps_fn(page)
#             if HOLD_SECS > 0:
#                 print(f"[Hold] keeping page open for {HOLD_SECS}s")
#                 time.sleep(HOLD_SECS)
#         finally:
#             if started:
#                 tracing_stop(context, out_zip)
#             try:
#                 context.close()
#             finally:
#                 browser.close()
#     print(f"===== DONE {label} =====")

# # =========================
# # Scenarios (your existing flows)
# # =========================
# def steps_positive(page):
#     page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
#     click_customers(page)
#     verify_add_customer_visible(page)
#     click_add_customer(page)

#     verify_full_name_visible(page)
#     enter_full_name(page, "John Doe")

#     verify_email_visible(page)
#     enter_email(page, "john.doe@example.com")

#     verify_phone_number_visible(page)
#     enter_phone_number(page, "1234567890")

#     verify_select_account_type_visible(page)
#     select_select_account_type(page, "Standard")

#     verify_address_visible(page)
#     enter_address(page, "123 Main St, Anytown, USA")

#     verify_occupation_visible(page)
#     enter_occupation(page, "Software Engineer")

#     verify_annual_income_visible(page)
#     enter_annual_income(page, "75000")

#     verify_initial_deposit_visible(page)
#     enter_initial_deposit(page, "1000")

#     click_add_customer(page)
#     enter_search_customers(page, "John Doe")
#     page.wait_for_timeout(1200)

# def steps_negative(page):
#     page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
#     click_customers(page)
#     verify_add_customer_visible(page)
#     click_add_customer(page)

#     verify_full_name_visible(page)
#     enter_full_name(page, "John Doe")

#     verify_email_visible(page)
#     enter_email(page, "john.doe@example")  # invalid email

#     verify_phone_number_visible(page)
#     enter_phone_number(page, "1234567890")

#     verify_select_account_type_visible(page)
#     select_select_account_type(page, "Standard")

#     verify_address_visible(page)
#     enter_address(page, "123 Main St, Anytown, USA")

#     verify_occupation_visible(page)
#     enter_occupation(page, "Software Engineer")

#     verify_annual_income_visible(page)
#     enter_annual_income(page, "75000")

#     verify_initial_deposit_visible(page)
#     enter_initial_deposit(page, "1000")

#     click_add_customer(page)
#     page.wait_for_timeout(1200)

# def steps_edge(page):
#     page.goto("https://preview--bank-buddy-crm-react.lovable.app/")
#     click_customers(page)
#     verify_add_customer_visible(page)
#     click_add_customer(page)

#     verify_full_name_visible(page)
#     enter_full_name(page, "J" * 256)  # very long name

#     verify_email_visible(page)
#     enter_email(page, "john.doe@example.com")

#     verify_phone_number_visible(page)
#     enter_phone_number(page, "1234567890")

#     verify_select_account_type_visible(page)
#     select_select_account_type(page, "Standard")

#     verify_address_visible(page)
#     enter_address(page, "123 Main St, Anytown, USA")

#     verify_occupation_visible(page)
#     enter_occupation(page, "Software Engineer")

#     verify_annual_income_visible(page)
#     enter_annual_income(page, "75000")

#     verify_initial_deposit_visible(page)
#     enter_initial_deposit(page, "1000")

#     click_add_customer(page)
#     page.wait_for_timeout(1200)

# # Public wrappers (names your harness expects)
# def run_positive_add_new_customer():
#     run_scenario("positive_add_new_customer", steps_positive)

# def run_negative_add_new_customer():
#     run_scenario("negative_add_new_customer", steps_negative)

# def run_edge_add_new_customer():
#     run_scenario("edge_add_new_customer", steps_edge)

# # =========================
# # Entry
# # =========================
# if __name__ == "__main__":
#     debug_banner()
#     print(f"[Info] Traces for this run go under:\n       {BASE_TRACE_DIR}\n")
#     ls(SRC_ROOT, "SRC_ROOT")
#     ls(SRC_ROOT / "traces", "SRC_ROOT/traces (pre-run)")

#     errors = []
#     for fn in [
#         run_positive_add_new_customer,
#         run_negative_add_new_customer,
#         run_edge_add_new_customer,
#     ]:
#         try:
#             fn()
#         except Exception as e:
#             print(f"[ERROR] {fn.__name__} failed: {e!r}")
#             errors.append({"function": fn.__name__, "error": str(e)})

#     print()
#     ls(SRC_ROOT / "traces", "SRC_ROOT/traces (post-run)")
#     ls(BASE_TRACE_DIR, "This run's trace root")
#     ls(BASE_TRACE_DIR / "positive_add_new_customer", "positive trace dir")
#     ls(BASE_TRACE_DIR / "negative_add_new_customer", "negative trace dir")
#     ls(BASE_TRACE_DIR / "edge_add_new_customer", "edge trace dir")

#     if errors:
#         print("\nSummary of failures:")
#         for e in errors:
#             print(f" - {e['function']} failed: {e['error']}")
#     else:
#         print("\nAll scenarios executed successfully!")

#     print("\nOpen a trace like this (copy the printed absolute path):")
#     print('playwright show-trace "<ABS_PATH>/trace.zip"')
