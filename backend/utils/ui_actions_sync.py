from __future__ import annotations

import re
import time
from typing import Callable, Optional, Sequence, Union

from playwright.sync_api import BrowserContext, Dialog, Download, FileChooser, Frame, FrameLocator, Locator, Page, Request, Response, expect


def safe_wait_ready(page: Page, wait_until: str = "domcontentloaded", timeout: int = 60000) -> None:
    page.wait_for_load_state(wait_until, timeout=timeout)

def safe_wait_url(page: Page, url_or_pattern, timeout: int = 60000) -> None:
    expect(page).to_have_url(url_or_pattern, timeout=timeout)

def safe_wait_load_state(page: Page, state: str = "domcontentloaded", timeout: int = 60000) -> None:
    page.wait_for_load_state(state, timeout=timeout)


def safe_click(
    locator: Locator,
    *,
    wait_visible: bool = True,
    wait_enabled: bool = True,
    timeout: int = 6000,
) -> None:
    if wait_visible:
        expect(locator).to_be_visible(timeout=timeout)
    if wait_enabled:
        expect(locator).to_be_enabled(timeout=timeout)
    locator.click()


def safe_fill(
    locator: Locator,
    value: str,
    *,
    clear_first: bool = False,
    timeout: int = 6000,
) -> None:
    expect(locator).to_be_visible(timeout=timeout)
    if clear_first:
        locator.fill("")
    locator.fill(str(value))


def safe_select(
    locator: Locator,
    *,
    value: Optional[str] = None,
    label: Optional[str] = None,
    index: Optional[int] = None,
    timeout: int = 6000,
) -> None:
    expect(locator).to_be_visible(timeout=timeout)
    locator.select_option(value=value, label=label, index=index)


def _as_file_list(file_paths: Union[str, Sequence[str]]) -> Union[str, list[str]]:
    if isinstance(file_paths, str):
        return file_paths
    return [str(p) for p in file_paths]


def _is_file_input(locator: Locator) -> bool:
    try:
        return bool(
            locator.evaluate(
                "el => el && el.tagName && el.tagName.toLowerCase() === 'input' && el.type === 'file'"
            )
        )
    except Exception:
        return False


def _resolve_file_input_target(locator: Locator, page: Optional[Page]) -> Locator:
    base = locator.first
    if _is_file_input(base):
        return base
    try:
        direct = base.locator("input[type='file']")
        if direct.count() > 0:
            return direct.first
    except Exception:
        pass
    try:
        for_attr = base.get_attribute("for")
        if for_attr and page is not None:
            by_for = page.locator(f"#{for_attr}")
            if by_for.count() > 0:
                return by_for.first
    except Exception:
        pass
    try:
        container = base.locator(
            "xpath=ancestor::*[self::label or self::div or self::form][1]//input[@type='file']"
        )
        if container.count() > 0:
            return container.first
    except Exception:
        pass
    try:
        following = base.locator("xpath=following::input[@type='file'][1]")
        if following.count() > 0:
            return following.first
    except Exception:
        pass
    return base


def safe_upload(
    locator_or_input: Locator,
    file_paths: Union[str, Sequence[str]],
    *,
    page: Optional[Page] = None,
    wait_for_completion: bool = True,
    timeout: int = 6000,
) -> None:
    target = _resolve_file_input_target(locator_or_input, page)
    try:
        target.wait_for(state="attached", timeout=timeout)
    except Exception:
        pass
    target.set_input_files(_as_file_list(file_paths))
    if wait_for_completion:
        try:
            expect(target).to_have_value(re.compile(".+"), timeout=timeout)
        except Exception:
            pass


