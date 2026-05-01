    # utils/smart_ai_utils.py
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from utils.request_context import get_src_dir as get_request_src_dir

if TYPE_CHECKING:
    from database.project_storage import DatabaseBackedProjectStorage
  
SMART_AI_CODE = """import os
import json
import re
import time
import numpy as np
from pathlib import Path
from functools import wraps

# Optional OpenAI + local SentenceTransformer backends
try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    from playwright.sync_api import Locator as PWLocator, expect
except Exception:  # pragma: no cover
    PWLocator = object
    expect = None


class SmartAILocatorError(Exception):
    pass


# ===========================================================
# SEMANTIC ENCODER (OpenAI + SentenceTransformer fallback)
# ===========================================================
class SemanticEncoder:
    '''
    Wrapper around embedding backends.

    Priority:
      1) OpenAI embeddings (text-embedding-3-small by default)
      2) Local SentenceTransformer ('all-MiniLM-L6-v2')
      3) Zero-vector fallback (similarity=0)
    '''

    def __init__(self):
        self.use_openai = False
        self.client = None
        self.openai_model = None
        self.local_model = None

        # Allow override via OPENAI_API_KEY or normal OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

        if OpenAI is not None and api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                self.openai_model = os.getenv(
                    "SMARTAI_OPENAI_EMBED_MODEL", "text-embedding-3-small"
                )
                self.use_openai = True
                print(
                    f"[SmartAI][SemanticEncoder] Using OpenAI embeddings: {self.openai_model}"
                )
            except Exception as e:  # pragma: no cover
                print(f"[SmartAI][SemanticEncoder] OpenAI init failed: {e}")

        if not self.use_openai and SentenceTransformer is not None:
            try:
                local_name = os.getenv(
                    "SMARTAI_LOCAL_EMBED_MODEL", "all-MiniLM-L6-v2"
                )
                self.local_model = SentenceTransformer(local_name)
                print(
                    f"[SmartAI][SemanticEncoder] Using local SentenceTransformer: {local_name}"
                )
            except Exception as e:  # pragma: no cover
                print(f"[SmartAI][SemanticEncoder] Local ST init failed: {e}")

        if not self.use_openai and self.local_model is None:
            print(
                "[SmartAI][SemanticEncoder] WARNING: No embedding backend available. Similarity will be 0."
            )

        # -------- context + text enrichment for embeddings -----------------------
    def enrich_for_embedding(self, meta: dict) -> str:
        '''
        Build a strong combined text representation including:
        - label_text / get_by_text / placeholder / text
        - aria_label / title_text / variant_text
        - parent_block_text / sibling_text
        '''
        if not meta:
            return ""

        parts = [
            meta.get("label_text") or "",
            meta.get("get_by_text") or "",
            meta.get("placeholder") or "",
            meta.get("text") or "",
            meta.get("value") or "",
            meta.get("aria_label") or "",
            meta.get("title_text") or "",
            meta.get("variant_text") or "",
            meta.get("parent_block_text") or "",
        ]

        # Add sibling list
        sibs = meta.get("sibling_text", [])
        if isinstance(sibs, list):
            parts.extend(sibs)
        elif isinstance(sibs, str):
            parts.append(sibs)

        return " | ".join(p for p in parts if p).strip()


    # -------- core helpers -------------------------------------------------
    def _encode_openai_many(self, texts):
        if not texts:
            return []
        if self.client is None or not self.use_openai:
            return None
        try:
            resp = self.client.embeddings.create(
                model=self.openai_model,
                input=texts,
            )
            vecs = [np.array(d.embedding, dtype="float32") for d in resp.data]
            # Normalize
            return [v / (np.linalg.norm(v) + 1e-12) for v in vecs]
        except Exception as e:  # pragma: no cover
            print(
                f"[SmartAI][SemanticEncoder] OpenAI embedding failed, falling back to local if available: {e}"
            )
            self.use_openai = False
            return None

    def _encode_local_many(self, texts):
        if not texts or self.local_model is None:
            return None
        try:
            arr = self.local_model.encode(texts, normalize_embeddings=True)
            return [np.array(v, dtype="float32") for v in arr]
        except Exception as e:  # pragma: no cover
            print(f"[SmartAI][SemanticEncoder] Local embedding failed: {e}")
            return None

    # -------- public API ---------------------------------------------------
    def encode_many(self, texts):
        '''
        Batch encode a list of strings into normalized numpy vectors.
        '''
        if not texts:
            return []
        cleaned = [
            t if (t is not None and isinstance(t, str) and t.strip()) else " "
            for t in texts
        ]

        vecs = None
        # Try OpenAI first
        if self.use_openai and self.client is not None:
            vecs = self._encode_openai_many(cleaned)

        # Fall back to local ST
        if vecs is None and self.local_model is not None:
            vecs = self._encode_local_many(cleaned)

        # Final safety: zero vectors
        if vecs is None:
            dim = 384
            vecs = [np.zeros(dim, dtype="float32") for _ in cleaned]

        return vecs

    def encode(self, text: str):
        return self.encode_many([text or " "])[0]

    def similarity_vec(self, a: np.ndarray, b: np.ndarray) -> float:
        if a is None or b is None:
            return 0.0
        if a.shape != b.shape:
            m = min(a.shape[0], b.shape[0])
            if m == 0:
                return 0.0
            a = a[:m]
            b = b[:m]
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def similarity_text(self, t1: str, t2: str) -> float:
        if not t1 or not t2:
            return 0.0
        v1 = self.encode(t1)
        v2 = self.encode(t2)
        return self.similarity_vec(v1, v2)


# ===========================================================
# WRAPPED LOCATOR
# ===========================================================
class SmartAIWrappedLocator(PWLocator):
    '''
    Thin wrapper over Playwright's Locator that:
    - Auto scrolls element into view before interaction
    - Provides robust fill() with verification & retries
    - Provides robust select_option() with multiple fallbacks
    '''

    def __init__(self, locator, page, element_meta=None):
        self._page = page
        self._locator = locator
        self._element_meta = element_meta if isinstance(element_meta, dict) else {}

        if self._should_prefer_fill_target():
            resolved = self._resolve_fill_target(self._locator)
            if resolved is not None:
                self._locator = resolved

        try:
            super().__init__(self._locator._impl_obj)
        except Exception:
            pass

    def __getattr__(self, name):
        # Delegate unknown attributes/methods to the underlying locator, but wrap callables so
        # SmartAI behavior (auto-scroll + consistent wrapping) applies to the full Playwright surface.
        attr = getattr(self._locator, name)
        if not callable(attr):
            return attr

        def _wrapped(*args, **kwargs):
            try:
                if self._should_auto_scroll_for(name):
                    self._safe_scroll()
            except Exception:
                pass
            result = attr(*args, **kwargs)
            return self._wrap_return_value(result)

        return _wrapped

    def _should_auto_scroll_for(self, method_name: str) -> bool:
        if not method_name:
            return False
        # Avoid auto-scrolling for pure getters; keep it for interactions and locator-producing calls.
        auto = {
            "click",
            "dblclick",
            "hover",
            "tap",
            "check",
            "uncheck",
            "fill",
            "type",
            "press",
            "press_sequentially",
            "select_option",
            "select_text",
            "set_input_files",
            "dispatch_event",
            "drag_to",
            "clear",
            "focus",
            "blur",
            "scroll_into_view_if_needed",
        }
        if method_name in auto:
            return True
        # Locator chaining commonly precedes actions; scrolling is harmless and reduces flakiness.
        if method_name in {"locator", "get_by_role", "get_by_text", "get_by_label", "get_by_placeholder", "get_by_test_id", "get_by_title", "get_by_alt_text", "nth", "filter", "and_", "or_"}:
            return True
        return False

    def _wrap_return_value(self, value):
        # Wrap any Locator (or list of Locators) returned by Playwright so callers keep SmartAI behavior.
        try:
            if isinstance(value, SmartAIWrappedLocator):
                return value
        except Exception:
            pass

        try:
            if PWLocator is not object and isinstance(value, PWLocator):
                return SmartAIWrappedLocator(value, self._page, element_meta=self._element_meta)
        except Exception:
            pass

        if isinstance(value, list):
            wrapped = []
            for item in value:
                try:
                    if PWLocator is not object and isinstance(item, PWLocator):
                        wrapped.append(SmartAIWrappedLocator(item, self._page, element_meta=self._element_meta))
                    else:
                        wrapped.append(item)
                except Exception:
                    wrapped.append(item)
            return wrapped

        if isinstance(value, tuple):
            wrapped = []
            for item in value:
                try:
                    if PWLocator is not object and isinstance(item, PWLocator):
                        wrapped.append(SmartAIWrappedLocator(item, self._page, element_meta=self._element_meta))
                    else:
                        wrapped.append(item)
                except Exception:
                    wrapped.append(item)
            return tuple(wrapped)

        return value

    # --- helpers -------------------------------------------------------------
    def _should_prefer_fill_target(self):
        meta = self._element_meta or {}
        if not meta:
            return False
        tag_name = str(meta.get("tag_name") or "").strip().lower()
        if tag_name in ("input", "textarea", "select"):
            return True

        hints = []
        for key in ("element_type", "ocr_type", "intent", "unique_name", "role"):
            val = meta.get(key)
            if val:
                hints.append(str(val).strip().lower())

        hint_text = " ".join(hints)
        keywords = (
            "textbox",
            "text_box",
            "text field",
            "textfield",
            "input",
            "password",
            "email",
            "username",
            "search",
        )
        return any(k in hint_text for k in keywords)

    def _safe_scroll(self, timeout: int = 2000):
        try:
            self._locator.scroll_into_view_if_needed(timeout=timeout)
        except Exception:
            # We never want scroll failures to block interaction
            pass
    def _ensure_attached(self, timeout: int = 6000):
        try:
            self._locator.first.wait_for(state="attached", timeout=timeout)
        except Exception:
            pass

    def _ensure_visible(self, timeout: int = 6000):
        try:
            self._locator.first.wait_for(state="visible", timeout=timeout)
        except Exception:
            pass

    def _ensure_enabled(self, timeout: int = 6000):
        try:
            if not hasattr(self._locator.first, "is_enabled"):
                return
            if expect is not None:
                expect(self._locator.first).to_be_enabled(timeout=timeout)
                return
            try:
                self._locator.first.is_enabled()
            except Exception:
                pass
        except Exception:
            pass
    def _safe_has_text(self, tag: str, txt: str):
        '''
        Build a safe Playwright selector:
            tag:has-text("value")
        Automatically escapes:
        - quotes
        - plus signs
        - brackets
        - parentheses
        Prevents SyntaxError and invalid selector errors.
        ''' 
        if not txt:
            return None

        # Escape quotes
        safe_txt = txt.replace('"', '\"').strip()

        # Escape CSS-special characters: + ( ) [ ]
        import re
        safe_txt = re.sub(r'([+()\[\]])', r'\', safe_txt)

        # Final selector
        return f'{tag}:has-text("{safe_txt}")'

    # --- core interactions ---------------------------------------------------
    def _is_fillable(self, locator):
        try:
            tag = locator.evaluate("el => (el.tagName || '').toLowerCase()")
        except Exception:
            tag = ""
        if tag in ("input", "textarea", "select"):
            return True
        try:
            role = locator.evaluate("el => el.getAttribute('role') || ''")
        except Exception:
            role = ""
        try:
            is_ce = locator.evaluate("el => !!el.isContentEditable")
        except Exception:
            is_ce = False
        return is_ce or role in ("textbox", "combobox", "searchbox", "spinbutton")

    def _resolve_fill_target(self, locator):
        # 1) direct descendants
        try:
            inner = locator.locator(
                "input, textarea, select, [contenteditable], [role='textbox'], "
                "[role='combobox'], [role='searchbox'], [role='spinbutton']"
            )
            if inner.count() > 0:
                return inner.first
        except Exception:
            pass

        # 2) label[for] -> #id
        try:
            for_attr = locator.get_attribute("for")
        except Exception:
            for_attr = None
        if for_attr:
            try:
                by_for = self._page.locator(f"#{for_attr}")
                if by_for.count() > 0:
                    return by_for.first
            except Exception:
                pass

        # 3) nearest relevant ancestor that contains inputs
        try:
            ancestor = locator.locator(
                "xpath=ancestor::*[self::label or self::td or self::th or self::div or self::tr or self::form][1]"
                "//input | "
                "ancestor::*[self::label or self::td or self::th or self::div or self::tr or self::form][1]"
                "//textarea | "
                "ancestor::*[self::label or self::td or self::th or self::div or self::tr or self::form][1]"
                "//select | "
                "ancestor::*[self::label or self::td or self::th or self::div or self::tr or self::form][1]"
                "//*[@contenteditable='true']"
            )
            if ancestor.count() > 0:
                return ancestor.first
        except Exception:
            pass

        # 4) next input-like element in DOM
        try:
            following = locator.locator(
                "xpath=following::input[1] | following::textarea[1] | following::select[1]"
            )
            if following.count() > 0:
                return following.first
        except Exception:
            pass

        return None

    def click(self, *args, **kwargs):
        self._safe_scroll()
        # Always click the first element for stability
        self._ensure_visible(kwargs.get("timeout", 6000))
        self._ensure_enabled(kwargs.get("timeout", 6000))
        return self._locator.first.click(*args, **kwargs)

    def right_click(self, *args, **kwargs):
        self._safe_scroll()
        kwargs = dict(kwargs)
        kwargs.setdefault("button", "right")
        self._ensure_visible(kwargs.get("timeout", 6000))
        self._ensure_enabled(kwargs.get("timeout", 6000))
        return self._locator.first.click(*args, **kwargs)

    def dblclick(self, *args, **kwargs):
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        self._ensure_enabled(kwargs.get("timeout", 6000))
        return self._locator.first.dblclick(*args, **kwargs)

    def hover(self, *args, **kwargs):
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        return self._locator.first.hover(*args, **kwargs)

    def focus(self, *args, **kwargs):
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        return self._locator.first.focus(*args, **kwargs)

    def blur(self, *args, **kwargs):
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        return self._locator.first.blur(*args, **kwargs)

    def press(self, key: str, *args, **kwargs):
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        return self._locator.first.press(key, *args, **kwargs)

    def type(self, value: str, *args, **kwargs):
        self._safe_scroll()
        target = self._locator.first
        if not self._is_fillable(target):
            resolved = self._resolve_fill_target(target)
            if resolved is not None:
                target = resolved
        self._ensure_visible(kwargs.get("timeout", 6000))
        return target.type(str(value), *args, **kwargs)

    def clear(self, *args, **kwargs):
        timeout = kwargs.get("timeout", 6000)
        return self.fill("", retries=1, timeout=timeout, force=kwargs.get("force", False))

    def _click_kwargs_from(self, kwargs: dict) -> dict:
        '''Best-effort mapping of check/uncheck kwargs to click kwargs.'''
        if not kwargs:
            return {}
        allowed = {
            "timeout",
            "force",
            "no_wait_after",
            "trial",
            "button",
            "modifiers",
            "position",
            "delay",
            "click_count",
            "strict",
        }
        return {k: v for k, v in kwargs.items() if k in allowed}

    def _best_label_hint(self) -> str:
        meta = self._element_meta or {}
        for key in (
            "label_text",
            "aria_label",
            "placeholder",
            "get_by_text",
            "text",
            "value",
            "name",
            "unique_name",
        ):
            value = meta.get(key)
            if not value:
                continue
            label = str(value).strip()
            if label:
                return label
        return ""

    def _resolve_checkbox_target(self):
        '''Try to find the real checkbox control when metadata points to a non-input element.'''
        label = self._best_label_hint()
        if not label:
            return None

        candidates = []
        try:
            regex = re.compile(re.escape(label), re.IGNORECASE)
        except Exception:
            regex = None

        # 1) ARIA checkbox by role
        try:
            if regex is not None:
                candidates.append(self._page.get_by_role("checkbox", name=regex))
            candidates.append(self._page.get_by_role("checkbox", name=label))
        except Exception:
            pass

        # 2) Label association (works for <label for=...>)
        try:
            candidates.append(self._page.get_by_label(label))
        except Exception:
            pass

        # 3) Common DOM patterns
        try:
            quoted = json.dumps(label)
        except Exception:
            quoted = "'" + label.replace("'", "\\'") + "'"

        selectors = [
            f"label:has-text({quoted}) input[type='checkbox']",
            f"label:has-text({quoted}) >> input[type='checkbox']",
            f\"[role='checkbox']:has-text({quoted})\",
            f\"input[type='checkbox'][aria-label={quoted}]\",
            f\"[aria-label={quoted}][role='checkbox']\",
        ]
        for sel in selectors:
            try:
                candidates.append(self._page.locator(sel))
            except Exception:
                continue

        for loc in candidates:
            try:
                if loc is not None and loc.count() > 0:
                    return loc.first
            except Exception:
                continue

        return None

    def check(self, *args, **kwargs):
        '''Robust checkbox check with fallback for anchor/button-based toggles.'''
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        self._ensure_enabled(kwargs.get("timeout", 6000))
        target = self._locator.first
        try:
            return target.check(*args, **kwargs)
        except Exception as e:
            message = str(e)
            if "Not a checkbox or radio button" in message or "not a checkbox" in message.lower():
                resolved = None
                try:
                    resolved = self._resolve_checkbox_target()
                except Exception:
                    resolved = None
                if resolved is not None:
                    try:
                        return resolved.check(*args, **kwargs)
                    except Exception:
                        pass
                return target.click(**self._click_kwargs_from(kwargs))
            raise

    def uncheck(self, *args, **kwargs):
        '''Robust checkbox uncheck with fallback for anchor/button-based toggles.'''
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        self._ensure_enabled(kwargs.get("timeout", 6000))
        target = self._locator.first
        try:
            return target.uncheck(*args, **kwargs)
        except Exception as e:
            message = str(e)
            if "Not a checkbox or radio button" in message or "not a checkbox" in message.lower():
                resolved = None
                try:
                    resolved = self._resolve_checkbox_target()
                except Exception:
                    resolved = None
                if resolved is not None:
                    try:
                        return resolved.uncheck(*args, **kwargs)
                    except Exception:
                        pass
                return target.click(**self._click_kwargs_from(kwargs))
            raise

    def set_checked(self, checked: bool = True, *args, **kwargs):
        '''Set checkbox state when supported; otherwise fall back to click.'''
        self._safe_scroll()
        self._ensure_visible(kwargs.get("timeout", 6000))
        self._ensure_enabled(kwargs.get("timeout", 6000))
        target = self._locator.first
        try:
            return target.set_checked(bool(checked), *args, **kwargs)
        except Exception as e:
            message = str(e)
            if "Not a checkbox or radio button" in message or "not a checkbox" in message.lower():
                resolved = None
                try:
                    resolved = self._resolve_checkbox_target()
                except Exception:
                    resolved = None
                if resolved is not None:
                    try:
                        return resolved.set_checked(bool(checked), *args, **kwargs)
                    except Exception:
                        pass
                return target.click(**self._click_kwargs_from(kwargs))
            raise

    def fill(self, value, retries: int = 3, timeout: int = 3000, force: bool = False):
        '''
        Fill value with validation and limited retries.
        If after all retries the field does not reflect the value, raise SmartAILocatorError.
        '''
        self._safe_scroll()
        self._ensure_attached(timeout)
        self._ensure_visible(timeout)
        target = self._locator.first
        if not self._is_fillable(target):
            resolved = self._resolve_fill_target(target)
            if resolved is not None:
                target = resolved
        last_error = None

        for attempt in range(1, retries + 1):
            try:
                target.fill(str(value), timeout=timeout, force=force)
            except Exception as e:
                last_error = e
                continue

            # Validate by reading it back
            try:
                current = None
                try:
                    current = target.input_value()
                except Exception:
                    # fallback to DOM value
                    current = target.evaluate('el => el.value')
                if current is None:
                    current = ''
                if str(current).strip() == str(value).strip():
                    return
            except Exception as e:
                last_error = e

        raise SmartAILocatorError(
            f"SmartAIWrappedLocator.fill failed after {retries} attempts. "
            f"Last error: {last_error}"
        )

    def select_option(
        self,
        value=None,
        *,
        label=None,
        index: int | None = None,
        timeout: int = 5000,
        force: bool = False,
        **kwargs,
    ):
        '''
        Robust select handler:
        1) Try native select_option(label=...) then value=...
        2) If native fails, treat it as a combobox & click an option with proper waits
        3) As a last resort on real <select>, map label->value case-insensitively via DOM
        '''
        self._safe_scroll()

        def _resolve_select_target():
            try:
                tag = self._locator.first.evaluate("el => (el.tagName || '').toLowerCase()")
                role = self._locator.first.evaluate("el => el.getAttribute('role') || ''")
            except Exception:
                tag = ""
                role = ""

            if tag == "select" or role == "combobox":
                return self._locator.first

            try:
                for_attr = self._locator.first.get_attribute("for")
            except Exception:
                for_attr = None

            if for_attr:
                candidate = self._page.locator(f"#{for_attr}")
                try:
                    if candidate.count() > 0:
                        return candidate.first
                except Exception:
                    pass

            try:
                container = self._locator.first.locator(
                    "xpath=ancestor::*[self::label or @role='group' or @role='presentation' or "
                    "contains(@class,'field') or contains(@class,'form')][1]"
                )
                candidate = container.locator("select, [role='combobox']")
                if candidate.count() > 0:
                    return candidate.first
            except Exception:
                pass

            try:
                candidate = self._locator.first.locator(
                    "xpath=following::*[self::select or @role='combobox'][1]"
                )
                if candidate.count() > 0:
                    return candidate.first
            except Exception:
                pass

            return None

        target = _resolve_select_target() or self._locator.first
        self._ensure_visible(timeout)

        # --- Native fast-path for real <select> ---
        try:
            return target.select_option(label=value)
        except Exception:
            try:
                return target.select_option(value=value)
            except Exception:
                pass  # fall through to combobox flow

        # --- Combobox / custom dropdown flow with waits ---
        try:
            trigger = None
            try:
                trigger = target.nth(index) if index is not None else target
            except Exception:
                trigger = None

            if trigger is None:
                trigger = self._page.get_by_role('combobox')
                trigger = trigger.nth(index) if index is not None else trigger.first

            trigger.scroll_into_view_if_needed(timeout=timeout)
            trigger.click(timeout=timeout)

            # Wait for options to show up
            try:
                self._page.get_by_role('listbox').first.wait_for(
                    state='visible', timeout=timeout
                )
            except Exception:
                self._page.wait_for_selector('[role="option"]', timeout=timeout)

            # Exact name first
            try:
                self._page.get_by_role(
                    'option', name=str(value), exact=True
                ).first.click(timeout=timeout, force=force)
                return
            except Exception:
                pass

            # Contains text
            try:
                self._page.get_by_role(
                    'option', name=str(value)
                ).first.click(timeout=timeout, force=force)
                return
            except Exception:
                pass

            # Case-insensitive attempts
            candidates = [
                str(value).strip(),
                str(value).capitalize(),
                str(value).title(),
                str(value).lower(),
                str(value).upper(),
            ]
            for v in candidates:
                try:
                    self._page.get_by_role('option', name=v).first.click(
                        timeout=timeout, force=force
                    )
                    return
                except Exception:
                    continue

            # Final: iterate options and compare text
            opts = self._page.locator('[role="option"]')
            try:
                n = opts.count()
            except Exception:
                n = 0
            target_low = str(value).strip().lower()
            for i in range(n):
                try:
                    txt = opts.nth(i).inner_text().strip()
                    if txt.lower() == target_low:
                        opts.nth(i).click(timeout=timeout, force=force)
                        return
                except Exception:
                    continue

        except Exception as e:
            print(f"[SmartAI][select_option fallback] Combobox flow failed: {e}")

        # --- Last-resort: if this truly was a <select> with label/value mismatch, map by DOM ---
        try:
            opts = self._locator.first.evaluate(
                'el => Array.from(el.options || []).map(o => ({value:o.value, label:o.label || o.text}))'
            )
            if isinstance(opts, list) and opts:
                target = str(value).strip().lower()
                # try exact label match (case-insensitive)
                for o in opts:
                    if (o.get('label') or '').strip().lower() == target:
                        return self._locator.first.select_option(value=o.get('value'))
                # try value equals (case-insensitive)
                for o in opts:
                    if (o.get('value') or '').strip().lower() == target:
                        return self._locator.first.select_option(value=o.get('value'))
            print(
                f"[SmartAI][select_option fallback] Could not map '{value}' to an option value on native <select>."
            )
        except Exception as e3:
            print(f"[SmartAI][select_option fallback] Native <select> mapping failed: {e3}")

        raise SmartAILocatorError(
            f"SmartAI: unable to select option '{value}' (index={index})"
        )

    def _resolve_file_input_target(self, locator):
        try:
            file_input = locator.locator("input[type='file']")
            if file_input.count() > 0:
                return file_input.first
        except Exception:
            pass

        try:
            if locator.get_attribute("for"):
                candidate = self._page.locator(f\"#{locator.get_attribute('for')}\")
                if candidate.count() > 0:
                    return candidate.first
        except Exception:
            pass

        try:
            container = locator.locator(
                "xpath=ancestor::*[self::label or self::div or self::form][1]//input[@type='file']"
            )
            if container.count() > 0:
                return container.first
        except Exception:
            pass

        try:
            following = locator.locator("xpath=following::input[@type='file'][1]")
            if following.count() > 0:
                return following.first
        except Exception:
            pass

        return None

    def set_input_files(self, files, *args, **kwargs):
        self._safe_scroll()
        if value is None and label is not None:
            value = label
        if value is None:
            raise SmartAILocatorError("SmartAIWrappedLocator.select_option requires value or label")
        target = self._resolve_file_input_target(self._locator.first) or self._locator.first
        # File inputs can be hidden; require attached but not visible.
        try:
            target.wait_for(state="attached", timeout=kwargs.get("timeout", 6000))
        except Exception:
            pass
        return target.set_input_files(files, *args, **kwargs)

    def drag_to(self, target, *args, **kwargs):
        self._safe_scroll()
        source = self._locator.first
        dest = None
        try:
            if isinstance(target, SmartAIWrappedLocator):
                dest = target._locator.first
            elif PWLocator is not object and isinstance(target, PWLocator):
                dest = target
        except Exception:
            dest = None
        if dest is None and isinstance(target, str):
            try:
                dest = self._page.locator(target).first
            except Exception:
                dest = None
        self._ensure_visible(kwargs.get("timeout", 6000))
        if dest is not None:
            return source.drag_to(dest, *args, **kwargs)
        return source.drag_to(target, *args, **kwargs)

    def drag_and_drop(self, target, *args, **kwargs):
        return self.drag_to(target, *args, **kwargs)


# ===========================================================
# SELF HEALING CORE
# ===========================================================
class SmartAISelfHealing:
    '''
    Core self-healing engine.
    Relies on:
      - unique_name
      - label_text / get_by_text / placeholder / text
      - ocr_type / tag_name / intent
      - optional dom_id / dom_class / class_list / data_attrs
    '''

    def __init__(self, metadata):
        self.metadata = metadata or []
        if not isinstance(self.metadata, list):
            self.metadata = list(self.metadata)

        # Semantic encoder (OpenAI + ST fallback)
        self.encoder = SemanticEncoder()

        # Lazy-computed embeddings for metadata elements
        self.embeddings = None

        # Track failures per-element
        self.locator_fail_count = {}

    def _log_healed_locator(self, unique_name: str, element: dict):
        try:
            base_dir = Path(__file__).resolve()
            for _ in range(4):
                base_dir = base_dir.parent
            logs_dir = base_dir / "data" / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "unique_name": unique_name,
                "label_text": (element or {}).get("label_text"),
                "timestamp": time.time(),
            }
            with (logs_dir / "smartai_healed_locators.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\\n")
        except Exception:
            pass

    # -------------------------------------------------------------
    # SANITIZER FOR TAILWIND / INVALID CSS CLASS NAMES
    # -------------------------------------------------------------
    def _sanitize_class_list(self, classes):
        '''
        Remove Tailwind variant tokens and invalid CSS pieces from class list.
        Example bad tokens: [&_svg]:size-4, peer-disabled:opacity-70, dark:bg-zinc-900
        We keep only real, usable CSS class names.
        '''
        safe = []
        for c in classes:
            if not c or not isinstance(c, str):
                continue
            c = c.strip()
            if not c:
                continue

            # Skip Tailwind JIT variant syntax like [&_svg]:size-4
            if '[' in c or ']' in c:
                continue

            # Remove state prefixes: hover:, focus:, dark:, etc.
            if ':' in c:
                parts = c.split(':')
                c = parts[-1].strip()
                if not c:
                    continue

            # 🔥 Handle illegal characters: remove "/" (Tailwind group modifiers)
            c = c.replace('/', '-')   # <-- FIX HERE (escape or replace)
            
            # Only allow alphanumeric, dash, underscore
            import re
            c = re.sub(r'[^A-Za-z0-9\-_]', '', c)

            if c:
                safe.append(c)

        # Deduplicate
        seen = set()
        out = []
        for cls in safe:
            if cls not in seen:
                seen.add(cls)
                out.append(cls)
        return out


    # ------------------------------------------------------------------ utils
    def _element_to_string(self, element: dict) -> str:
        '''
        Build a dense text representation from metadata fields for embedding.
        '''
        if not isinstance(element, dict):
            return ""
        data_attrs = element.get("data_attrs") or {}
        if not isinstance(data_attrs, dict):
            data_attrs = {}

        fields = [
            element.get("unique_name", ""),
            element.get("label_text", ""),
            element.get("intent", ""),
            element.get("ocr_type", ""),
            element.get("element_type", ""),
            element.get("tag_name", ""),
            element.get("placeholder", ""),
            element.get("text", ""),
            " ".join(element.get("class_list", []) or []),
            " ".join(f"{k}:{v}" for k, v in data_attrs.items()),
            element.get("sample_value", ""),
        ]
        base = " ".join(str(f) for f in fields if f)
        enriched = SmartAISelfHealing.encoder.enrich_for_embedding(element) if hasattr(SmartAISelfHealing, "encoder") else ""
        return f"{base} | {enriched}".strip()
        return " ".join(str(f) for f in fields if f)

    def _ensure_metadata_embeddings(self):
        '''
        Lazily compute embeddings for all metadata elements in one batch.
        '''
        if self.embeddings is not None:
            return
        texts = [self._element_to_string(e) or " " for e in self.metadata]
        self.embeddings = self.encoder.encode_many(texts)

    def _semantic_similarity(self, a: str, b: str) -> float:
        '''
        Compare two texts using the configured semantic encoder.
        '''
        return self.encoder.similarity_text(a, b)

    # --- synonym-like text variants (no hardcoded domain words) ---------------
    def _truncate_text_for_matching(self, txt: str, max_len: int = 180) -> str:
        '''
        Limit overly long text used for selectors/regex to avoid Playwright
        selector parsing issues and expensive matches.
        '''
        if not txt:
            return ""
        clean = " ".join(str(txt).split())
        if len(clean) <= max_len:
            return clean
        parts = clean.split()
        if len(parts) >= 6:
            return " ".join(parts[-6:])
        return clean[-max_len:]

    def _synonym_texts(self, txt: str):
        '''
        Generate neutral text variants without any domain-specific hardcoding.
        This is light helper logic; true semantic matching is done via embeddings.
        '''
        if not txt:
            return []

        variants = set()
        clean = self._truncate_text_for_matching(txt)  # normalize + cap length

        # Basic variants
        variants.add(clean)
        variants.add(clean.lower())
        variants.add(clean.title())
        variants.add(clean.upper())

        # Remove leading '+ ' if present, and also keep version without '+'
        if clean.startswith("+ "):
            variants.add(clean[2:].strip())
        else:
            variants.add("+ " + clean)

        # Last word / last 2-3 words (helps if label is long)
        parts = clean.split()
        if len(parts) >= 2:
            variants.add(" ".join(parts[-2:]))
        if len(parts) >= 3:
            variants.add(" ".join(parts[-3:]))

        out = []
        seen = set()
        for v in variants:
            v2 = v.strip()
            if v2 and v2 not in seen:
                seen.add(v2)
                out.append(v2)
        return out

    def _names_for_roles(self, element: dict):
        '''
        Collect reasonable accessible names to try for role-based queries,
        including neutral variants.
        '''
        names = []
        for key in ("label_text", "get_by_text", "placeholder", "text", "aria_label", "title_text"):
            v = self._truncate_text_for_matching(element.get(key) or "")
            if v:
                names.extend(self._synonym_texts(v))

        uniq = (element.get("unique_name") or "").strip()
        if uniq:
            cleaned = re.sub(r"[^A-Za-z0-9]+", " ", uniq).strip()
            if cleaned:
                names.append(cleaned)
                parts = cleaned.split()
                # Focus on tail words
                if len(parts) >= 2:
                    names.append(" ".join(parts[-2:]))
                if len(parts) >= 3:
                    names.append(" ".join(parts[-3:]))

        # Deduplicate while preserving order
        seen = set()
        out = []
        for n in names:
            n_stripped = n.strip()
            if n_stripped and n_stripped not in seen:
                seen.add(n_stripped)
                out.append(n_stripped)
        return out

    def _candidate_roles(self, element: dict):
        '''
        Infer likely roles from ocr_type/tag_name + intent.
        Uses intent to avoid picking textbox when we really want a button.
        '''
        ocr = (element.get("ocr_type") or "").lower()
        tag = (element.get("tag_name") or "").lower()
        intent = (element.get("intent") or "").lower()

        roles = []

        # Heuristic: if intent is click-ish, strongly prefer button/link/combobox
        clickish = any(
            k in intent
            for k in [
                "click",
                "submit",
                "delete",
                "remove",
                "add",
                "create",
                "open",
                "next",
                "previous",
                "save",
                "confirm",
                "ok",
                "proceed",
            ]
        )
        inputish = any(
            k in intent for k in ["type", "enter", "fill", "search", "filter", "input"]
        )

        # Primary from ocr/tag
        if ocr in ("button", "submit", "iconbutton") or tag == "button":
            roles.append("button")
        if ocr in ("select", "dropdown", "combobox") or tag == "select":
            roles.append("combobox")
        if ocr in ("textbox", "text", "input", "email", "password") or tag in (
            "input",
            "textarea",
        ):
            roles.append("textbox")
        if ocr in ("link", "anchor") or tag == "a":
            roles.append("link")

        # Adjust ordering based on intent
        if clickish:
            ordered = []
            for r in ("button", "link", "combobox", "textbox"):
                if r in roles and r not in ordered:
                    ordered.append(r)
            if "textbox" in ordered:
                ordered.remove("textbox")
                ordered.append("textbox")
            roles = ordered
        elif inputish:
            ordered = []
            for r in ("textbox", "combobox", "button", "link"):
                if r in roles and r not in ordered:
                    ordered.append(r)
            roles = ordered

        # Always add generic fallbacks (order respected)
        for r in ("button", "combobox", "textbox", "link"):
            if r not in roles:
                roles.append(r)
        return roles

    def _map_tag_to_role(self, tag: str):
        tag_role_map = {
            "button": "button",
            "input": "textbox",
            "select": "combobox",
            "textarea": "textbox",
            "checkbox": "checkbox",
        }
        return tag_role_map.get((tag or "").lower(), None)

    def _is_click_like_element(self, element: dict) -> bool:
        ocr = (element.get("ocr_type") or "").lower()
        tag = (element.get("tag_name") or "").lower()
        intent = (element.get("intent") or "").lower()
        if ocr in ("button", "submit", "iconbutton", "link", "anchor"):
            return True
        if tag in ("button", "a"):
            return True
        return any(
            token in intent
            for token in (
                "click",
                "open",
                "close",
                "submit",
                "save",
                "confirm",
                "cancel",
                "calendar",
                "icon",
            )
        )

    def _is_generic_container_selector(self, selector: str) -> bool:
        text = (selector or "").strip().lower()
        if not text:
            return False
        if any(token in text for token in ("button", "[role=", "input", "textarea", "select", "a", "svg")):
            return False
        generic_prefixes = (
            "div",
            "span",
            ".mui",
            ".mat",
            ".ant-",
            ".chakra",
        )
        if text in ("div", "span"):
            return True
        if text.startswith(("div.", "span.")):
            return True
        return text.startswith(generic_prefixes)

    def _should_reject_strategy(self, element: dict, desc: str) -> bool:
        if not self._is_click_like_element(element):
            return False
        lowered = (desc or "").lower()
        css_selector = (element.get("css_selector") or element.get("css-selector") or "").strip()
        dom_class = (element.get("dom_class") or element.get("dom-class") or element.get("class_name") or "").strip()
        if "[css_selector]" in lowered and self._is_generic_container_selector(css_selector):
            return True
        if ("[class exact sanitized]" in lowered or "[class partial sanitized]" in lowered or "[class_list sanitized]" in lowered):
            class_selector = "." + ".".join(part for part in re.split(r"\s+", dom_class) if part)
            if self._is_generic_container_selector(class_selector):
                return True
        return False

    # ----------------------------------------------------------------- locators
    def _try_all_locators(self, element: dict, page):
        '''
        Try a layered set of locator strategies from strongest → weakest.
        Returns a *raw* Playwright Locator on success, or None.
        '''

        # Give the app some time to settle
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        strategies = []

        # Normalize dom-id / dom_class
        dom_id = element.get("dom_id") or element.get("dom-id") or element.get("id")
        dom_class = (
            element.get("dom_class")
            or element.get("dom-class")
            or element.get("class_name")
        )
        data_testid = element.get("data_testid") or element.get("data-testid")
        aria_label = element.get("aria_label") or element.get("aria-label")
        css_selector = element.get("css_selector") or element.get("css-selector")

        label_text = self._truncate_text_for_matching(element.get("label_text") or "")
        get_by_text_v = self._truncate_text_for_matching(element.get("get_by_text") or "")
        placeholder = self._truncate_text_for_matching(element.get("placeholder") or "")
        xpath = (element.get("xpath") or "").strip()
        raw_text = self._truncate_text_for_matching(element.get("text") or "")

        text_variants = []
        for t in [label_text, get_by_text_v, raw_text]:
            if t:
                text_variants.extend(self._synonym_texts(t))

        # ------- Test IDs (strong if present)
        if data_testid:
            def _by_test_id(data_testid=data_testid):
                return page.get_by_test_id(data_testid)

            strategies.append((_by_test_id, f"get_by_test_id('{data_testid}')"))

            def _by_test_id_css(data_testid=data_testid):
                safe = str(data_testid).replace('"', '\\"')
                return page.locator(f'[data-testid="{safe}"]')

            strategies.append((_by_test_id_css, f'locator([data-testid="{data_testid}"])'))

        # ------- aria-label (common for icon-only buttons)
        if aria_label:
            def _by_aria_label(aria_label=aria_label):
                return page.get_by_label(aria_label)

            strategies.append((_by_aria_label, f"get_by_label('{aria_label}') [aria-label]"))

            def _by_aria_button(aria_label=aria_label):
                return page.get_by_role("button", name=aria_label)

            strategies.append((_by_aria_button, f"get_by_role(button, name='{aria_label}') [aria-label]"))

            def _by_aria_locator(aria_label=aria_label):
                safe = str(aria_label).replace('"', '\\"')
                return page.locator(f'[aria-label="{safe}"]')

            strategies.append((_by_aria_locator, f'locator([aria-label="{aria_label}"])'))

        # ------- ROLE-BASED QUERIES (most robust when accessible names exist)
        names = self._names_for_roles(element)
        if names:
            roles = self._candidate_roles(element)
            for nm in names:
                for role in roles:
                    # Exact case-sensitive first
                    def _role_exact(nm=nm, role=role):
                        return page.get_by_role(role, name=nm)

                    strategies.append(
                        (_role_exact, f"get_by_role({role}, name='{nm}')")
                    )

                    # Case-insensitive regex
                    try:
                        if len(nm) > 200:
                            raise ValueError("name too long for regex selector")
                        regex = re.compile(re.escape(nm), re.IGNORECASE)

                        def _role_regex(regex=regex, role=role):
                            return page.get_by_role(role, name=regex)

                        strategies.append(
                            (_role_regex, f"get_by_role({role}, name=/{nm}/i)")
                        )
                    except Exception:
                        pass

        # ------- tag-to-role mapping with label_text
        tag = element.get("tag_name")
        if tag and label_text:
            role = self._map_tag_to_role(tag)
            if role:
                def _mapped_role(role=role, label_text=label_text):
                    return page.get_by_role(role, name=label_text)

                strategies.append(
                    (
                        _mapped_role,
                        f"get_by_role({role}, name='{label_text}') [tag-map]",
                    )
                )

        # ------- get_by_label (best for inputs/selects with associated <label>)
        if label_text:
            def _by_label(label_text=label_text):
                return page.get_by_label(label_text)

            strategies.append((_by_label, f"get_by_label('{label_text}')"))

        # ------- Exact visible text
        if label_text:
            def _by_text_exact(label_text=label_text):
                return page.get_by_text(label_text, exact=True)

            strategies.append(
                (_by_text_exact, f"get_by_text('{label_text}', exact=True)")
            )

        # ------- Loose text / substring / case-insensitive
        for txt in text_variants:
            def _by_text_contains(txt=txt):
                return page.get_by_text(txt)

            strategies.append((_by_text_contains, f"get_by_text('{txt}') [contains]"))

            try:
                regex = re.compile(re.escape(txt), re.IGNORECASE)

                def _by_text_regex(regex=regex):
                    return page.get_by_text(regex)

                strategies.append((_by_text_regex, f"get_by_text(/{txt}/i)"))
            except Exception:
                pass

        # ------- Placeholder
        if placeholder:
            for ph in self._synonym_texts(placeholder):
                def _by_placeholder(ph=ph):
                    return page.get_by_placeholder(ph)

                strategies.append((_by_placeholder, f"get_by_placeholder('{ph}')"))

        # ------- Sample value
        sample_value = (element.get("sample_value") or "").strip()
        if sample_value:
            def _by_display_value(sample_value=sample_value):
                return page.get_by_display_value(sample_value)

            strategies.append(
                (_by_display_value, f"get_by_display_value('{sample_value}')")
            )

        # ------- Raw css selector from metadata
        if css_selector:
            def _css_selector(css_selector=css_selector):
                return page.locator(css_selector)

            strategies.append((_css_selector, f"locator({css_selector}) [css_selector]"))

        # ------- Data attributes (test-id / qa)
        data_attrs = element.get("data_attrs") or {}
        if isinstance(data_attrs, dict):
            for k, v in data_attrs.items():
                if not v:
                    continue
                if "test" in k.lower() or "qa" in k.lower():
                    def _by_test_id(v=v):
                        return page.get_by_test_id(v)

                    strategies.append((_by_test_id, f"get_by_test_id('{v}') for {k}"))

        # ------- By ID (exact and partial)
        if dom_id:
            def _id_exact(dom_id=dom_id):
                safe = str(dom_id).replace('"', '\\"')
                if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*$", str(dom_id)):
                    return page.locator(f"#{dom_id}")
                return page.locator(f'[id="{safe}"]')

            strategies.append((_id_exact, f"locator(#{dom_id}) [ID exact]"))

            def _id_partial(dom_id=dom_id):
                safe = str(dom_id).replace('"', '\\"')
                return page.locator(f'[id="{safe}"], [id*="{safe}"]')

            strategies.append(
                (_id_partial, f'locator([id="{dom_id}"], [id*="{dom_id}"]) [ID partial]')
            )

        # ------- By dom_class (sanitized)
        if dom_class:
            tokens = str(dom_class).split()
            safe_tokens = self._sanitize_class_list(tokens)
            if safe_tokens:
                class_sel = "." + ".".join(safe_tokens)

                def _class_exact(class_sel=class_sel):
                    return page.locator(class_sel)

                strategies.append(
                    (_class_exact, f"locator({class_sel}) [class exact sanitized]")
                )

                def _class_partial(class_value=" ".join(safe_tokens)):
                    return page.locator(f'[class*="{class_value}"]')

                strategies.append(
                    (
                        _class_partial,
                        f'locator([class*="{ " ".join(safe_tokens) }"]) [class partial sanitized]',
                    )
                )

        # ------- By class_list (sanitized)
        class_list = element.get("class_list") or []
        if isinstance(class_list, list) and class_list:
            safe_classes = self._sanitize_class_list(class_list)
            if safe_classes:
                sel = "." + ".".join(safe_classes)

                def _class_list(sel=sel):
                    return page.locator(sel)

                strategies.append(
                    (_class_list, f"locator({sel}) [class_list sanitized]")
                )

        # ------- CSS / XPath from metadata
        locator_info = element.get("locator") or {}
        if isinstance(locator_info, dict):
            if locator_info.get("type") == "css" and locator_info.get("value"):
                css = locator_info["value"]

                def _css(css=css):
                    return page.locator(css)

                strategies.append((_css, f"locator({css}) [custom css]"))

            if locator_info.get("type") == "xpath" and locator_info.get("value"):
                xp = locator_info["value"]

                def _xp(xp=xp):
                    return page.locator(f"xpath={xp}")

                strategies.append((_xp, f"locator(xpath={xp}) [custom xpath]"))

        # If plain xpath field available
        if xpath:
            def _xp_field(xpath=xpath):
                return page.locator(f"xpath={xpath}")

            strategies.append((_xp_field, f"locator(xpath={xpath}) [xpath field]"))

        # ------- Execute in order
        for func, desc in strategies:
            try:
                if self._should_reject_strategy(element, desc):
                    print(f"[SmartAI][Skip] {desc} rejected as weak generic container match.")
                    continue
                locator = func()
                if not locator:
                    continue
                try:
                    count = locator.count()
                except Exception:
                    count = 1

                if count > 0:
                    print(f"[SmartAI][Return] {desc} succeeded (count={count}).")
                    self.locator_fail_count[element.get("unique_name")] = 0
                    return locator.first
            except Exception as e:
                unique_name = element.get("unique_name", "")
                self.locator_fail_count[unique_name] = (
                    self.locator_fail_count.get(unique_name, 0) + 1
                )
                print(f"[SmartAI][Skip] {desc} failed: {e}")

        # -------------------------------------------------------------
        # Semantic Text Healing Layer (matches text drift)
        # -------------------------------------------------------------
        semantic_candidates = []
        semantic_candidates_all = []
        try:
            orig_label = (element.get("label_text") or "").strip()
            if orig_label:
                # search similar visible buttons/links
                candidates_loc = page.locator('button, [role="button"], a')

                try:
                    total = candidates_loc.count()
                except Exception:
                    total = 0

                total = min(total, 80)  # cap for performance

                for i in range(total):
                    loc = candidates_loc.nth(i)
                    try:
                        txt = loc.inner_text().strip()
                        if not txt:
                            continue

                        # --- Parent / Sibling boosting logic ---
                        parent = (element.get("parent_block_text") or "").lower()
                        sibling_list = element.get("sibling_text") or []
                        siblings = sibling_list if isinstance(sibling_list, list) else [sibling_list]

                        base_score = self._semantic_similarity(orig_label, txt)

                        parent_bonus = 0.15 if parent and parent in txt.lower() else 0
                        sibling_bonus = 0.10 if any(s.lower() in txt.lower() for s in siblings) else 0

                        score = base_score + parent_bonus + sibling_bonus

                        semantic_candidates_all.append((score, loc))
                        if score >= 0.45:   # threshold after boosting
                            semantic_candidates.append((score, loc))

                    except Exception:
                        continue


            if semantic_candidates:
                # If the boosted score includes parent/sibling matches,
                # prefer those above plain semantic similarity
                semantic_candidates = sorted(semantic_candidates, key=lambda x: x[0], reverse=True)
                semantic_candidates_all = sorted(semantic_candidates_all, key=lambda x: x[0], reverse=True)
                best_score, best_loc = semantic_candidates[0]
                if len(semantic_candidates_all) > 1:
                    second_score, _second_loc = semantic_candidates_all[1]
                    if best_score >= 0.45 and best_score - second_score < 0.10:
                        raise SmartAILocatorError(
                            "Ambiguous semantic matches found for element."
                        )
                try:
                    healed_text = best_loc.inner_text().strip()
                except Exception:
                    healed_text = "<unreadable>"
                print(
                    f"[SmartAI][Semantic] '{orig_label}' healed to '{healed_text}' score={best_score:.2f}"
                )
                return best_loc.first

        except Exception as e:
            print(f"[SmartAI][Semantic search failed] {e}")

        print("[SmartAI][Return] No locator found for element.")
        return None

    # ----------------------------------------------------------------- ML heal
    def _ml_self_heal(self, unique_name: str):
        '''
        ML healing based on:
          - unique_name
          - label_text
          - get_by_text
          - placeholder
        '''
        queries = []
        if unique_name:
            queries.append(unique_name)

        # include OCR and DOM visible text for ML search
        base_el = next(
            (el for el in self.metadata if el.get("unique_name") == unique_name), None
        )
        if base_el:
            for key in ("label_text", "get_by_text", "placeholder", "text"):
                v = (base_el.get(key) or "").strip()
                if v:
                    queries.append(v)

        if not queries:
            return None, 0.0

        self._ensure_metadata_embeddings()
        if not self.embeddings:
            return None, 0.0

        query_vecs = [self.encoder.encode(q) for q in queries]

        scores = []
        for emb in self.embeddings:
            try:
                element_best = max(
                    self.encoder.similarity_vec(qv, emb) for qv in query_vecs
                )
            except Exception:
                element_best = 0.0
            scores.append(element_best)

        best_idx = int(np.argmax(scores))
        best_score = scores[best_idx]

        print(f"[SmartAI] ML healed best match score: {best_score:.2f}")
        if best_score < 0.50:
            return None, best_score

        return self.metadata[best_idx], best_score

    # ---------------------------------------------------------------- brute
    def _brute_force_locator(self, element: dict, page):
        '''
        Last-resort text-based sweep when ML score is high but structured locators failed.
        Uses neutral text variants only (no domain-specific hardcoding).
        '''
        texts = []
        for k in ("label_text", "get_by_text", "placeholder", "text"):
            v = (element.get(k) or "").strip()
            if v:
                texts.extend(self._synonym_texts(v))

        uniq = (element.get("unique_name") or "").strip()
        if uniq:
            cleaned = re.sub(r"[^A-Za-z0-9]+", " ", uniq).strip()
            if cleaned:
                texts.append(cleaned)
                parts = cleaned.split()
                if len(parts) > 3:
                    texts.append(" ".join(parts[-3:]))
                if len(parts) >= 2:
                    texts.append(" ".join(parts[-2:]))

        tried = set()
        for txt in texts:
            if not txt or txt in tried:
                continue
            tried.add(txt)

            try:
                loc = page.get_by_text(txt)
                if loc.count() > 0:
                    print(f"[SmartAI][Brute] get_by_text('{txt}') succeeded.")
                    return loc.first
            except Exception:
                pass

            try:
                regex = re.compile(re.escape(txt), re.IGNORECASE)
                loc = page.get_by_role("button", name=regex)
                if loc.count() > 0:
                    print(f"[SmartAI][Brute] role=button regex '{txt}' succeeded.")
                    return loc.first
            except Exception:
                pass

            try:
                loc = page.get_by_role("link", name=txt)
                if loc.count() > 0:
                    print(f"[SmartAI][Brute] link name='{txt}' succeeded.")
                    return loc.first
            except Exception:
                pass

            try:
                regex = re.compile(re.escape(txt), re.IGNORECASE)
                loc = page.get_by_role("link", name=regex)
                if loc.count() > 0:
                    print(f"[SmartAI][Brute] link regex '{txt}' succeeded.")
                    return loc.first
            except Exception:
                pass

        return None

    # ----------------------------------------------------------------- entry
    def _find_by_unique_name(self, unique_name: str):
        return next(
            (e for e in self.metadata if e.get("unique_name") == unique_name), None
        )

    def find_element(self, unique_name: str, page):
        '''
        Main entry for SmartAI from tests:
            page.smartAI("<unique_name>").click()
        '''
        element = self._find_by_unique_name(unique_name)

        # 1) Try exact metadata-driven strategies
        if element:
            locator = self._try_all_locators(element, page)
            if locator:
                print(
                    f"[SmartAI] Element '{unique_name}' found using primary metadata."
                )
                self._log_healed_locator(unique_name, element)
                return SmartAIWrappedLocator(locator, page, element_meta=element)

            print(
                f"[SmartAI] Primary methods failed for '{unique_name}', trying ML self-healing..."
            )

        # 2) ML-based fallback
        element_ml, ml_score = self._ml_self_heal(unique_name)
        if element_ml:
            locator_ml = self._try_all_locators(element_ml, page)
            if locator_ml:
                print(
                    f"[SmartAI] Healed element via ML ({ml_score:.2f}): '{element_ml.get('unique_name')}'"
                )
                self._log_healed_locator(unique_name, element_ml)
                return SmartAIWrappedLocator(locator_ml, page, element_meta=element_ml)

            # If structured locators failed but score is still strong, brute-force text sweep
            if ml_score >= 0.50:
                locator_generic = self._brute_force_locator(element_ml, page)
                if locator_generic:
                    print(
                        f"[SmartAI] Healed element via generic text sweep ({ml_score:.2f}): '{element_ml.get('unique_name')}'"
                    )
                    self._log_healed_locator(unique_name, element_ml)
                    return SmartAIWrappedLocator(locator_generic, page, element_meta=element_ml)

        # 3) Intent-based fallback (nearest neighbor by intent)
        target_intent = (
            (element_ml or element or {}).get("intent") if (element_ml or element) else None
        )
        if target_intent:
            for e in self.metadata:
                if e.get("intent") == target_intent and e.get("unique_name") != unique_name:
                    locator = self._try_all_locators(e, page)
                    if locator:
                        print(
                            f"[SmartAI] Healed element by intent ('{target_intent}'): '{e.get('unique_name')}'"
                        )
                        self._log_healed_locator(unique_name, e)
                        return SmartAIWrappedLocator(locator, page, element_meta=e)

        raise SmartAILocatorError(
            f"Element '{unique_name}' not found and cannot self-heal."
        )


# ====== PAGE PATCH (FULL SMARTAI WRAPPER INJECTION) ======


def patch_page_with_smartai(page, metadata):
    '''
    Patch a Playwright Page so that:
      - page.locator(...) and all get_by_* methods return SmartAIWrappedLocator
      - page.smartAI(<unique_name>) does metadata-driven self-healing lookup
    '''
    healer = SmartAISelfHealing(metadata or [])

    # 1️⃣ ---- WRAP ANY LOCATOR WITH SmartAIWrappedLocator ----
    def wrap_locator(original_func):
        @wraps(original_func)
        def wrapper(*args, **kwargs):
            locator = original_func(*args, **kwargs)
            return SmartAIWrappedLocator(locator, page)

        return wrapper

    # 2️⃣ ---- OVERRIDE page.locator ----
    if hasattr(page, "locator"):
        page.locator = wrap_locator(page.locator)

    # 3️⃣ ---- OVERRIDE every get_by_* ----
    get_by_methods = [
        "get_by_role",
        "get_by_text",
        "get_by_label",
        "get_by_placeholder",
        "get_by_alt_text",
        "get_by_title",
        "get_by_test_id",
        "get_by_display_value",
    ]

    for method_name in get_by_methods:
        if hasattr(page, method_name):
            setattr(page, method_name, wrap_locator(getattr(page, method_name)))

    # 4️⃣ ---- expose SmartAI direct lookup (unique_name-based healing) ----
    def smartAI(unique_name: str):
        return healer.find_element(unique_name, page)

    page.smartAI = smartAI

    print("[SmartAI] Page successfully patched with locator wrappers.")
    return page
"""


