# utils/smart_ai_utils.py
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from database.project_storage import DatabaseBackedProjectStorage

SMART_AI_CODE = """

import os
from pathlib import Path
import json
import re

def _smartai_logs_dir() -> str:
    base = os.environ.get("SMARTAI_SRC_DIR")
    if base:
        path = Path(base) / "logs"
    else:
        project = os.environ.get("SMARTAI_PROJECT_DIR")
        if project:
            path = Path(project) / "generated_runs" / "src" / "logs"
        else:
            path = Path(__file__).resolve().parents[2] / "generated_runs" / "src" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _label_variants(label: str):
    base = (label or "").strip()
    if not base:
        return []
    variants = []
    seen = set()
    candidates = {base, re.sub(r"\s+", " ", base)}
    swap_candidates = [
        (" - ", ": "),
        ("-", ": "),
        ("-", ":"),
        (":", " - "),
        (":", " -"),
        (":", "-"),
    ]
    for src, dest in swap_candidates:
        if src in base:
            candidates.add(base.replace(src, dest))
    collapsed = re.sub(r"[^A-Za-z0-9]+", " ", base).strip()
    if collapsed:
        candidates.add(collapsed)
    for cand in candidates:
        cand = cand.strip()
        if not cand or cand in seen:
            continue
        variants.append(cand)
        seen.add(cand)
    return variants

# Optional ML dependencies for self-healing. Allow module import even when these
# packages are not installed (so tests that don't use ML healing can still run).
HAS_NUMPY = False
try:
    import numpy as np
    HAS_NUMPY = True
except Exception:
    np = None

# SentenceTransformers import is lazily attempted only if the env var
# SMARTAI_ENABLE_ML is set. Avoid importing heavy ML packages at module
# import time so simple runs are fast.
HAS_SENTENCE_TRANSFORMERS = False
SentenceTransformer = None
util = None


class SmartAILocatorError(Exception):
    pass


def _metadata_selector_variants(metadata_id):
    if not metadata_id:
        return []
    low = str(metadata_id).lower()
    pieces = {low}
    if "_" in low:
        pieces.add(low.split("_", 1)[-1])
    for marker in ("textbox_", "input_", "select_", "button_", "toggle_", "field_", "lookup_"):
        if marker in low:
            try:
                pieces.add(low.split(marker, 1)[1])
            except Exception:
                pass
    if "_field_" in low:
        try:
            pieces.add(low.split("_field_", 1)[0])
        except Exception:
            pass
    variants = []
    seen = set()
    for piece in pieces:
        piece = piece.strip("_- ")
        if not piece:
            continue
        candidates = {
            piece,
            piece.replace("_-_", "_"),
            piece.replace("__", "_"),
            piece.replace("_", ""),
            piece.replace("-", ""),
        }
        for cand in candidates:
            cand = cand.strip("_- ")
            if cand and cand not in seen:
                variants.append(cand)
                seen.add(cand)
            if len(variants) >= 12:
                break
        if len(variants) >= 12:
            break
    return variants


class SmartAIWrappedLocator:
    def __init__(self, locator, page, unique_name=None, healer=None):
        self._locator = locator
        self._page = page
        self._unique_name = unique_name
        # Optional reference back to the SmartAISelfHealing instance that
        # created this wrapper. Allows using metadata when performing
        # complex actions like combobox selection.
        self._healer = healer

    def fill(self, value, timeout=3000, max_retries=5, verify=True):
        import time
        locator = self._locator.first if hasattr(self._locator, 'first') else self._locator
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                # Debug: capture screenshot of target before filling
                try:
                    import os, time, re
                    logs_dir = _smartai_logs_dir()
                    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', (self._unique_name or 'unknown'))[:60]
                    ts = int(time.time() * 1000)
                    shot_path = os.path.join(logs_dir, f"debug_fill_{safe_name}_{ts}.png")
                    try:
                        # Prefer locator-level screenshot
                        locator.screenshot(path=shot_path)
                    except Exception:
                        try:
                            # full page screenshot fallback
                            self._page.screenshot(path=shot_path)
                        except Exception:
                            pass
                    print(f"[SmartAI][Debug] Saved fill target screenshot: {shot_path}")
                except Exception:
                    pass
                # Ensure we have the actual input/textarea or contenteditable to write into
                target = locator
                try:
                    tag = target.evaluate('el => el.tagName.toLowerCase()')
                except Exception:
                    tag = None
                if tag not in ('input', 'textarea'):
                    resolved = None
                    # search direct descendants for an editable node
                    try:
                        descendants = target.locator('input, textarea, [contenteditable="true"], [role="combobox"] input, [role="textbox"]')
                        if descendants and descendants.count() > 0:
                            resolved = descendants.first
                    except Exception:
                        resolved = None
                    # fallback: look within the nearest ancestor container that exposes an input
                    if not resolved:
                        try:
                            ancestor = target.locator('xpath=ancestor::*[.//input or .//textarea or .//*[@contenteditable="true"] or .//*[@role="textbox"]][1]')
                            if ancestor and ancestor.count() > 0:
                                inner = ancestor.first.locator('input, textarea, [contenteditable="true"], [role="combobox"], [role="textbox"]')
                                if inner and inner.count() > 0:
                                    resolved = inner.first
                        except Exception:
                            resolved = None
                    # fallback: use metadata label to locate a matching input elsewhere
                    if not resolved and self._healer and self._unique_name:
                        try:
                            meta = self._healer._find_by_unique_name(self._unique_name)
                        except Exception:
                            meta = None
                        label = ''
                        if meta:
                            label = (meta.get('get_by_text') or meta.get('label_text') or meta.get('placeholder') or '').strip()
                        if label:
                            variants = _label_variants(label) or [label]
                            matchers = []
                            for variant in variants:
                                var = variant.strip()
                                if not var:
                                    continue
                                low_var = var.lower()
                                norm_var = _normalize_for_match(var)
                                matchers.append((var, low_var, norm_var))
                            if not matchers:
                                matchers.append((label, label.lower(), _normalize_for_match(label)))
                            for original, _, _ in matchers:
                                try:
                                    by_label = self._page.get_by_label(original)
                                    if by_label and by_label.count() > 0:
                                        resolved = by_label.first
                                        break
                                except Exception:
                                    continue
                            if not resolved:
                                selectors = [
                                    "input[aria-label]",
                                    "input[placeholder]",
                                    "[role='textbox']",
                                    "textarea",
                                ]
                                for sel in selectors:
                                    try:
                                        candidates = self._page.locator(sel)
                                        cnt = candidates.count()
                                    except Exception:
                                        cnt = 0
                                    for idx in range(min(cnt, 10)):
                                        try:
                                            cand = candidates.nth(idx)
                                            txt = ''
                                            try:
                                                txt = (cand.get_attribute('aria-label') or cand.get_attribute('placeholder') or '').strip()
                                            except Exception:
                                                txt = ''
                                            if not txt:
                                                try:
                                                    txt = (cand.evaluate('el=>el.innerText||el.textContent') or '').strip()
                                                except Exception:
                                                    txt = ''
                                            if not txt:
                                                continue
                                            txt_low = txt.lower()
                                            txt_norm = _normalize_for_match(txt)
                                            matched = False
                                            for _, low_var, norm_var in matchers:
                                                if low_var and (low_var in txt_low or txt_low in low_var):
                                                    matched = True
                                                    break
                                                if norm_var and txt_norm and norm_var in txt_norm:
                                                    matched = True
                                                    break
                                            if matched:
                                                resolved = cand
                                                break
                                        except Exception:
                                            continue
                                    if resolved:
                                        break
                            if not resolved:
                                try:
                                    for _, low_var, _ in matchers:
                                        if not low_var:
                                            continue
                                        escaped = low_var.replace("'", "'")
                                        label_xpath = (
                                            "xpath=//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '"
                                            + escaped +
                                            "')]"
                                        )
                                        label_nodes = self._page.locator(label_xpath)
                                        lcount = label_nodes.count()
                                        for li in range(min(lcount, 5)):
                                            try:
                                                ln = label_nodes.nth(li)
                                                neighbor = ln.locator("xpath=following::*[@role='textbox' or self::input or self::textarea or @contenteditable='true'][1]")
                                                if neighbor and neighbor.count() > 0:
                                                    resolved = neighbor.first
                                                    break
                                            except Exception:
                                                continue
                                        if resolved:
                                            break
                                except Exception:
                                    pass
                    if resolved:
                        target = resolved

                # Scroll into view and focus
                try:
                    target.scroll_into_view_if_needed(timeout=timeout)
                except Exception:
                    pass
                try:
                    target.focus()
                except Exception:
                    try:
                        target.click(timeout=timeout)
                    except Exception:
                        try:
                            target.click(force=True, timeout=timeout)
                        except Exception:
                            pass

                # Clear existing value
                try:
                    target.fill("")
                except Exception:
                    try:
                        target.press("Control+A")
                        target.press("Backspace")
                    except Exception:
                        # last resort: set value via JS
                        try:
                            h = target.element_handle()
                            if h:
                                h.evaluate("el => { if('value' in el) el.value=''; else el.innerText=''; el.dispatchEvent(new Event('input',{bubbles:true})); }")
                        except Exception:
                            pass

                # Fill the value
                try:
                    target.fill(value, timeout=timeout)
                except Exception:
                    # fallback for contenteditable or stubborn inputs
                    try:
                        h = target.element_handle()
                        if h:
                            h.evaluate("(v) => { if('value' in this) { this.value = v; this.dispatchEvent(new Event('input',{bubbles:true})); } else { this.innerText = v; this.dispatchEvent(new Event('input',{bubbles:true})); } }", value)
                    except Exception:
                        pass
                # Small wait for any suggestion/lookup popup to appear, then try to
                # select a matching suggestion (Dynamics often shows a lookup list)
                try:
                    value_lower = (value or '').strip().lower()
                    # give UI a short moment to render suggestions
                    try:
                        self._page.wait_for_timeout(200)
                    except Exception:
                        pass
                    roots = [self._page]
                    try:
                        roots += list(getattr(self._page, 'frames', []))
                    except Exception:
                        pass
                    suggestion_clicked = False
                    for root in roots:
                        try:
                            # common suggestion/lookup containers and option roles
                            cand_opts = root.locator("[role='option'], [role='listitem'], [role='menuitem'], [role='menuitemradio'], [role='treeitem'], [role='gridcell'], [data-id*='lookup'], .ms-lookup, .lookup, .suggestion, .suggestions")
                            cnt = cand_opts.count() if cand_opts else 0
                            for oi in range(cnt):
                                try:
                                    o = cand_opts.nth(oi)
                                    if not o.is_visible(timeout=50):
                                        continue
                                    txt = ''
                                    try:
                                        txt = (o.get_attribute('aria-label') or o.get_attribute('title') or o.inner_text() or '').strip()
                                    except Exception:
                                        try:
                                            txt = (o.evaluate('el=>el.textContent') or '').strip()
                                        except Exception:
                                            txt = ''
                                    if not txt:
                                        continue
                                    tl = txt.lower()
                                    if value_lower and (value_lower in tl or tl in value_lower):
                                        try:
                                            o.click()
                                            suggestion_clicked = True
                                            break
                                        except Exception:
                                            try:
                                                h = o.element_handle()
                                                if h:
                                                    h.evaluate('el=>el.click()')
                                                    suggestion_clicked = True
                                                    break
                                            except Exception:
                                                pass
                                except Exception:
                                    continue
                            if suggestion_clicked:
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
                # Optionally, trigger blur/change events
                try:
                    locator.press("Tab")
                except Exception:
                    pass
                # Verify the value
                if verify:
                    actual = ""
                    try:
                        actual = target.input_value(timeout=timeout)
                    except Exception:
                        # fallback: try JS property
                        try:
                            actual = target.evaluate('el => el.value || el.innerText || el.textContent')
                        except Exception:
                            pass
                    if actual == value:
                        return
                    else:
                        print(f"[SmartAI][Debug] Fill attempt {attempt}: value not retained (got '{actual}', expected '{value}'). Retrying...")
                        time.sleep(0.3)
                        continue
                else:
                    return
            except Exception as e:
                last_error = e
                print(f"[SmartAI][Debug] Fill attempt {attempt} failed: {e}")
                time.sleep(0.3)
        raise Exception(f"Failed to fill textbox with value '{value}' after {max_retries} attempts. Last error: {last_error}")
    def click(self, **kwargs):
        locator = self._locator.first if hasattr(self._locator, 'first') else self._locator
        # Debug: capture screenshot of target before clicking and highlight
        try:
            import os, time, re
            logs_dir = _smartai_logs_dir()
            safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', (self._unique_name or 'unknown'))[:60]
            ts = int(time.time() * 1000)
            shot_path = os.path.join(logs_dir, f"debug_click_{safe_name}_{ts}.png")
            try:
                locator.screenshot(path=shot_path)
            except Exception:
                try:
                    # highlight element briefly for full page screenshot
                    try:
                        locator.evaluate("el => el.style.outline='3px solid red'; setTimeout(()=>el.style.outline='',2000);")
                    except Exception:
                        pass
                    self._page.screenshot(path=shot_path)
                except Exception:
                    pass
            print(f"[SmartAI][Debug] Saved click target screenshot: {shot_path}")
        except Exception:
            pass
        try:
            # Ensure visible and in view
            try:
                locator.scroll_into_view_if_needed()
            except Exception:
                pass
            try:
                locator.click(**kwargs)
                return
            except Exception:
                # try force click
                try:
                    locator.click(force=True, **kwargs)
                    return
                except Exception:
                    pass
            # try clicking a clickable descendant
            try:
                clickable = locator.locator('button,a,span,div')
                if clickable.count() > 0:
                    try:
                        clickable.first.click(**kwargs)
                        return
                    except Exception:
                        try:
                            clickable.first.click(force=True, **kwargs)
                            return
                        except Exception:
                            pass
            except Exception:
                pass
            # try element handle JS click
            try:
                h = locator.element_handle()
                if h:
                    h.evaluate('el => el.click()')
                    return
            except Exception:
                pass
            # as a last resort try clicking ancestor clickable
            try:
                anc = locator.locator('xpath=ancestor::button[1] | xpath=ancestor::a[1] | xpath=ancestor::li[1]')
                if anc and anc.count() > 0:
                    try:
                        anc.first.click(force=True)
                        return
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception as e:
            print(f"[SmartAI][Debug] click failed: {e}")
            raise
    # Proxy any unknown attribute/method calls to the underlying Playwright locator
    def __getattr__(self, name):
        # Intercept a few common actions to add waits/fallbacks, otherwise proxy
        # to the underlying Playwright locator.
        # Helper to get the concrete locator (prefer .first when available)
        def _get_concrete():
            return self._locator.first if hasattr(self._locator, 'first') else self._locator

        if name in ('_impl_obj', '_channel', '_sync'):
            return getattr(self._locator, name)

        if name == 'type':
            def _type_wrapper(text, delay=0, timeout=None):
                loc = _get_concrete()
                try:
                    loc.wait_for(state='visible', timeout=3000)
                except Exception:
                    pass
                try:
                    if timeout is not None:
                        return loc.type(text, delay=delay, timeout=timeout)
                    return loc.type(text, delay=delay)
                except Exception:
                    # fallback to fill when typing fails — use verify=True so
                    # lookup/typeahead selection logic in fill runs.
                    return self.fill(text, timeout=3000, verify=True)
            return _type_wrapper

        if name == 'press':
            def _press_wrapper(key):
                loc = _get_concrete()
                try:
                    loc.focus()
                except Exception:
                    try:
                        loc.wait_for(state='visible', timeout=1000)
                    except Exception:
                        pass
                try:
                    return loc.press(key)
                except Exception:
                    try:
                        # fallback to page keyboard
                        return self._page.keyboard.press(key)
                    except Exception:
                        raise
            return _press_wrapper

        if name == 'focus':
            def _focus_wrapper(timeout=None):
                loc = _get_concrete()
                try:
                    loc.scroll_into_view_if_needed(timeout=timeout or 1000)
                except Exception:
                    pass
                try:
                    if timeout is not None:
                        return loc.focus(timeout=timeout)
                    return loc.focus()
                except Exception:
                    try:
                        loc.click(timeout=timeout or 1000)
                    except Exception:
                        pass
                    return None
            return _focus_wrapper

        # Default: proxy to underlying locator attribute/method. If the
        # attribute we retrieve is itself a Locator-like object (for
        # example `.first` or `.last`), wrap it so subsequent calls still
        # go through SmartAIWrappedLocator and benefit from filling/
        # suggestion-selection behavior.
        try:
            attr = getattr(self._locator, name)
        except Exception:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        try:
            # Heuristic: if the attribute exposes locator-like methods,
            # return a wrapped locator rather than the raw Playwright one.
            if not callable(attr) and (hasattr(attr, 'type') or hasattr(attr, 'fill') or hasattr(attr, 'click')):
                return SmartAIWrappedLocator(attr, self._page, unique_name=self._unique_name, healer=self._healer)
        except Exception:
            pass
        return attr

    def select_option(self, value, timeout=2000):
        import time
        page = self._page

        def _normalize(text):
            return (text or '').strip().lower()

        def _relaxed(text):
            return ''.join(ch for ch in _normalize(text) if ch.isalnum())

        value_norm = _normalize(value)
        value_relaxed = _relaxed(value)

        def _matches_option_text(option_text):
            cand_norm = _normalize(option_text)
            cand_relaxed = _relaxed(option_text)
            if not cand_norm and not cand_relaxed:
                return False
            if value_norm and (cand_norm == value_norm or value_norm in cand_norm):
                return True
            if value_relaxed and cand_relaxed and (cand_relaxed == value_relaxed or value_relaxed in cand_relaxed):
                return True
            return False

        # Try clicking the locator to open any overlay
        try:
            self._locator.first.click(timeout=timeout)
        except Exception:
            pass

        # Try clicking an inner toggle if present (Dynamics pattern)
        try:
            inner_toggle = None
            try:
                inner_toggle = self._locator.first.locator('button, [role="button"], [data-id*="toggle"], .ms-Dropdown-toggle').first
            except Exception:
                inner_toggle = None
            if inner_toggle:
                try:
                    inner_toggle.click(timeout=timeout)
                except Exception:
                    try:
                        inner_toggle.click(force=True, timeout=timeout)
                    except Exception:
                        pass
        except Exception:
            pass

        # If native select, try selecting by option text/value
        try:
            tag = self._locator.first.evaluate('el => el.tagName && el.tagName.toLowerCase()')
            if tag == 'select':
                try:
                    opts = self._locator.first.locator('option')
                    cnt = opts.count()
                except Exception:
                    cnt = 0
                for i in range(cnt):
                    try:
                        o = opts.nth(i)
                        txt = (o.inner_text() or '').strip()
                        val = (o.get_attribute('value') or '').strip()
                        if txt == value or val == value or txt.lower() == value.lower() or val.lower() == value.lower():
                            try:
                                self._locator.first.select_option(value=val if val else txt)
                                return
                            except Exception:
                                pass
                    except Exception:
                        continue
        except Exception:
            pass

        # Search overlay roots (page + frames) but scope to the popup container when possible
        roots = [page]
        try:
            roots += list(getattr(page, 'frames', []))
        except Exception:
            pass

        # Try to identify a popup/container id referenced by the control (aria-controls/aria-owns)
        popup_ids = []
        try:
            try:
                ac = self._locator.first.get_attribute('aria-controls')
            except Exception:
                ac = None
            try:
                ao = self._locator.first.get_attribute('aria-owns')
            except Exception:
                ao = None
            try:
                # sometimes the interactive input/child has the aria attrs
                child_inp = None
                try:
                    child_inp = self._locator.first.locator('input, [role="combobox"], [aria-controls], [aria-owns]').first
                except Exception:
                    child_inp = None
                if child_inp:
                    try:
                        ac2 = child_inp.get_attribute('aria-controls')
                    except Exception:
                        ac2 = None
                    try:
                        ao2 = child_inp.get_attribute('aria-owns')
                    except Exception:
                        ao2 = None
                else:
                    ac2 = None; ao2 = None
            except Exception:
                ac2 = None; ao2 = None
            for v in (ac, ao, ac2, ao2):
                if v:
                    # aria-controls may contain space-separated ids; split
                    for pid in str(v).split():
                        pid = pid.strip()
                        if pid:
                            popup_ids.append(pid)
        except Exception:
            pass

        # Also consider any visible popup-like containers (aria-expanded=true) as candidates
        popup_candidate_selectors = [
            "[role='option']",
            "[role='menuitem']",
            "[role='menuitemradio']",
            "[role='listitem']",
            "[role='treeitem']",
            "[role='gridcell']",
            "[data-id*='lookup']",
            '.lookupItem',
            '.ms-ListItem',
            '.suggestion',
            '.suggestions',
            '.dropdown',
            '.ms-Dropdown-items'
        ]

        def _verify_after_click(control_locator):
            # verify that the control shows the expected value after selection
            try:
                # try to read input value or element text
                try:
                    v = control_locator.input_value(timeout=500)
                except Exception:
                    try:
                        v = control_locator.evaluate('el=>el.value || el.innerText || el.textContent')
                    except Exception:
                        v = None
                if v and _matches_option_text(v):
                    return True
            except Exception:
                pass
            return False

        # First, try scoping inside popup ids if we found any
        for pid in popup_ids:
            for root in roots:
                try:
                    try:
                        popup = root.locator(f"#{pid}")
                    except Exception:
                        popup = None
                    if not popup:
                        continue
                    # search for option candidates inside this popup only
                    combined = ', '.join(popup_candidate_selectors)
                    try:
                        items = popup.locator(combined)
                        total = items.count()
                    except Exception:
                        total = 0
                    for idx in range(total):
                        try:
                            it = items.nth(idx)
                            try:
                                if not it.is_visible(timeout=50):
                                    continue
                            except Exception:
                                pass
                            txt = ''
                            try:
                                txt = (it.get_attribute('aria-label') or it.get_attribute('title') or it.inner_text() or '').strip()
                            except Exception:
                                try:
                                    txt = (it.evaluate('el=>el.textContent') or '').strip()
                                except Exception:
                                    txt = ''
                            if not txt:
                                continue
                            if _matches_option_text(txt):
                                try:
                                    it.click(timeout=timeout)
                                except Exception:
                                    try:
                                        h = it.element_handle()
                                        if h:
                                            h.evaluate('el=>el.click()')
                                    except Exception:
                                        pass
                                # verify selection applied to the original control
                                try:
                                    if _verify_after_click(self._locator.first):
                                        return
                                except Exception:
                                    pass
                        except Exception:
                            continue
                except Exception:
                    continue

        # Next, search visible popup-like roots (aria-expanded or visible containers) to avoid unrelated lists
        for root in roots:
            try:
                # look for containers that are likely the open popup for this control
                popup_containers = []
                try:
                    # containers with aria-expanded=true or role=listbox, dialog, menu
                    popup_containers += list(root.locator("[aria-expanded='true']").all())
                except Exception:
                    pass
                try:
                    popup_containers += list(root.locator("[role='listbox']").all())
                except Exception:
                    pass
                try:
                    popup_containers += list(root.locator("[role='menu']").all())
                except Exception:
                    pass
                # ensure unique list
                seen = set()
                uniq_containers = []
                for c in popup_containers:
                    try:
                        outer = c.evaluate('el=>el.outerHTML')
                        if outer and outer not in seen:
                            seen.add(outer); uniq_containers.append(c)
                    except Exception:
                        continue

                for popup in uniq_containers:
                    try:
                        # search for option candidates inside this popup only
                        combined = ', '.join(popup_candidate_selectors)
                        try:
                            items = popup.locator(combined)
                            total = items.count()
                        except Exception:
                            total = 0
                        for idx in range(total):
                            try:
                                it = items.nth(idx)
                                try:
                                    if not it.is_visible(timeout=50):
                                        continue
                                except Exception:
                                    pass
                                txt = ''
                                try:
                                    txt = (it.get_attribute('aria-label') or it.get_attribute('title') or it.inner_text() or '').strip()
                                except Exception:
                                    try:
                                        txt = (it.evaluate('el=>el.textContent') or '').strip()
                                    except Exception:
                                        txt = ''
                                if not txt:
                                    continue
                                if _matches_option_text(txt):
                                    try:
                                        it.click(timeout=timeout)
                                    except Exception:
                                        try:
                                            h = it.element_handle()
                                            if h:
                                                h.evaluate('el=>el.click()')
                                        except Exception:
                                            pass
                                    try:
                                        if _verify_after_click(self._locator.first):
                                            return
                                    except Exception:
                                        pass
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                continue

        # Fallback: broad search across roots but verify after click to avoid picking unrelated items
        selectors = [
            "[role='option']",
            "[role='menuitem']",
            "[role='menuitemradio']",
            "[role='listitem']",
            "[role='treeitem']",
            "[role='gridcell']",
            'li',
            'tr',
            "div[role='option']",
            '.pa-item',
            '.fui-ListItem',
            '.lookupItem',
            '.ms-ListItem'
        ]
        for root in roots:
            try:
                combined = ', '.join(selectors)
                try:
                    items = root.locator(combined)
                    total = items.count()
                except Exception:
                    total = 0
                for idx in range(total):
                    try:
                        it = items.nth(idx)
                        try:
                            if not it.is_visible(timeout=50):
                                continue
                        except Exception:
                            pass
                        txt = ''
                        try:
                            txt = (it.get_attribute('aria-label') or it.get_attribute('title') or it.inner_text() or '').strip()
                        except Exception:
                            try:
                                txt = (it.evaluate('el=>el.textContent') or '').strip()
                            except Exception:
                                txt = ''
                        if not txt:
                            continue
                        if _matches_option_text(txt):
                            try:
                                it.click(timeout=timeout)
                            except Exception:
                                try:
                                    h = it.element_handle()
                                    if h:
                                        h.evaluate('el=>el.click()')
                                except Exception:
                                    pass
                            try:
                                if _verify_after_click(self._locator.first):
                                    return
                            except Exception:
                                pass
                    except Exception:
                        continue
            except Exception:
                continue

        # As a last-resort, set select value via JS for native selects
        try:
            for root in roots:
                try:
                    res = root.evaluate("(val) => { const sels = Array.from(document.querySelectorAll('select')); for(const s of sels){ for(const o of s.options){ if(o.text.trim().toLowerCase()===val.toLowerCase()|| (o.value||'').trim().toLowerCase()===val.toLowerCase()){ s.value = o.value; s.dispatchEvent(new Event('change',{bubbles:true})); return true } } } return false }", value)
                    if res:
                        return
                except Exception:
                    continue
        except Exception:
            pass

        # Final fallback: type the value directly and confirm with Enter for combo-box inputs
        try:
            target = self._locator.first
            try:
                typed_target = target.locator('input, [role="combobox"], [contenteditable="true"]').first
                if typed_target:
                    target = typed_target
            except Exception:
                pass
            try:
                target.click(timeout=timeout)
            except Exception:
                try:
                    target.click(force=True, timeout=timeout)
                except Exception:
                    pass
            try:
                target.fill(value)
            except Exception:
                try:
                    target.type(value, delay=30)
                except Exception:
                    try:
                        h = target.element_handle()
                        if h:
                            h.evaluate('(val) => { if("value" in this) { this.value = val; this.dispatchEvent(new Event("input",{bubbles:true})); } else { this.textContent = val; this.dispatchEvent(new Event("input",{bubbles:true})); } }', value)
                    except Exception:
                        pass
            try:
                target.press('Enter')
            except Exception:
                try:
                    self._page.keyboard.press('Enter')
                except Exception:
                    pass
            if _verify_after_click(self._locator.first):
                return
        except Exception:
            pass

        raise Exception(f"Option '{value}' not found in any visible dropdown.")



class SmartAISelfHealing:
    def __init__(self, metadata):
        self.metadata = metadata or []
        # Initialize ML model only if available; otherwise skip ML-based healing.
        if HAS_SENTENCE_TRANSFORMERS and HAS_NUMPY:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.embeddings = [
                    self.model.encode(self._element_to_string(e), convert_to_tensor=True, show_progress_bar=False)
                    for e in self.metadata
                ]
            except Exception as e:
                print(f"[SmartAI][Warn] Failed to initialize ML model: {e}")
                self.model = None
                self.embeddings = []
        else:
            self.model = None
            self.embeddings = []
        self.locator_fail_count = {}

    def _names_for_roles(self, element):
        names = []
        seen = set()
        for key in ("get_by_text", "label_text", "placeholder"):
            raw = (element.get(key) or "").strip()
            if not raw:
                continue
            variants = _label_variants(raw) or []
            for variant in variants:
                val = variant.strip()
                if val and val not in seen:
                    names.append(val)
                    seen.add(val)
        return names

    def _candidate_roles(self, element):
        ocr = (element.get("ocr_type") or "").lower()
        tag = (element.get("tag_name") or "").lower()
        roles = []
        if ocr in ("button", "submit", "iconbutton") or tag == "button":
            roles.append("button")
        if ocr in ("select", "dropdown", "combobox") or tag == "select":
            roles.append("combobox")
        if ocr in ("textbox", "text", "input", "email", "password") or tag in ("input", "textarea"):
            roles.append("textbox")
        if ocr in ("link", "anchor") or tag == "a":
            roles.append("link")
        for r in ("button", "combobox", "textbox", "link"):
            if r not in roles:
                roles.append(r)
        return roles

    def _evaluate_locator(self, locator):
        import time
        if locator is None:
            return False
        # Prefer visible + enabled elements. Use short timeouts to avoid long blocking
        try:
            try:
                # check visible quickly
                if locator.first.is_visible(timeout=200):
                    try:
                        if locator.first.is_enabled(timeout=200):
                            return True
                    except Exception:
                        # if enabled check fails, assume visible is sufficient
                        return True
            except Exception:
                # visibility check failed or timed out; fall back to count
                pass
        except Exception:
            # safety net: continue to count-based checks
            pass

        # fallback: quick count checks with short timeouts
        for _ in range(2):
            try:
                cnt = locator.count()
                if cnt and cnt > 0:
                    return True
                break
            except Exception:
                time.sleep(0.05)
        return False

    def _try_all_locators(self, element, page):
        strategies = []
        names = self._names_for_roles(element)
        if names:
            roles = self._candidate_roles(element)
            for nm in names:
                for role in roles:
                    strategies.append((lambda scope, nm=nm, role=role: scope.get_by_role(role, name=nm), f"get_by_role({role}, name={nm})"))
                # Attribute-based locator: prefer exact-match attributes rendered by Dynamics (data-text, id containing, data-lp-id, title, aria-label)
                def _attribute_locator(scope, nm=nm, element=element):
                    try:
                        lbl = (nm or '').strip()
                        if not lbl:
                            return None
                        low = lbl.lower()
                        # Try several XPath tests that are case-insensitive using translate
                        xpaths = [
                            "xpath=//*[@data-text and translate(normalize-space(@data-text), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '" + low.replace("'","'") + "']",
                            "xpath=//*[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '" + low.replace("'","'") + "')]",
                            "xpath=//*[contains(translate(@data-lp-id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '" + low.replace("'","'") + "')]",
                            "xpath=//*[@title and translate(normalize-space(@title), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '" + low.replace("'","'") + "']",
                            "xpath=//*[@aria-label and translate(normalize-space(@aria-label), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = '" + low.replace("'","'") + "']",
                            "xpath=//*[contains(translate(@data-id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '" + low.replace("'","'") + "')]",
                        ]
                        for xp in xpaths:
                            try:
                                loc = scope.locator(xp)
                                if loc and self._evaluate_locator(loc):
                                    return loc
                            except Exception:
                                continue
                    except Exception:
                        pass
                    return None
                strategies.append((lambda scope, nm=nm: _attribute_locator(scope, nm), f"attribute_match({nm})"))
                # Case-insensitive contains text search with clickable-ancestor resolution
                def _ci_clickable(scope, nm=nm):
                    low = nm.strip().lower()
                    xpath = (
                        "xpath=(//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '"
                        + low.replace("'","'")
                        + "')][not(self::script) and not(self::style)])"
                    )
                    # Enhanced clickable: allow <li> and descendants
                    clickable = "xpath=ancestor-or-self::*[(self::a or self::button or self::li or @role='link' or @role='button' or @role='menuitem' or @role='treeitem' or number(@tabindex) >= 0 or @data-id or @data-control-name or @data-lp-id)][1]"
                    try:
                        base = scope.locator(xpath)
                        candidates = base.locator(clickable)
                        # Filter for visible and clickable elements
                        filtered = []
                        count = candidates.count() if candidates else 0
                        for i in range(count):
                            try:
                                cand = candidates.nth(i)
                                if cand.is_visible(timeout=200):
                                    # Try to check if clickable by attempting to get bounding box
                                    if cand.bounding_box() is not None:
                                        filtered.append(cand)
                            except Exception:
                                pass
                        # Log outer HTML and attributes for all candidates
                        print(f"[SmartAI][Debug] Candidates for label '{nm}': {count} found, {len(filtered)} visible/clickable")
                        for i in range(count):
                            try:
                                cand = candidates.nth(i)
                                outer = cand.evaluate('el => el.outerHTML')
                                attrs = cand.evaluate('el => { let a={}; for(let attr of el.attributes){a[attr.name]=attr.value;} return a; }')
                                print(f"[SmartAI][Debug] Candidate[{i}] outerHTML: {outer[:300]} attrs: {attrs}")
                            except Exception:
                                pass
                        if filtered:
                            # If <li>, try to click it directly; else, find first clickable descendant
                            for cand in filtered:
                                tag = cand.evaluate('el => el.tagName.toLowerCase()')
                                if tag == 'li' or tag == 'button' or tag == 'a':
                                    return cand
                                # Try to find a clickable descendant
                                try:
                                    desc = cand.locator("button,a,span,div")
                                    if desc.count() > 0 and desc.is_visible(timeout=200):
                                        return desc
                                except Exception:
                                    pass
                            return filtered[0]
                        return candidates if count > 0 else scope.locator(xpath)
                    except Exception:
                        return scope.locator(xpath)
                strategies.append((lambda scope, nm=nm: _ci_clickable(scope, nm), f"clickable_text_ci({nm})"))
        if element.get("label_text"):
            strategies.append((lambda scope, label=element["label_text"]: scope.get_by_text(label, exact=True), f"get_by_text({element['label_text']}, exact=True)"))
            strategies.append((lambda scope, label=element["label_text"]: scope.get_by_text(label, exact=False), f"get_by_text({element['label_text']}, exact=False)"))
        data_attrs = element.get("data_attrs", {})
        for k, v in data_attrs.items():
            if "test" in k.lower() or "qa" in k.lower():
                strategies.append((lambda scope, v=v: scope.get_by_test_id(v), f"get_by_test_id({v}) for {k}"))
        if element.get("dom_id"):
            id_value = element["dom_id"]
            strategies.append((lambda scope, id_value=id_value: scope.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]"))
            strategies.append((lambda scope, id_value=id_value: scope.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]'))
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            strategies.append((lambda scope, class_sel=class_sel: scope.locator(class_sel), f"locator({class_sel}) [class exact]"))
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            strategies.append((lambda scope, sel=sel: scope.locator(sel), f"locator({sel}) [class_list]"))
        if element.get("locator") and element["locator"].get("type") == "css":
            strategies.append((lambda scope, css=element["locator"]["value"]: scope.locator(css), f"locator({element['locator']['value']}) [custom css]"))

        for func, desc in strategies:
            try:
                candidate = func(page)
            except Exception:
                candidate = None
            if self._evaluate_locator(candidate):
                print(f"[SmartAI][Return] {desc} succeeded.")
                self.locator_fail_count[element.get("unique_name")] = 0
                return candidate.first
            # short wait and retry
            try:
                page.wait_for_timeout(100)
                candidate = func(page)
                if self._evaluate_locator(candidate):
                    print(f"[SmartAI][Return] {desc} succeeded after short wait.")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return candidate.first
            except Exception:
                pass
            for frame in getattr(page, 'frames', []):
                try:
                    candidate = func(frame)
                except Exception:
                    candidate = None
                if self._evaluate_locator(candidate):
                    print(f"[SmartAI][Return] {desc} succeeded inside frame.")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return candidate.first
            unique_name = element.get("unique_name", "")
            self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
            print(f"[SmartAI][Skip] {desc} found no matching nodes.")
        print("[SmartAI][Return] No locator found for element.")
        return None


    def find_element(self, unique_name, page):
        import time
        element = self._find_by_unique_name(unique_name)
        # Try primary metadata and ML healing with retries for up to 15 seconds
        start = time.time()
        last_error = None
        attempt = 0
        while time.time() - start < 15.0:
            attempt += 1
            print(f"[SmartAI][Debug] Attempt {attempt} to find '{unique_name}'")
            if element:
                for _ in range(2):
                    locator = self._try_all_locators(element, page)
                    if locator:
                        # Validate locator against expected roles. If the element is
                        # expected to be a combobox but the found locator does not
                        # appear to be a select/combobox/listbox, skip it so that
                        # combobox-specific fallback will run.
                        try:
                            expected_roles = self._candidate_roles(element)
                        except Exception:
                            expected_roles = []
                        tag = None
                        role_attr = None
                        aria_haspopup = None
                        try:
                            tag = locator.evaluate('el => el.tagName && el.tagName.toLowerCase()')
                        except Exception:
                            tag = None
                        try:
                            role_attr = locator.get_attribute('role')
                        except Exception:
                            role_attr = None
                        try:
                            aria_haspopup = locator.get_attribute('aria-haspopup')
                        except Exception:
                            aria_haspopup = None

                        is_combobox_expected = 'combobox' in expected_roles
                        if is_combobox_expected:
                            try:
                                # quick checks for combobox-like elements
                                looks_like_combobox = False
                                if tag == 'select':
                                    looks_like_combobox = True
                                if role_attr and role_attr.lower() in ('combobox', 'listbox'):
                                    looks_like_combobox = True
                                if aria_haspopup and aria_haspopup.lower() in ('listbox', 'true'):
                                    looks_like_combobox = True
                                # also look for descendant options or inputs
                                try:
                                    if locator.locator("[role='option']").count() > 0:
                                        looks_like_combobox = True
                                except Exception:
                                    pass
                                try:
                                    if locator.locator('select, input, [role="combobox"]').count() > 0:
                                        looks_like_combobox = True
                                except Exception:
                                    pass
                                if not looks_like_combobox:
                                    print(f"[SmartAI][Debug] Candidate for '{unique_name}' found but does not look like combobox (tag={tag} role={role_attr} aria-haspopup={aria_haspopup}). Skipping this candidate to try combobox-specific fallback.")
                                    locator = None
                            except Exception:
                                # If validation errors occur, proceed to return the locator
                                pass

                        if locator:
                            is_textbox_expected = 'textbox' in expected_roles
                            if is_textbox_expected:
                                try:
                                    looks_like_textbox = False
                                    if tag in ('input', 'textarea'):
                                        looks_like_textbox = True
                                    if role_attr and role_attr.lower() in ('textbox', 'combobox'):
                                        looks_like_textbox = True
                                    try:
                                        if locator.locator('input, textarea, [contenteditable="true"], [role="textbox"]').count() > 0:
                                            looks_like_textbox = True
                                    except Exception:
                                        pass
                                    if not looks_like_textbox:
                                        print(f"[SmartAI][Debug] Candidate for '{unique_name}' found but does not look like textbox (tag={tag} role={role_attr}). Skipping this candidate to try textbox-specific fallback.")
                                        locator = None
                                except Exception:
                                    pass

                        if locator:
                            print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                            return SmartAIWrappedLocator(locator, page, unique_name, healer=self)
            element_ml, ml_score = self._ml_self_heal(unique_name)
            if element_ml:
                locator_ml = self._try_all_locators(element_ml, page)
                if locator_ml:
                    print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                    return SmartAIWrappedLocator(locator_ml, page, element_ml.get('unique_name'), healer=self)
            target_intent = element_ml.get("intent") if element_ml else None
            if target_intent:
                for e in self.metadata:
                    if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                        locator = self._try_all_locators(e, page)
                        if locator:
                                    print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                                    return SmartAIWrappedLocator(locator, page, e.get('unique_name'), healer=self)
            # Combobox-specific fallback: search frames for combobox widgets near the label
            try:
                for candidate in (element, element_ml):
                    try:
                        if not candidate:
                            continue
                        roles = self._candidate_roles(candidate)
                        lbl = (candidate.get('label_text') or candidate.get('get_by_text') or '').strip()
                        if lbl:
                            cb_loc = self._find_combobox_by_label_across_roots(lbl, page)
                            if cb_loc:
                                print(f"[SmartAI] Found combobox for label '{lbl}' via combobox-specific fallback.")
                                # pass the candidate's unique_name when available
                                cand_name = candidate.get('unique_name') if candidate else None
                                return SmartAIWrappedLocator(cb_loc, page, cand_name, healer=self)
                    except Exception as e:
                        last_error = e
                        continue
            except Exception as e:
                last_error = e
            # Re-check all frames/roots for the element
            try:
                frames = [page] + list(getattr(page, 'frames', []))
                for frame in frames:
                    try:
                        locator = self._try_all_locators(element, frame)
                        if locator:
                            print(f"[SmartAI][Debug] Found in frame/root on attempt {attempt}.")
                            return SmartAIWrappedLocator(locator, frame, element.get('unique_name') if element else None, healer=self)
                    except Exception as e:
                        print(f"[SmartAI][Debug] Frame/root search error: {e}")
            except Exception as e:
                print(f"[SmartAI][Debug] Error re-checking frames/roots: {e}")
            time.sleep(1)
        # Debug dump to help investigate why the element cannot be found
        print(f"[SmartAI][Debug] Failed to find '{unique_name}' after {attempt} attempts and {time.time()-start:.1f}s")
        self._debug_dump_context(unique_name, page)
        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

    def _debug_dump_context(self, unique_name, page):
        try:
            print(f"[SmartAI][Debug] Dumping context for '{unique_name}'")
            try:
                roots = [page] + [f for f in page.frames]
            except Exception:
                roots = [page]

            for r in roots:
                try:
                    url = getattr(r, 'url', '<url-unavailable>')
                except Exception:
                    url = '<url-unavailable>'
                print(f"[SmartAI][Debug] Root: {url}")
                try:
                    # case-insensitive search for label text in this frame
                    elem = next((e for e in self.metadata if e.get('unique_name')==unique_name), None)
                    label = (elem.get('label_text') or elem.get('get_by_text') or '') if elem else ''
                    if label:
                        low = label.strip().lower()
                        xpath = ("xpath=//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '"+low.replace("'","'")+"')]")
                        nodes = r.locator(xpath)
                        cnt = nodes.count()
                        print(f"[SmartAI][Debug] found {cnt} matching DOM nodes with label '{label}' in root {url}")
                        for i in range(min(5, cnt)):
                            try:
                                node = nodes.nth(i)
                                try:
                                    oh = node.evaluate('n=>n.outerHTML')
                                except Exception:
                                    oh = '<outerHTML-unavailable>'
                                try:
                                    bb = node.bounding_box()
                                except Exception:
                                    bb = None
                                print(f"[SmartAI][Debug] node[{i}] bbox={bb} html_snippet={oh[:300]}")
                            except Exception:
                                continue
                    # capture a screenshot and small HTML snippet for this root to help post-mortem
                    try:
                        import os, time, re
                        debug_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'debug')
                        try:
                            os.makedirs(debug_dir, exist_ok=True)
                        except Exception:
                            pass
                        ts = int(time.time() * 1000)
                        # sanitize url to a safe filename fragment
                        safe_url = (url or '').strip()
                        safe = re.sub(r'[^A-Za-z0-9._-]', '_', safe_url)[:80]
                        # sanitize unique_name too
                        safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', unique_name)[:60]
                        screenshot_path = os.path.join(debug_dir, f"smartai_{safe_name}_{safe}_{ts}.png")
                        html_path = os.path.join(debug_dir, f"smartai_{safe_name}_{safe}_{ts}.html")
                        wrote_screenshot = False
                        wrote_html = False
                        try:
                            # For frame-like roots, use frame.screenshot when available
                            if hasattr(r, 'screenshot'):
                                r.screenshot(path=screenshot_path)
                            else:
                                page.screenshot(path=screenshot_path)
                            wrote_screenshot = os.path.exists(screenshot_path)
                        except Exception as e:
                            print(f"[SmartAI][Debug] screenshot failed for root {url}: {e}")
                        try:
                            # grab outerHTML up to a reasonable limit
                            html = None
                            try:
                                html = r.evaluate('() => document.documentElement.outerHTML')
                            except Exception:
                                try:
                                    html = page.evaluate('() => document.documentElement.outerHTML')
                                except Exception:
                                    html = '<outerHTML-unavailable>'
                            with open(html_path, 'w', encoding='utf-8') as fh:
                                fh.write((html or '')[:20000])
                            wrote_html = os.path.exists(html_path)
                        except Exception as e:
                            print(f"[SmartAI][Debug] html dump failed for root {url}: {e}")
                        try:
                            if wrote_screenshot:
                                print(f"[SmartAI][Debug] saved screenshot: {screenshot_path}")
                            if wrote_html:
                                print(f"[SmartAI][Debug] saved html snippet: {html_path}")
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[SmartAI][Debug] error while dumping root {url}: {e}")
        except Exception:
            pass

    def _find_combobox_by_label_across_roots(self, label, page):
        roots = [page]
        try:
            for f in page.frames:
                if f not in roots:
                    roots.append(f)
        except Exception:
            pass

        low = label.strip().lower()
        for root in roots:
            # find comboboxes
            try:
                combs = root.get_by_role('combobox')
            except Exception:
                try:
                    combs = root.locator("[role='combobox']")
                except Exception:
                    combs = None

            if not combs:
                continue

            try:
                ccount = combs.count()
            except Exception:
                ccount = 0

            for i in range(ccount):
                try:
                    c = combs.nth(i)
                    # check nearest label/ancestor text
                    try:
                        txt = (c.inner_text() or '').strip().lower()
                    except Exception:
                        txt = ''
                    if low in txt:
                        return c.first
                    # check preceding label/sibling
                    try:
                        sib = c.locator('xpath=preceding::label[1] | xpath=ancestor::label[1]')
                        if sib and sib.count() > 0:
                            try:
                                stext = (sib.first.inner_text() or '').strip().lower()
                            except Exception:
                                stext = ''
                            if low in stext:
                                return c.first
                    except Exception:
                        pass
                except Exception:
                    continue

                # If direct combobox search failed, try locating by label node then finding nearby control
                # any element whose text contains the label (case-insensitive)
                label_xpath = (
                    "xpath=//*[contains(translate(normalize-space(string(.)), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '"
                    + low.replace("'", "'")
                    + ")]"
                )
                lbl_nodes = root.locator(label_xpath)
                lcount = 0
                try:
                    lcount = lbl_nodes.count()
                except Exception:
                    lcount = 0
                for j in range(min(10, lcount)):
                    try:
                        ln = lbl_nodes.nth(j)
                        # search following siblings/descendants for a likely control
                        candidates_sel = (
                            "xpath=following::*[@role='combobox' or @aria-haspopup or @aria-controls or @aria-owns or self::select or self::input][1]"
                        )
                        try:
                            cand = ln.locator(candidates_sel)
                            if cand and cand.count() > 0:
                                return cand.first
                        except Exception:
                            pass
                        # try ancestor container then descendants
                        try:
                            container = ln.locator('xpath=ancestor::*[self::div or self::section or self::td or self::li][1]')
                            if container and container.count() > 0:
                                inner = container.first.locator("[role='combobox'], button[aria-haspopup], [aria-controls], [aria-owns], select, input")
                                try:
                                    if inner and inner.count() > 0:
                                        return inner.first
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    except Exception:
                        continue
        return None

    def _find_by_unique_name(self, unique_name):
        return next((e for e in self.metadata if e.get("unique_name") == unique_name), None)

    def _map_tag_to_role(self, tag):
        tag_role_map = {
            'button': 'button',
            'input': 'textbox',
            'select': 'combobox',
            'textarea': 'textbox',
            'checkbox': 'checkbox'
        }
        return tag_role_map.get(tag.lower(), None)

    def _ml_self_heal(self, unique_name):
        # If ML model isn't available, skip ML healing.
        if not self.model or not self.embeddings:
            return (None, 0.0)
        try:
            query_embedding = self.model.encode(unique_name, convert_to_tensor=True, show_progress_bar=False)
            scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
            best_idx = int(np.argmax(scores)) if scores else -1
            best_score = scores[best_idx] if best_idx >= 0 else 0.0
            print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
            return (self.metadata[best_idx], best_score) if best_idx >= 0 and best_score > 0.6 else (None, best_score)
        except Exception as e:
            print(f"[SmartAI][Warn] ML healing failed: {e}")
            return (None, 0.0)

    def _element_to_string(self, element):
        fields = [
            element.get('unique_name', ''),
            element.get('label_text', ''),
            element.get('intent', ''),
            element.get('ocr_type', ''),
            element.get('element_type', ''),
            element.get('tag_name', ''),
            element.get('placeholder', ''),
            ' '.join(element.get('class_list', []) or []),
            ' '.join(f"{k}:{v}" for k, v in (element.get('data_attrs', {}) or {}).items()),
            element.get('sample_value', ''),
        ]
        return ' '.join([str(f) for f in fields if f])


def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata or [])
    def smartAI(unique_name):
        return ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page 

"""