def dismiss_cookie_banner(page: Page) -> bool:
    cookie_text = re.compile(r"(cookie|consent|gdpr|privacy|tracking)", re.I)
    decline_patterns = [
        r"decline",
        r"reject",
        r"disagree",
        r"deny",
        r"refuse",
        r"opt out",
        r"no thanks",
        r"not now",
        r"cancel",
        r"only necessary",
        r"essential only",
        r"manage preferences",
        r"settings",
    ]
    accept_patterns = [
        r"accept all",
        r"accept",
        r"i agree",
        r"agree",
        r"ok",
        r"okay",
        r"got it",
        r"continue",
        r"yes",
        r"close",
        r"dismiss",
        r"skip",
    ]

    banner_selectors = [
        "[id*='cookie' i]",
        "[class*='cookie' i]",
        "[data-testid*='cookie' i]",
        "[data-test*='cookie' i]",
        "[id*='consent' i]",
        "[class*='consent' i]",
        "[data-testid*='consent' i]",
        "[data-test*='consent' i]",
        "[id*='gdpr' i]",
        "[class*='gdpr' i]",
        "[id*='privacy' i]",
        "[class*='privacy' i]",
        "[aria-label*='cookie' i]",
        "[aria-label*='consent' i]",
    ]

    def _promote_container(candidate):
        try:
            container = candidate.locator(
                "xpath=ancestor-or-self::*[self::div or self::section or self::aside or self::dialog or @role='dialog' or @aria-modal='true'][1]"
            ).first
            if container.is_visible(timeout=600):
                return container
        except Exception:
            pass
        return candidate

    def _find_cookie_banner():
        for selector in banner_selectors:
            try:
                loc = page.locator(selector)
                try:
                    filtered = loc.filter(has_text=cookie_text).first
                    if filtered.is_visible(timeout=600):
                        return _promote_container(filtered)
                except Exception:
                    pass
                candidate = loc.first
                if candidate.is_visible(timeout=600):
                    return _promote_container(candidate)
            except Exception:
                continue
        try:
            text_loc = page.get_by_text(cookie_text).first
            if text_loc.is_visible(timeout=600):
                container = text_loc.locator(
                    "xpath=ancestor-or-self::*[self::div or self::section or self::aside or self::dialog or @role='dialog' or @aria-modal='true'][1]"
                ).first
                if container.is_visible(timeout=600):
                    return container
        except Exception:
            pass
        return None

    def _try_patterns(scope, patterns) -> bool:
        for pat in patterns:
            try:
                locator = scope.get_by_role("button", name=re.compile(pat, re.I)).first
                if locator.is_visible(timeout=800):
                    locator.click(timeout=1000)
                    return True
            except Exception:
                continue
        return False

    banner = _find_cookie_banner()
    if not banner:
        return False

    if _try_patterns(banner, decline_patterns):
        return True
    if _try_patterns(banner, accept_patterns):
        return True
    fallback_selectors = [
        "button[aria-label*='decline' i]",
        "button[aria-label*='reject' i]",
        "button[aria-label*='cancel' i]",
        "button[aria-label*='deny' i]",
        "button[aria-label*='accept' i]",
        "button[aria-label*='close' i]",
        "button:has-text('Accept all')",
        "button:has-text('Decline')",
        "button:has-text('Reject')",
        "button:has-text('Cancel')",
        "button:has-text('No thanks')",
        "button:has-text('Accept')",
        "button:has-text('I agree')",
        "button:has-text('Close')",
        "button:has-text('Not now')",
        "button:has-text('Skip')",
        "button:has-text('Only necessary')",
        "button:has-text('Essential only')",
        "button:has-text('Manage preferences')",
        "button:has-text('Settings')",
        "button:has-text('×')",
        "span:has-text('×')",
        "a:has-text('Accept')",
        "a:has-text('Accept all')",
        "a:has-text('I agree')",
        "a:has-text('Close')",
        "[aria-label*='accept' i]",
        "[aria-label*='close' i]",
        "[aria-label*='decline' i]",
        "[aria-label*='reject' i]",
        "[aria-label*='cancel' i]",
        "[data-testid*='cookie' i] button",
        "[id*='cookie' i] button",
        "[class*='cookie' i] button",
        "[id*='consent' i] button",
        "[class*='consent' i] button",
        "[data-testid*='consent' i] button",
        "[data-test*='consent' i] button",
        "[id*='gdpr' i] button",
        "[class*='gdpr' i] button",
        "[id*='privacy' i] button",
        "[class*='privacy' i] button",
    ]
    for selector in fallback_selectors:
        try:
            locator = banner.locator(selector).first
            if locator.is_visible(timeout=1000):
                locator.click(timeout=1000)
                return True
        except Exception:
            continue
    return False


def safe_expect_dialog(
    page: Page,
    action: Callable[[], None],
    *,
    accept: bool = True,
    prompt_text: Optional[str] = None,
    timeout: int = 60000,
) -> Dialog:
    with page.expect_dialog(timeout=timeout) as dlg_info:
        action()
    dialog = dlg_info.value
    if accept:
        dialog.accept(prompt_text)
    else:
        dialog.dismiss()
    return dialog


def safe_expect_download(
    page: Page,
    action: Callable[[], None],
    *,
    path: Optional[str] = None,
    timeout: int = 60000,
) -> Download:
    with page.expect_download(timeout=timeout) as dl_info:
        action()
    download = dl_info.value
    if path:
        download.save_as(path)
    return download


def safe_expect_popup(
    page: Page,
    action: Callable[[], None],
    *,
    timeout: int = 60000,
) -> Page:
    with page.expect_popup(timeout=timeout) as popup_info:
        action()
    return popup_info.value