ALLURE_RUNTIME_CODE = """from __future__ import annotations

import os
import re
import traceback
from pathlib import Path

try:
    from allure_commons._core import plugin_manager
    from allure_commons._hooks import hookimpl
    from allure_commons.logger import AllureFileLogger
    from allure_commons.model2 import Parameter, Status, StatusDetails, TestResult, TestStepResult
    from allure_commons.reporter import AllureReporter
    from allure_commons.utils import now, uuid4
except Exception:  # pragma: no cover - optional dependency
    plugin_manager = None
    AllureFileLogger = None
    hookimpl = None
    AllureReporter = None
    Parameter = None
    Status = None
    StatusDetails = None
    TestResult = None
    TestStepResult = None
    now = None
    uuid4 = None


_LOGGER = None
_REPORTER = None
_LISTENER = None
_CURRENT_TEST_UUID = None
_CURRENT_PAGE = None


def _results_dir() -> Path | None:
    env_dir = os.getenv("ALLURE_RESULTS_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    return None


def _ensure_lifecycle():
    global _LOGGER, _REPORTER, _LISTENER
    if AllureFileLogger is None or AllureReporter is None or plugin_manager is None:
        return None
    results_dir = _results_dir()
    if not results_dir:
        return None
    results_dir.mkdir(parents=True, exist_ok=True)

    if _LOGGER is None:
        _LOGGER = AllureFileLogger(str(results_dir))
    try:
        if _LOGGER not in plugin_manager.get_plugins():
            plugin_manager.register(_LOGGER)
    except Exception:
        pass

    if _REPORTER is None:
        _REPORTER = AllureReporter()

    if _LISTENER is None:
        _LISTENER = _StandaloneAllureListener(_REPORTER)
        try:
            if _LISTENER not in plugin_manager.get_plugins():
                plugin_manager.register(_LISTENER)
        except Exception:
            pass

    return _REPORTER


def set_current_page(page):
    global _CURRENT_PAGE
    _CURRENT_PAGE = page


def _sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", name or "test")


def _highlight_last_locator(page) -> None:
    try:
        locator = getattr(page, "_last_locator", None)
        if not locator:
            return
        target = None
        try:
            target = locator.first if hasattr(locator, "first") else locator
        except Exception:
            target = locator
        if hasattr(target, "scroll_into_view_if_needed"):
            try:
                target.scroll_into_view_if_needed(timeout=1000)
            except Exception:
                pass
        try:
            target.evaluate(
                "el => { if (!el) return; el.setAttribute('data-smartai-highlight','1');"
                "el.style.outline='3px solid #ff3b30'; el.style.outlineOffset='2px';"
                "el.style.boxShadow='0 0 0 2px rgba(255,59,48,0.4)'; }"
            )
        except Exception:
            pass
    except Exception:
        pass


def _capture_failure_screenshot(test_name: str, test_uuid: str | None):
    page = _CURRENT_PAGE
    if page is None:
        return None
    try:
        results_dir = _results_dir()
        if not results_dir:
            return None
        results_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _sanitize_filename(test_name)
        suffix = f"_{test_uuid}" if test_uuid else ""
        path = results_dir / f"{safe_name}{suffix}_failure.png"
        try:
            _highlight_last_locator(page)
            page.screenshot(path=str(path), full_page=False)
        except Exception:
            return None
        return path
    except Exception:
        return None


class _StandaloneAllureListener:
    def __init__(self, reporter):
        self.reporter = reporter

    @hookimpl
    def start_step(self, uuid, title, params):
        if TestStepResult is None:
            return
        step = TestStepResult()
        step.name = title
        if now:
            step.start = now()
        if Parameter is not None and isinstance(params, dict) and params:
            step.parameters = [
                Parameter(name=str(key), value=str(value))
                for key, value in params.items()
            ]
        self.reporter.start_step(_CURRENT_TEST_UUID, uuid, step)

    @hookimpl
    def stop_step(self, uuid, exc_type, exc_val, exc_tb):
        kwargs = {}
        if exc_type and Status is not None:
            kwargs["status"] = Status.FAILED
            if StatusDetails is not None:
                kwargs["statusDetails"] = StatusDetails(
                    message=str(exc_val),
                    trace="".join(traceback.format_exception(exc_type, exc_val, exc_tb)),
                )
        elif Status is not None:
            kwargs["status"] = Status.PASSED
        if now:
            kwargs["stop"] = now()
        self.reporter.stop_step(uuid, **kwargs)

    @hookimpl
    def attach_data(self, body, name, attachment_type, extension):
        attachment_uuid = uuid4() if uuid4 else _CURRENT_TEST_UUID
        self.reporter.attach_data(
            attachment_uuid,
            body,
            name=name,
            attachment_type=attachment_type,
            extension=extension,
        )

    @hookimpl
    def attach_file(self, source, name, attachment_type, extension):
        attachment_uuid = uuid4() if uuid4 else _CURRENT_TEST_UUID
        self.reporter.attach_file(
            attachment_uuid,
            source,
            name=name,
            attachment_type=attachment_type,
            extension=extension,
        )


def run_allure_case(name: str, func, *args, **kwargs):
    global _CURRENT_TEST_UUID
    reporter = _ensure_lifecycle()
    if reporter is None or TestResult is None or Status is None:
        return func(*args, **kwargs)
    outcome = None
    error = None
    test_result = TestResult()
    if uuid4:
        test_result.uuid = uuid4()
    test_result.name = name
    if now:
        test_result.start = now()
    test_uuid = test_result.uuid
    reporter.schedule_test(test_uuid, test_result)
    _CURRENT_TEST_UUID = test_uuid
    try:
        outcome = func(*args, **kwargs)
        test_result.status = Status.PASSED
    except Exception as exc:
        error = exc
        test_result.status = Status.FAILED
        if StatusDetails:
            test_result.statusDetails = StatusDetails(
                message=str(exc),
                trace=traceback.format_exc(),
            )
        try:
            screenshot_path = _capture_failure_screenshot(name, test_uuid)
            if screenshot_path and reporter is not None:
                reporter.attach_file(
                    test_uuid,
                    str(screenshot_path),
                    name="Failure Screenshot",
                    attachment_type="image/png",
                    extension="png",
                )
        except Exception:
            pass
    finally:
        if now:
            test_result.stop = now()
        _CURRENT_TEST_UUID = None
    reporter.close_test(test_uuid)
    if error:
        raise error
    return outcome
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
    request_src = get_request_src_dir()
    if request_src:
        return Path(request_src)
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

    ui_actions_src = Path(__file__).resolve().parent / "ui_actions_sync.py"
    ui_actions_file = lib_path / "ui_actions.py"
    try:
        ui_actions_content = ui_actions_src.read_text(encoding="utf-8")
    except Exception:
        ui_actions_content = ""
    ui_actions_file.write_text(ui_actions_content, encoding="utf-8")
    _persist_storage_file(storage, ui_actions_file, ui_actions_content)

    allure_runtime_file = lib_path / "allure_runtime.py"
    allure_runtime_file.write_text(ALLURE_RUNTIME_CODE, encoding="utf-8")
    _persist_storage_file(storage, allure_runtime_file, ALLURE_RUNTIME_CODE)

def analyze_test_case_content(content: str) -> dict:
    tags = []
    priority = "Low"
    lowered = (content or "").lower()

    is_negative = "negative" in lowered
    is_edge = "edge" in lowered
    is_positive = "positive" in lowered

    if is_negative or is_edge:
        tags.append("functional")
    else:
        regression_keywords = ("verify", "ensure", "check", "all fields")
        if any(keyword in lowered for keyword in regression_keywords) or is_positive:
            tags.append("regression")

    medium_keywords = ("ui", "visual", "layout", "style")
    if any(keyword in lowered for keyword in medium_keywords):
        priority = "Medium"

    return {"tags": tags, "priority": priority}