def get_smartai_src_dir() -> Path:
    """
    Resolve the base src directory where generated SmartAI artifacts (lib/pages/tests)
    should live. Priority order:
      1. SMARTAI_SRC_DIR env var (explicit override).
      2. SMARTAI_PROJECT_DIR/generated_runs/src (active project scope).
      3. backend/generated_runs/src (repo-scoped default).
      4. generated_runs/src at repo root (legacy fallback).
      5. testfiles/generated_runs/src (legacy test data).
    The first existing path wins; if none exist yet we return the first candidate so
    callers create it on demand.
    """
    env_src = os.environ.get("SMARTAI_SRC_DIR")
    if env_src:
        return Path(env_src)

    candidates: list[Path] = []
    project_root = os.environ.get("SMARTAI_PROJECT_DIR")
    if project_root:
        candidates.append(Path(project_root) / "generated_runs" / "src")

    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend([
        repo_root / "backend" / "generated_runs" / "src",
        repo_root / "generated_runs" / "src",
        repo_root / "testfiles" / "generated_runs" / "src",
    ])

    for cand in candidates:
        if cand.exists():
            return cand

    return candidates[0] if candidates else Path.cwd()

def _persist_storage_file(storage: Optional["DatabaseBackedProjectStorage"], path: Path, content: str) -> None:
    if not storage:
        return
    try:
        relative = path.relative_to(storage.base_dir)
    except ValueError:
        return
    storage.write_file(relative.as_posix(), content, "utf-8")


def ensure_smart_ai_module(storage: Optional["DatabaseBackedProjectStorage"] = None):
    src_dir = get_smartai_src_dir()
    src_dir.mkdir(parents=True, exist_ok=True)

    lib_path = src_dir / "lib"
    lib_path.mkdir(parents=True, exist_ok=True)
    init_file = lib_path / "__init__.py"
    init_content = ""
    init_file.write_text(init_content, encoding="utf-8")
    _persist_storage_file(storage, init_file, init_content)

    smart_ai_file = lib_path / "smart_ai.py"
    smart_ai_file.write_text(SMART_AI_CODE, encoding="utf-8")
    _persist_storage_file(storage, smart_ai_file, SMART_AI_CODE)