def safe_expect_new_page(
    context: BrowserContext,
    action: Callable[[], None],
    *,
    timeout: int = 60000,
) -> Page:
    with context.expect_page(timeout=timeout) as page_info:
        action()
    return page_info.value


def safe_expect_file_chooser(
    page: Page,
    action: Callable[[], None],
    *,
    files: Optional[Union[str, Sequence[str]]] = None,
    timeout: int = 60000,
) -> FileChooser:
    with page.expect_file_chooser(timeout=timeout) as fc_info:
        action()
    chooser = fc_info.value
    if files is not None:
        chooser.set_files(_as_file_list(files))
    return chooser


def safe_expect_response(
    page: Page,
    url_or_predicate,
    *,
    action: Optional[Callable[[], None]] = None,
    timeout: int = 60000,
) -> Response:
    if action is None:
        return page.wait_for_response(url_or_predicate, timeout=timeout)
    with page.expect_response(url_or_predicate, timeout=timeout) as resp_info:
        action()
    return resp_info.value


def safe_expect_request(
    page: Page,
    url_or_predicate,
    *,
    action: Optional[Callable[[], None]] = None,
    timeout: int = 60000,
) -> Request:
    if action is None:
        return page.wait_for_request(url_or_predicate, timeout=timeout)
    with page.expect_request(url_or_predicate, timeout=timeout) as req_info:
        action()
    return req_info.value


def resolve_frame(page: Page, name_or_url: str) -> Optional[Frame]:
    if not name_or_url:
        return None
    for frame in page.frames:
        if frame.name == name_or_url:
            return frame
        if frame.url and name_or_url in frame.url:
            return frame
    return None


def resolve_frame_locator(page: Page, frame_path: str) -> FrameLocator:
    context: FrameLocator = page.frame_locator("iframe")
    if not frame_path:
        return context
    for segment in [seg.strip() for seg in str(frame_path).split("/") if seg.strip()]:
        safe = segment.replace("'", "\\'")
        context = context.frame_locator(f"iframe#{safe}, iframe[name='{safe}'], iframe[id='{safe}'], iframe")
    return context


def safe_key_sequence(page: Page, keys: Sequence[str], delay: int = 50) -> None:
    for key in keys:
        page.keyboard.press(key, delay=delay)


def safe_key_chord(page: Page, chord: str, delay: int = 50) -> None:
    page.keyboard.press(chord, delay=delay)


def safe_type(page: Page, text: str, delay: int = 0) -> None:
    page.keyboard.type(str(text), delay=delay)


def safe_mouse_wheel(page: Page, dx: int = 0, dy: int = 120) -> None:
    page.mouse.wheel(dx, dy)


def _resolve_page_from_locators(source: Locator, target: Locator, page: Optional[Page]) -> Optional[Page]:
    if page is not None:
        return page
    for locator in (source, target):
        for attr in ("_page", "page"):
            try:
                candidate = getattr(locator, attr, None)
                if candidate is not None:
                    return candidate
            except Exception:
                continue
    return None


def _locator_from_candidates(locator: Locator, bbox_hint: Optional[dict] = None) -> Locator:
    try:
        count = locator.count()
    except Exception:
        return locator.first
    if count <= 1:
        return locator.first

    best = None
    best_score = None
    max_items = min(count, 6)
    for i in range(max_items):
        candidate = locator.nth(i)
        try:
            if not candidate.is_visible():
                continue
            bbox = candidate.bounding_box()
            if not bbox:
                continue
        except Exception:
            continue

        score = 0.0
        if bbox_hint:
            try:
                hx = bbox_hint.get("x", 0) + (bbox_hint.get("w", bbox_hint.get("width", 0)) / 2)
                hy = bbox_hint.get("y", 0) + (bbox_hint.get("h", bbox_hint.get("height", 0)) / 2)
                cx = (bbox.get("x", 0)) + (bbox.get("width", 0) / 2)
                cy = (bbox.get("y", 0)) + (bbox.get("height", 0) / 2)
                dx = abs(cx - hx)
                dy = abs(cy - hy)
                score = -(dx + dy)
            except Exception:
                score = 0.0
        else:
            score = (bbox.get("width", 0) * bbox.get("height", 0))

        if best_score is None or score > best_score:
            best = candidate
            best_score = score

    return best if best is not None else locator.first


def _point_from_bbox(bbox: dict, position: str, custom: Optional[dict]) -> tuple[float, float]:
    x = float(bbox.get("x", 0))
    y = float(bbox.get("y", 0))
    w = float(bbox.get("width", 0))
    h = float(bbox.get("height", 0))
    if position == "topleft":
        px, py = x + 2, y + 2
    elif position == "custom" and custom:
        px, py = x + float(custom.get("dx", 0)), y + float(custom.get("dy", 0))
    else:
        px, py = x + (w / 2), y + (h / 2)
    return px, py


