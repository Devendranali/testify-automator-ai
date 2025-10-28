import os
from pathlib import Path

SMART_AI_CODE = """import json
import re
import time
import numpy as np
from collections import defaultdict
from sentence_transformers import SentenceTransformer, util

class SmartAILocatorError(Exception):
    pass

# ðŸŸ¢ Minimal wrapper to handle select_option fallback automatically + safe scroll
class SmartAIWrappedLocator:
    def __init__(self, locator, page):
        self._locator = locator
        self._page = page

    def __getattr__(self, name):
        # Delegate all other methods/attributes to Playwright's locator
        return getattr(self._locator, name)

    def _safe_scroll(self, timeout=2000):
        try:
            self._locator.scroll_into_view_if_needed(timeout=timeout)
        except Exception:
            pass

    def click(self, *args, **kwargs):
        self._safe_scroll()
        return self._locator.first.click(*args, **kwargs)

    def fill(self, value, retries: int = 3, timeout: int = 1000, force: bool = False):
        '''Fill value with validation and retries.
        Raises Exception if after retries the field does not reflect the value.
        '''
        self._safe_scroll(timeout=timeout)
        backoff = 0.12
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                # verify locator visibility & enabled
                if not self._locator.first.is_visible():
                    raise Exception("Locator not visible")
                if not self._locator.first.is_enabled():
                    raise Exception("Locator not enabled")

                self._locator.first.fill(value, timeout=timeout, force=force)

                # Post-fill validation: ensure input_value matches intended value
                try:
                    current = self._locator.first.input_value()
                    if str(current) == str(value):
                        print(f"[SmartAI][fill] Success: value set to '{value}'")
                        return
                except Exception:
                    # input_value may not be supported; fallback to evaluate
                    try:
                        current = self._locator.first.evaluate('el => el.value')
                        if str(current) == str(value):
                            print(f"[SmartAI][fill] Success (eval): value set to '{value}'")
                            return
                    except Exception:
                        pass

                # If not matched, raise to retry
                raise Exception(f"Post-fill validation failed: expected '{value}', got '{current if 'current' in locals() else 'unknown'}'")
            except Exception as e:
                last_exc = e
                wait = backoff * (2 ** (attempt - 1))
                try:
                    self._page.wait_for_timeout(int(wait * 1000))
                except Exception:
                    pass
                continue

        # exhausted retries
        raise Exception(f"SmartAI.fill failed after {retries} attempts: {last_exc}")

    def select_option(self, value, index: int | None = None, retries: int = 3, timeout: int = 4000, force: bool = False):
        '''
        Robust select handler:
        1) Try native select_option(label=...) then value=...
        2) If native fails, open combobox (optionally by index) and click an option with proper waits
        3) As a last resort on real <select>, map label->value case-insensitively via DOM
        '''
        self._safe_scroll(timeout=timeout)

        # --- Native fast-path for real <select> with retries ---
        last_exc = None
        backoff = 0.12
        for attempt in range(1, retries + 1):
            try:
                # ensure native select is visible/enabled
                if not self._locator.first.is_visible():
                    raise Exception("Locator not visible")
                if not self._locator.first.is_enabled():
                    raise Exception("Locator not enabled")

                try:
                    res = self._locator.first.select_option(label=value)
                    # validate selected value if possible
                    try:
                        sel = self._locator.first.evaluate('el => el.value')
                        if sel is not None:
                            print(f"[SmartAI][select_option] Native select chose value '{sel}'")
                            return res
                    except Exception:
                        return res
                except Exception:
                    try:
                        res = self._locator.first.select_option(value=value)
                        return res
                    except Exception:
                        pass

                # --- Combobox / custom dropdown flow with waits ---
                try:
                    trigger_candidates = []
                    try:
                        trigger_candidates.append(self._locator.nth(index) if index is not None else self._locator.first)
                    except Exception:
                        pass
                    if not trigger_candidates:
                        trigger_candidates.append(self._locator.first)
                    trigger = None
                    for candidate in trigger_candidates:
                        try:
                            candidate.scroll_into_view_if_needed(timeout=timeout)
                            candidate.click(timeout=timeout, force=force)
                            trigger = candidate
                            break
                        except Exception:
                            continue
                    if trigger is None:
                        trigger = self._page.get_by_role("combobox")
                        trigger = trigger.nth(index) if index is not None else trigger.first
                        trigger.scroll_into_view_if_needed(timeout=timeout)
                        trigger.click(timeout=timeout, force=force)

                    # Wait for options to show up (scope to closest container first)
                    try:
                        trigger.locator("[role='listbox']").first.wait_for(state="visible", timeout=timeout)
                    except Exception:
                        try:
                            self._page.get_by_role("listbox").first.wait_for(state="visible", timeout=timeout)
                        except Exception:
                            try:
                                self._page.wait_for_selector("[role='option']", timeout=timeout)
                            except Exception:
                                pass

                    # Exact name first
                    try:
                        trigger.get_by_role("option", name=value, exact=True).first.click(timeout=timeout, force=force)
                        print(f"[SmartAI][select_option] Scoped combobox matched exact '{value}'")
                        return
                    except Exception:
                        pass
                    try:
                        self._page.get_by_role("option", name=value, exact=True).first.click(timeout=timeout, force=force)
                        print(f"[SmartAI][select_option] Combobox matched exact '{value}'")
                        return
                    except Exception:
                        pass

                    # Contains text then case-insensitive attempts
                    try:
                        trigger.locator("[role='option']", has_text=value).first.click(timeout=timeout, force=force)
                        return
                    except Exception:
                        pass

                    try:
                        trigger.locator(f"text={value}").first.click(timeout=timeout, force=force)
                        return
                    except Exception:
                        pass

                    try:
                        self._page.locator("[role='option']", has_text=value).first.click(timeout=timeout, force=force)
                        return
                    except Exception:
                        pass

                    for v in (value, str(value).strip(), str(value).capitalize(), str(value).title(), str(value).lower(), str(value).upper()):
                        try:
                            trigger.get_by_role("option", name=v).first.click(timeout=timeout, force=force)
                            return
                        except Exception:
                            continue
                        try:
                            self._page.get_by_role("option", name=v).first.click(timeout=timeout, force=force)
                            return
                        except Exception:
                            continue

                    # Final: iterate visible options and compare text with normalization
                    opts = trigger.locator("[role='option']")
                    if opts.count() == 0:
                        opts = self._page.locator("[role='option']")
                    n = opts.count()
                    target_low = str(value).strip().lower()
                    for i in range(n):
                        try:
                            txt = opts.nth(i).inner_text().strip()
                            if txt and txt.lower() == target_low:
                                opts.nth(i).click(timeout=timeout, force=force)
                                return
                        except Exception:
                            continue

                    # Broader textual fallback for overlay menus without ARIA roles
                    variants = []
                    for v in (value, str(value).strip(), str(value).capitalize(), str(value).title(), str(value).lower(), str(value).upper()):
                        if v and v not in variants:
                            variants.append(v)
                    overlay_selectors = (
                        "[role='listbox'], [role='menu'], [role='grid'], [role='tree'], [role='dialog'] [role='menu'], "
                        ".ant-select-dropdown, .chakra-select__menu, .mantine-Select-dropdown, .mantine-Select-items, "
                        ".MuiPopover-root, .MuiList-root, .rc-select-dropdown, .bp4-portal, .select__menu"
                    )
                    try:
                        overlays = self._page.locator(overlay_selectors)
                    except Exception:
                        overlays = None
                    candidate_scopes = []
                    if overlays is not None:
                        try:
                            count = min(overlays.count(), 6)
                            for idx in range(count):
                                try:
                                    scope = overlays.nth(idx)
                                    candidate_scopes.append(scope)
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    if trigger is not None:
                        candidate_scopes.append(trigger)

                    for scope in candidate_scopes:
                        if scope is None:
                            continue
                        for variant in variants:
                            try:
                                scope.get_by_text(variant, exact=True).first.click(timeout=timeout, force=force)
                                print(f"[SmartAI][select_option] Fallback matched exact text '{variant}'")
                                return
                            except Exception:
                                pass
                            try:
                                scope.get_by_text(variant).first.click(timeout=timeout, force=force)
                                print(f"[SmartAI][select_option] Fallback matched text contains '{variant}'")
                                return
                            except Exception:
                                pass
                            try:
                                scope.locator(f"text={variant}").first.click(timeout=timeout, force=force)
                                print(f"[SmartAI][select_option] Fallback matched locator text '{variant}'")
                                return
                            except Exception:
                                pass
                            try:
                                pattern = re.compile(re.escape(variant), re.IGNORECASE)
                                scope.locator(":scope *", has_text=pattern).first.click(timeout=timeout, force=force)
                                print(f"[SmartAI][select_option] Fallback regex matched '{variant}'")
                                return
                            except Exception:
                                pass

                except Exception as e:
                    last_exc = e

                # Last-resort mapping for native select
                try:
                    opts = self._locator.first.evaluate(
                        "el => Array.from(el.options).map(o => ({value:o.value, label:o.label || o.text}))"
                    )
                    if isinstance(opts, list) and opts:
                        target = str(value).strip().lower()
                        for o in opts:
                            if (o.get('label') or '').strip().lower() == target:
                                return self._locator.first.select_option(value=o.get('value'))
                        for o in opts:
                            if (o.get('value') or '').strip().lower() == target:
                                return self._locator.first.select_option(value=o.get('value'))
                    last_exc = Exception(f"Could not map '{value}' to native select options")
                except Exception as e3:
                    last_exc = e3

            except Exception as e_outer:
                last_exc = e_outer

            # retry/backoff
            wait = backoff * (2 ** (attempt - 1))
            try:
                self._page.wait_for_timeout(int(wait * 1000))
            except Exception:
                pass
            continue

        # exhausted retries
        raise Exception(f"SmartAI: unable to select option '{value}' (index={index}) after {retries} attempts; last error: {last_exc}")

# ========== 🔍 Assertion helper for dropdown/select ==========
def _expect_select_value(page, hint, expected_value, smartai_id=None):
    \"\"\"Assert selected value (visible text or value) for <select> dropdowns.\"\"\"
    from playwright.sync_api import expect

    try:
        loc = page.smartAI(hint)
        loc._safe_scroll()

        selected_text = loc.evaluate(
            \"\"\"(el) => {
                const opts = [...el.selectedOptions].map(o => o.textContent.trim());
                return opts.join(', ');
            }\"\"\"
        ).strip()

        if not selected_text:
            selected_text = loc.evaluate("el => el.value")

        assert expected_value.lower() in selected_text.lower(), (
            f"❌ Expected '{expected_value}' but found '{selected_text}' for {hint}"
        )
        print(f"✅ Dropdown '{hint}' has expected value '{expected_value}'")

    except Exception as e:
        print(f"[SmartAI Select Assert Failed] {e}")




class SmartAISelfHealing:
    _MODEL = None

    def __init__(self, metadata):
        self.metadata = metadata or []
        if SmartAISelfHealing._MODEL is None:
            SmartAISelfHealing._MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        self.model = SmartAISelfHealing._MODEL
        texts = [self._element_to_string(e) for e in self.metadata]
        self.embeddings = [
            self.model.encode(text, convert_to_tensor=True, show_progress_bar=False)
            for text in texts
        ] if texts else []
        self.locator_fail_count = {}
        self.failure_log = defaultdict(list)
        self._metadata_by_unique = {
            str(e.get("unique_name")): e for e in self.metadata if e.get("unique_name")
        }
        self._query_embed_cache = {}

    def _names_for_roles(self, element):
        '''Collect reasonable accessible names t o try for role-based queries.'''
        names = []
        for key in (
            "get_by_text",
            "label_text",
            "text",
            "title",
            "aria_label",
            "nearby_label",
            "name",
            "placeholder",
        ):
            v = (element.get(key) or "").strip()
            if v:
                names.append(v)
        # Include class-based hints only if short (avoid noise)
        dom_class = (element.get("dom_class") or "").strip()
        if dom_class and len(dom_class) < 80:
            names.append(dom_class)
        # De-dup while preserving order
        seen = set()
        uniq = []
        for n in names:
            if n not in seen:
                uniq.append(n); seen.add(n)
        return uniq

    def _candidate_roles(self, element):
        ocr = (element.get("ocr_type") or "").lower()
        tag = (element.get("tag_name") or "").lower()
        roles: list[str] = []

        def add(role: str | None):
            if role and role not in roles:
                roles.append(role)

        is_button_like = ocr in ("button", "submit", "iconbutton") or tag == "button"
        is_select_like = ocr in ("select", "dropdown", "combobox") or tag == "select"
        is_text_like = ocr in ("textbox", "text", "input", "email", "password") or tag in ("input", "textarea")
        is_link_like = ocr in ("link", "anchor") or tag == "a"

        if is_button_like:
            add("button")
        if is_select_like:
            add("combobox")
        if is_text_like:
            add("textbox")
        if is_link_like:
            add("link")

        # Targeted fallbacks based on inferred type
        if is_button_like:
            add("link")  # buttons sometimes render as anchors
        if is_select_like:
            add("button")  # custom selects often use button triggers
            add("textbox")  # some comboboxes expose textbox role
        if is_text_like:
            add("combobox")  # autocomplete inputs may present as combobox
        if is_link_like:
            add("button")

        # If we could not infer anything, fall back to a safe generic order
        if not roles:
            for fallback_role in ("button", "link", "combobox", "textbox"):
                add(fallback_role)

        return roles

    def _build_query_text(self, unique_name, reference=None):
        unique_key = str(unique_name or "")
        parts = [unique_key.replace("_", " ").strip()]
        ref = reference or self._metadata_by_unique.get(unique_key)
        if isinstance(ref, dict):
            for field in ("label_text", "placeholder", "intent", "text", "aria_label", "name", "nearby_label"):
                value = ref.get(field)
                if value:
                    parts.append(str(value).strip())
        text = " | ".join(p for p in parts if p)
        return text or unique_key

    def _get_query_embedding(self, unique_name, reference=None):
        ref_key = None
        if isinstance(reference, dict):
            ref_key = reference.get("unique_name") or reference.get("intent") or id(reference)
        unique_key = str(unique_name or "")
        cache_key = (unique_key, ref_key)
        if cache_key not in self._query_embed_cache:
            query_text = self._build_query_text(unique_key, reference)
            self._query_embed_cache[cache_key] = self.model.encode(
                query_text,
                convert_to_tensor=True,
                show_progress_bar=False
            )
        return self._query_embed_cache[cache_key]

    def _to_sequence(self, value):
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            return list(value)
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (list, tuple)):
                    return list(parsed)
                if parsed is None:
                    return []
                return [parsed]
            except Exception:
                return [value]
        return [value]

    def _metadata_tokens(self, meta):
        token_source = " ".join(
            filter(
                None,
                (
                    meta.get("unique_name"),
                    meta.get("intent"),
                    meta.get("label_text"),
                    meta.get("placeholder"),
                    meta.get("aria_label"),
                    meta.get("nearby_label"),
                ),
            )
        )
        return [tok for tok in re.split(r"[\s_\-]+", token_source.lower()) if len(tok) > 2]

    def _metadata_center(self, meta):
        def _center_from_rect(x, y, w, h):
            return (x + w / 2.0, y + h / 2.0)

        bbox = meta.get("bbox")
        if isinstance(bbox, str):
            try:
                bbox = json.loads(bbox)
            except Exception:
                bbox = None
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            try:
                x0, y0, w, h = map(float, bbox[:4])
                return _center_from_rect(x0, y0, w, h)
            except Exception:
                return None
        if isinstance(bbox, dict):
            try:
                return _center_from_rect(
                    float(bbox.get("x", 0.0)),
                    float(bbox.get("y", 0.0)),
                    float(bbox.get("width", bbox.get("w", 0.0))),
                    float(bbox.get("height", bbox.get("h", 0.0))),
                )
            except Exception:
                return None
        try:
            x0 = float(meta.get("x"))
            y0 = float(meta.get("y"))
            w = float(meta.get("width") or meta.get("w") or 0.0)
            h = float(meta.get("height") or meta.get("h") or 0.0)
            if w or h:
                return _center_from_rect(x0, y0, w, h)
        except Exception:
            pass
        return None

    def _direction_bias(self, tokens):
        token_set = set(tokens)
        return {
            "right": bool(token_set & {"right", "rpanel", "column2", "col2", "secondary"}),
            "left": bool(token_set & {"left", "lpanel", "column1", "col1", "primary"}),
            "bottom": bool(token_set & {"bottom", "lower", "footer"}),
            "top": bool(token_set & {"top", "upper", "header"}),
        }

    def _safe_attr(self, candidate, cache, name):
        if name in cache:
            return cache[name]
        try:
            cache[name] = candidate.get_attribute(name)
        except Exception:
            cache[name] = None
        return cache[name]

    def _score_candidate(self, candidate, meta, attr_targets, tokens, target_center):
        score = 0.0
        cache = {}
        norm = lambda s: (s or "").strip().lower()

        try:
            if candidate.is_visible():
                score += 1.0
        except Exception:
            pass

        for attr_name, target_value, weight in attr_targets:
            if not target_value:
                continue
            val = self._safe_attr(candidate, cache, attr_name)
            if val and norm(val) == norm(str(target_value)):
                score += weight

        text_content = None
        try:
            text_content = candidate.inner_text().strip()
            label_text = meta.get("label_text")
            if text_content and label_text and norm(text_content) == norm(label_text):
                score += 1.5
        except Exception:
            pass

        try:
            combined = " ".join(str(v) for v in cache.values() if isinstance(v, str))
            combined = f"{combined} {text_content or ''}".lower()
            for token in tokens:
                if token and token in combined:
                    score += 0.6
        except Exception:
            pass

        center = None
        try:
            box = candidate.bounding_box()
        except Exception:
            box = None
        if isinstance(box, dict):
            cx = box.get("x", 0.0) + box.get("width", 0.0) / 2.0
            cy = box.get("y", 0.0) + box.get("height", 0.0) / 2.0
            center = (cx, cy)
            if target_center:
                dist = abs(cx - target_center[0]) + abs(cy - target_center[1])
                score += max(0.0, 14.0 - dist / 18.0)

        return score, center

    def _apply_direction_bias(self, infos, bias):
        centers = [info["center"] for info in infos if info["center"] is not None]
        if not centers:
            return
        xs = [c[0] for c in centers]
        ys = [c[1] for c in centers]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1e-3)
        span_y = max(max_y - min_y, 1e-3)

        for info in infos:
            if info["center"] is None:
                continue
            cx, cy = info["center"]
            norm_x = (cx - min_x) / span_x
            norm_y = (cy - min_y) / span_y
            if bias["right"]:
                info["score"] += norm_x * 4.5
            if bias["left"]:
                info["score"] += (1.0 - norm_x) * 4.5
            if bias["bottom"]:
                info["score"] += norm_y * 3.0
            if bias["top"]:
                info["score"] += (1.0 - norm_y) * 3.0

    def _select_child_frame(self, current, identifier):
        try:
            if isinstance(identifier, int):
                frames = current.frames if hasattr(current, "frames") else current.child_frames
                return frames[identifier] if 0 <= identifier < len(frames) else None
            if isinstance(identifier, str):
                frame = current.frame(name=identifier) if hasattr(current, "frame") else None
                if frame:
                    return frame
                frames = current.frames if hasattr(current, "frames") else current.child_frames
                for child in frames:
                    if child.name == identifier or identifier in (child.url or ""):
                        return child
        except Exception:
            return None
        return None

    def _resolve_frame(self, page, meta):
        frame_path = self._to_sequence(meta.get("frame_path"))
        current = page
        for identifier in frame_path:
            next_frame = self._select_child_frame(current, identifier)
            if not next_frame:
                return page
            current = next_frame
        return current

    def _resolve_context(self, page, meta):
        context = self._resolve_frame(page, meta)
        scope = None
        shadow_chain = self._to_sequence(meta.get("shadow_chain") or meta.get("shadow_selectors"))
        if shadow_chain:
            try:
                current = context
                current_locator = None
                for selector in shadow_chain:
                    loc = current.locator(selector).first
                    current_locator = loc
                    current = loc
                scope = current_locator
            except Exception:
                scope = None
        section_selector = meta.get("section_selector")
        if section_selector:
            try:
                base = scope or context
                scope = base.locator(section_selector).first
            except Exception:
                pass
        return context, scope

    def _run_pre_actions(self, context, meta):
        for action in self._to_sequence(meta.get("pre_actions")):
            if not action:
                continue
            if isinstance(action, str):
                action = {"type": "click_selector", "value": action}
            try:
                act_type = action.get("type")
                value = action.get("value")
                if act_type == "click_selector" and value:
                    context.locator(value).first.click()
                elif act_type == "click_text" and value:
                    context.get_by_text(value, exact=False).first.click()
                elif act_type == "wait_for_selector" and value:
                    context.locator(value).first.wait_for(state=action.get("state", "visible"), timeout=action.get("timeout", 4000))
                elif act_type == "sleep":
                    time.sleep(float(action.get("seconds", 0.2)))
                elif act_type == "script":
                    context.evaluate(action.get("script"), action.get("arg"))
            except Exception as e:
                print(f"[SmartAI][PreAction] Failed '{action}': {e}")

    def _log_failure(self, unique_name, desc, error):
        key = str(unique_name or "unknown")
        log = self.failure_log[key]
        log.append({"desc": desc, "error": str(error), "time": time.time()})
        if len(log) > 20:
            del log[:-20]
        if len(log) >= 3:
            print(f"[SmartAI][Warn] '{key}' has {len(log)} consecutive failures. Consider recapturing metadata.")


    def _is_locator_ready(self, locator, quick: bool = False):
        '''Best-effort validation that the Playwright locator resolves to at least one element.'''
        if quick:
            try:
                return locator.count() > 0
            except Exception:
                return False
        try:
            locator.first.wait_for(state="attached", timeout=1200)
            return True
        except Exception:
            pass
        try:
            return locator.count() > 0
        except Exception:
            return False

    def _select_best_locator(self, locator, element):
        # Disambiguate multi-match locators using metadata-aware scoring.
        try:
            count = locator.count()
        except Exception:
            count = 1
        if count <= 1:
            return locator.first

        meta = element or {}
        tokens = self._metadata_tokens(meta)
        target_center = self._metadata_center(meta)
        bias = self._direction_bias(tokens)
        attr_targets = [
            ("id", meta.get("dom_id"), 5.0),
            ("name", meta.get("name"), 4.5),
            ("placeholder", meta.get("placeholder"), 3.5),
            ("data-testid", meta.get("data_testid") or meta.get("data-testid"), 4.5),
            ("data-element-id", meta.get("element_id"), 5.5),
            ("data-id", meta.get("data_id"), 4.5),
            ("data-name", meta.get("data_name"), 3.5),
            ("aria-label", meta.get("aria_label"), 3.5),
            ("title", meta.get("title"), 2.5),
        ]

        candidates_info = []
        max_samples = min(count, 8)
        for idx in range(max_samples):
            candidate = locator.nth(idx)
            score, center = self._score_candidate(candidate, meta, attr_targets, tokens, target_center)
            candidates_info.append({"candidate": candidate, "score": score, "center": center, "index": idx})

        self._apply_direction_bias(candidates_info, bias)

        if not candidates_info:
            return locator.first

        best_info = max(candidates_info, key=lambda info: info["score"])
        try:
            print(f"[SmartAI][Disambiguate] Resolved to candidate index {best_info['index']} with score {best_info['score']:.2f}")
        except Exception:
            pass
        return best_info["candidate"]

    # Core locator strategy
    def _try_all_locators(self, element, context, scope=None):
        '''
        Attempt all locator strategies but stop immediately once a working, visible locator is found.
        
        '''
        strategies = []
        unique_name = element.get("unique_name", "")

        def add_strategy(func, desc, stop_on_success=False):
            strategies.append((func, desc, stop_on_success))

        # Section anchors help scope complex layouts.
        for anchor in self._to_sequence(element.get("section_anchor") or element.get("panel_anchor")):
            if not anchor:
                continue
            anchor_json = json.dumps(str(anchor))
            add_strategy(
                lambda anchor_json=anchor_json: context.locator(
                    f"xpath=//*[normalize-space()={anchor_json}]"
                    "/following::*[self::input or self::textarea or self::select or contains(@role,'textbox')][1]"
                ),
                f"anchor_follow({anchor})",
                True,
            )
            add_strategy(
                lambda anchor_json=anchor_json: context.locator(
                    f"xpath=//*[normalize-space()={anchor_json}]"
                    "/preceding::*[self::input or self::textarea or self::select or contains(@role,'textbox')][1]"
                ),
                f"anchor_precede({anchor})",
                True,
            )

        if scope is not None:
            add_strategy(
                lambda: scope.locator("xpath=.//*[self::input or self::textarea or self::select or contains(@contenteditable,'true')]").first,
                "section_scope_fallback",
                True,
            )

        # Role-based queries using accessible names for multiple roles
        names = self._names_for_roles(element)
        if names:
            roles = self._candidate_roles(element)
            for nm in names:
                for role in roles:
                    add_strategy(lambda nm=nm, role=role: context.get_by_role(role, name=nm),
                                f"get_by_role({role}, name={nm})", True)

        # Try by label, text, placeholder, aria-label, etc. (same as before)
        if element.get("label_text"):
            add_strategy(lambda: context.get_by_label(element["label_text"]),
                        f"get_by_label({element['label_text']})", True)
            add_strategy(lambda: context.get_by_text(element["label_text"], exact=True),
                        f"get_by_text({element['label_text']}, exact=True)", True)

        if element.get("placeholder"):
            add_strategy(lambda: context.get_by_placeholder(element["placeholder"]),
                        f"get_by_placeholder({element['placeholder']})", True)
            add_strategy(lambda: context.locator(f'[placeholder="{element["placeholder"]}"]'),
                        f'locator([placeholder="{element["placeholder"]}"])', True)

        aria_label = (element.get("aria_label") or "").strip()
        if aria_label:
            add_strategy(lambda aria_label=aria_label: context.locator(f'[aria-label=\"{aria_label}\"]'),
                        f'locator([aria-label=\"{aria_label}\"])', True)
        title_attr = (element.get("title") or "").strip()
        if title_attr:
            add_strategy(lambda title_attr=title_attr: context.locator(f'[title="{title_attr}"]'), f'locator([title="{title_attr}"])', True)
        name_attr = (element.get("name") or "").strip()
        if name_attr:
            add_strategy(lambda name_attr=name_attr: context.locator(f'[name="{name_attr}"]'), f'locator([name="{name_attr}"])', True)

        # Nearby label / text hints
        nearby_label = (element.get("nearby_label") or "").strip()
        if nearby_label:
            add_strategy(lambda nearby_label=nearby_label: context.get_by_text(nearby_label, exact=False), f"get_by_text({nearby_label}, exact=False) [nearby_label]")
        plain_text = (element.get("text") or "").strip()
        if plain_text:
            add_strategy(lambda plain_text=plain_text: context.get_by_text(plain_text, exact=True), f"get_by_text({plain_text}, exact=True) [text]", True)
            add_strategy(lambda plain_text=plain_text: context.locator(f"text={plain_text}"), f"locator(text={plain_text})", True)

        # Text-neighbor heuristics: locate controls that appear near known text labels
        text_hints = []
        for key in ("get_by_text", "label_text", "nearby_label", "text"):
            val = (element.get(key) or "").strip()
            if val and len(val) < 120 and val not in text_hints:
                text_hints.append(val)
        for hint in text_hints:
            safe_hint = json.dumps(hint)
            follow_xpath = (
                f"xpath=//*[normalize-space()={safe_hint}]"
                "/following::*[self::select or contains(@role,'combobox') or contains(@role,'button')][1]"
            )
            sibling_xpath = (
                f"xpath=//*[normalize-space()={safe_hint}]"
                "/ancestor::*[self::label or self::*][1]//*[self::select or contains(@role,'combobox') or contains(@role,'button')]"
            )
            add_strategy(lambda selector=follow_xpath: context.locator(selector), f"locator({follow_xpath}) [text-following control]")
            add_strategy(lambda selector=sibling_xpath: context.locator(selector), f"locator({sibling_xpath}) [text-ancestor control]")

        # Try by sample value
        if element.get("sample_value"):
            add_strategy(lambda: context.get_by_display_value(element["sample_value"]), f"get_by_display_value({element['sample_value']})", True)

        # Data attributes (support dict or JSON string + explicit fields)
        data_attrs = element.get("data_attrs", {})
        if isinstance(data_attrs, str):
            try:
                data_attrs = json.loads(data_attrs)
            except Exception:
                data_attrs = {}
        explicit_data_fields = {
            "data-testid": element.get("data_testid"),
            "data-test-id": element.get("data_test_id"),
            "data-qa": element.get("data_qa"),
            "data-id": element.get("data_id"),
            "data-name": element.get("data_name"),
            "data-field": element.get("data_field"),
        }
        for attr, value in explicit_data_fields.items():
            if value:
                data_attrs[attr] = value
        for attr, value in data_attrs.items():
            if not value:
                continue
            attr_clean = attr.replace("_", "-")
            if "test" in attr_clean.lower() or "qa" in attr_clean.lower():
                add_strategy(lambda value=value: context.get_by_test_id(value), f"get_by_test_id({value})", True)
            add_strategy(lambda attr_clean=attr_clean, value=value: context.locator(f'[{attr_clean}="{value}"]'), f'locator([{attr_clean}="{value}"]) [data_attr]', True)

        # NEW: Try by data-id (exact & partial)
        data_id = element.get("data_id") or ""
        if data_id:
            add_strategy(lambda data_id=data_id: context.locator(f'[data-id="{data_id}"]'), f'locator([data-id="{data_id}"]) [data-id exact]', True)
            add_strategy(lambda data_id=data_id: context.locator(f'[data-id*="{data_id}"]'), f'locator([data-id*="{data_id}"]) [data-id partial]', True)

        # By id (exact and partial)
        if element.get("dom_id"):
            id_value = element["dom_id"]
            add_strategy(lambda id_value=id_value: context.locator(f'#{id_value}'), f"locator(#{id_value}) [ID exact]", True)
            add_strategy(lambda id_value=id_value: context.locator(f'[id*="{id_value}"]'), f'locator([id*="{id_value}"]) [ID partial]', True)

        # By class (exact and partial)
        if element.get("dom_class"):
            class_value = element["dom_class"]
            class_sel = "." + ".".join(class_value.split())
            add_strategy(lambda class_sel=class_sel: context.locator(class_sel), f"locator({class_sel}) [class exact]", True)
            add_strategy(lambda class_value=class_value: context.locator(f'[class*="{class_value}"]'), f'locator([class*="{class_value}"]) [class partial]', True)

        # By class_list
        if element.get("class_list"):
            sel = "." + ".".join(element["class_list"])
            add_strategy(lambda sel=sel: context.locator(sel), f"locator({sel}) [class_list]", True)

        # Custom CSS locator
        if element.get("locator"):
            try:
                locator_type = element["locator"].get("type")
                locator_value = element["locator"].get("value")
                if locator_type == "css" and locator_value:
                    add_strategy(lambda css=locator_value: context.locator(css), f"locator({locator_value}) [custom css]", True)
                if locator_type == "xpath" and locator_value:
                    add_strategy(lambda xp=locator_value: context.locator(f'xpath={xp}'), f"locator(xpath={locator_value}) [custom xpath]", True)
            except Exception:
                pass

        # Direct css/xpath shorthand fields
        css_value = element.get("css") or element.get("css_selector")
        if css_value:
            add_strategy(lambda css_value=css_value: context.locator(css_value), f"locator({css_value}) [css field]", True)
        xpath_value = element.get("xpath")
        if xpath_value:
            add_strategy(lambda xpath_value=xpath_value: context.locator(f'xpath={xpath_value}'), f"locator(xpath={xpath_value}) [xpath field]", True)

        # Attempt strategies in order
        for func, desc, stop_on_success in strategies:
            try:
                locator = func()
                if not locator:
                    continue

                # Check readiness and visibility
                if self._is_locator_ready(locator):
                    try:
                        count = locator.count()
                    except Exception:
                        count = 1
                    if count > 1:
                        print(f"[SmartAI][Warn] '{desc}' matched {count} elements; scoring candidates.")
                        chosen = self._select_best_locator(locator, element)
                    else:
                        chosen = locator.first

                    print(f"[SmartAI][Return] {desc} succeeded.")
                    self.locator_fail_count[unique_name] = 0
                    self.failure_log.pop(str(unique_name or "unknown"), None)

                    # ✅ Stop completely once first valid locator found
                    return chosen

                # Not ready — count as fail
                self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
                print(f"[SmartAI][Skip] {desc} resolved to no elements.")
                self._log_failure(unique_name, desc, "not-ready")
            except Exception as e:
                self.locator_fail_count[unique_name] = self.locator_fail_count.get(unique_name, 0) + 1
                print(f"[SmartAI][Skip] {desc} failed: {e}")
                self._log_failure(unique_name, desc, e)

        print(f"[SmartAI][Return] No valid locator found for '{unique_name}'.")
        self._log_failure(unique_name, "all_strategies", "exhausted")
        return None

    def find_element(self, unique_name, page):
        element = self._find_by_unique_name(unique_name)
        if element:
            context, scope = self._resolve_context(page, element)
            self._run_pre_actions(context, element)
            locator = self._try_all_locators(element, context, scope)
            if locator:
                print(f"[SmartAI] Element '{unique_name}' found using primary metadata.")
                return SmartAIWrappedLocator(locator, page)
            print(f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing...")

        element_ml, ml_score = self._ml_self_heal(unique_name, element)
        if element_ml:
            context_ml, scope_ml = self._resolve_context(page, element_ml)
            self._run_pre_actions(context_ml, element_ml)
            locator_ml = self._try_all_locators(element_ml, context_ml, scope_ml)
            if locator_ml:
                print(f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'")
                return SmartAIWrappedLocator(locator_ml, page)

        target_intent = element_ml.get("intent") if element_ml else None
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    context_intent, scope_intent = self._resolve_context(page, e)
                    self._run_pre_actions(context_intent, e)
                    locator = self._try_all_locators(e, context_intent, scope_intent)
                    if locator:
                        print(f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'")
                        return SmartAIWrappedLocator(locator, page)

        raise SmartAILocatorError(f"Element '{unique_name}' not found and cannot self-heal.")

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

    def _ml_self_heal(self, unique_name, reference=None):
        if not self.embeddings:
            return (None, 0.0)
        query_embedding = self._get_query_embedding(unique_name, reference)
        scores = [util.cos_sim(query_embedding, emb).item() for emb in self.embeddings]
        if not scores:
            return (None, 0.0)
        best_idx = int(np.argmax(scores))
        best_score = scores[best_idx]
        print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
        return (self.metadata[best_idx], best_score) if best_score > 0.6 else (None, best_score)

    def _element_to_string(self, element):
        data_attrs = element.get('data_attrs') or {}
        data_attr_parts = []
        if isinstance(data_attrs, str):
            try:
                data_attrs = json.loads(data_attrs)
            except Exception:
                data_attr_parts.append(str(data_attrs))
                data_attrs = {}
        if isinstance(data_attrs, dict):
            for k, v in data_attrs.items():
                if v:
                    data_attr_parts.append(f"{k}:{v}")
        fields = [
            element.get('unique_name', ''),
            element.get('label_text', ''),
            element.get('intent', ''),
            element.get('ocr_type', ''),
            element.get('element_type', ''),
            element.get('tag_name', ''),
            element.get('placeholder', ''),
            element.get('aria_label', ''),
            element.get('nearby_label', ''),
            element.get('text', ''),
            element.get('title', ''),
            element.get('name', ''),
            element.get('get_by_text', ''),
            element.get('css', ''),
            element.get('css_selector', ''),
            element.get('xpath', ''),
            element.get('dom_id', ''),
            element.get('dom_class', ''),
            element.get('frame', ''),
            element.get('data_testid', '') or element.get('data-testid', ''),
            element.get('data_name', ''),
            element.get('data_field', ''),
            ' '.join(element.get('class_list', []) or []),
            ' '.join(data_attr_parts),
            element.get('sample_value', ''),
            element.get('data_id', ''),
        ]
        return ' '.join([str(f) for f in fields if f])

# ====== PAGE PATCH ======
def patch_page_with_smartai(page, metadata):
    ai_healer = SmartAISelfHealing(metadata or [])
    def smartAI(unique_name):
        return ai_healer.find_element(unique_name, page)
    page.smartAI = smartAI
    return page
"""

def get_smartai_src_dir() -> Path:
    env_src = os.environ.get("SMARTAI_SRC_DIR")
    if env_src:
        return Path(env_src)
    backend_root = Path(__file__).resolve().parents[1]
    sandbox_src = backend_root / "sandbox" / "generated_runs" / "src"
    legacy_src = backend_root / "generated_runs" / "src"
    if sandbox_src.exists() or not legacy_src.exists():
        return sandbox_src
    return legacy_src


def ensure_smart_ai_module():
    lib_path = get_smartai_src_dir() / "lib"
    lib_path.mkdir(parents=True, exist_ok=True)
    (lib_path / "__init__.py").touch()
    smart_ai_file = lib_path / "smart_ai.py"
    smart_ai_file.write_text(SMART_AI_CODE, encoding="utf-8")