def _dispatch_html5_drag(page: Page, source: Locator, target: Locator) -> None:
    source_handle = source.element_handle()
    target_handle = target.element_handle()
    if source_handle is None or target_handle is None:
        raise RuntimeError("Unable to resolve element handles for HTML5 drag-and-drop.")
    page.evaluate(
        """
        ([source, target]) => {
          const dataTransfer = new DataTransfer();
          const fire = (el, type, dt) => {
            const evt = new DragEvent(type, {
              bubbles: true,
              cancelable: true,
              dataTransfer: dt
            });
            el.dispatchEvent(evt);
          };
          fire(source, 'dragstart', dataTransfer);
          fire(target, 'dragenter', dataTransfer);
          fire(target, 'dragover', dataTransfer);
          fire(target, 'drop', dataTransfer);
          fire(source, 'dragend', dataTransfer);
        }
        """,
        [source_handle, target_handle],
    )


def safe_drag_and_drop(
    source: Locator,
    target: Locator,
    timeout: int = 30000,
    *,
    page: Optional[Page] = None,
    method: str = "auto",
    start_position: str = "center",
    end_position: str = "center",
    custom_start: Optional[dict] = None,
    custom_end: Optional[dict] = None,
    hold_ms: int = 150,
    move_steps: int = 20,
    retries: int = 2,
    screenshot_on_fail: bool = True,
    source_bbox_hint: Optional[dict] = None,
    target_bbox_hint: Optional[dict] = None,
) -> None:
    """
    Robust drag-and-drop with fallback strategies.
    Supports Playwright drag_to, mouse-based drag, and HTML5 event dispatch.
    """
    page = _resolve_page_from_locators(source, target, page)
    attempt = 0
    last_error: Optional[Exception] = None
    method = (method or "auto").lower()

    while attempt <= retries:
        attempt += 1
        try:
            src = _locator_from_candidates(source, source_bbox_hint)
            tgt = _locator_from_candidates(target, target_bbox_hint)

            expect(src).to_be_visible(timeout=timeout)
            expect(tgt).to_be_visible(timeout=timeout)
            try:
                src.scroll_into_view_if_needed(timeout=timeout)
            except Exception:
                pass
            try:
                tgt.scroll_into_view_if_needed(timeout=timeout)
            except Exception:
                pass

            used_method = method
            if method in ("auto", "playwright"):
                try:
                    src.drag_to(tgt, timeout=timeout)
                    used_method = "playwright"
                    if page is not None:
                        page._last_action = f"DRAG_AND_DROP: source -> target (method={used_method})"
                        page._last_locator = src
                    return
                except Exception as exc:
                    last_error = exc
                    if method == "playwright":
                        raise

            if method in ("auto", "mouse"):
                if page is None:
                    raise RuntimeError("Mouse drag requires a Page instance.")
                bbox_s = src.bounding_box()
                bbox_t = tgt.bounding_box()
                if not bbox_s or not bbox_t:
                    raise RuntimeError("Unable to resolve bounding boxes for drag-and-drop.")
                start = _point_from_bbox(bbox_s, start_position.lower(), custom_start)
                end = _point_from_bbox(bbox_t, end_position.lower(), custom_end)
                page.mouse.move(*start)
                page.mouse.down()
                if hold_ms:
                    time.sleep(max(hold_ms, 0) / 1000)
                page.mouse.move(*end, steps=max(1, move_steps))
                page.mouse.up()
                used_method = "mouse"
                if page is not None:
                    page._last_action = f"DRAG_AND_DROP: source -> target (method={used_method})"
                    page._last_locator = src
                return

            if method in ("auto", "html5", "js"):
                if page is None:
                    raise RuntimeError("HTML5 drag requires a Page instance.")
                _dispatch_html5_drag(page, src, tgt)
                used_method = "html5"
                if page is not None:
                    page._last_action = f"DRAG_AND_DROP: source -> target (method={used_method})"
                    page._last_locator = src
                return

        except Exception as exc:
            last_error = exc
            if attempt > retries:
                break
            try:
                if page is not None and screenshot_on_fail:
                    page.screenshot(path=f"drag_drop_retry_{attempt}.png", full_page=False)
            except Exception:
                pass
            continue

    if page is not None:
        try:
            page._last_action = "DRAG_AND_DROP: failed"
            page._last_locator = source
        except Exception:
            pass
    if last_error is not None:
        raise last_error
    raise RuntimeError("Drag-and-drop failed without a specific error.")
