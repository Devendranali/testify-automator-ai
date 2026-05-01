from __future__ import annotations

import re
from pathlib import Path

import pytest

import sys

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from utils import smart_ai_utils  # noqa: E402


class FakeElement:
    def __init__(
        self,
        text: str = "",
        role: str | None = None,
        label: str | None = None,
        placeholder: str | None = None,
        test_id: str | None = None,
        dom_id: str | None = None,
        name: str | None = None,
        tag: str | None = None,
        value: str | None = None,
    ):
        self.text = text or ""
        self.role = role or ""
        self.label = label or ""
        self.placeholder = placeholder or ""
        self.tag = tag or ""
        self.attrs = {}
        if test_id:
            self.attrs["data-testid"] = test_id
        if dom_id:
            self.attrs["id"] = dom_id
        if name:
            self.attrs["name"] = name
        if label:
            self.attrs["aria-label"] = label
        if value:
            self.attrs["value"] = value


class FakeLocator:
    def __init__(self, items: list[FakeElement]):
        self._items = items

    def count(self):
        return len(self._items)

    def nth(self, idx: int):
        if idx < 0 or idx >= len(self._items):
            return FakeLocator([])
        return FakeLocator([self._items[idx]])

    @property
    def first(self):
        return self.nth(0)

    def inner_text(self):
        if not self._items:
            return ""
        return self._items[0].text

    def get_attribute(self, name: str):
        if not self._items:
            return None
        return self._items[0].attrs.get(name)

    def wait_for(self, **_kwargs):
        if not self._items:
            raise RuntimeError("No elements")
        return None


class FakePage:
    def __init__(self, elements: list[FakeElement]):
        self.elements = elements

    def wait_for_load_state(self, *_args, **_kwargs):
        return None

    def screenshot(self, path: str, **_kwargs):
        Path(path).write_bytes(b"")

    def content(self):
        return "<html></html>"

    def locator(self, selector: str):
        selector = selector or ""
        if selector.startswith("#"):
            dom_id = selector[1:]
            return FakeLocator([el for el in self.elements if el.attrs.get("id") == dom_id])
        if selector.startswith("[") and "]" in selector and "=" in selector:
            key = selector.split("[", 1)[1].split("=", 1)[0].strip()
            value = selector.split("=", 1)[1].strip().strip("]").strip('"')
            return FakeLocator([el for el in self.elements if el.attrs.get(key) == value])
        if "button" in selector or "role=\"button\"" in selector:
            return FakeLocator([el for el in self.elements if el.role == "button" or el.tag == "button"])
        if "a" in selector:
            return FakeLocator([el for el in self.elements if el.tag == "a"])
        if "textbox" in selector or "input" in selector or "textarea" in selector:
            return FakeLocator([el for el in self.elements if el.role == "textbox" or el.tag in ("input", "textarea")])
        if "combobox" in selector or "select" in selector:
            return FakeLocator([el for el in self.elements if el.role == "combobox" or el.tag == "select"])
        return FakeLocator([])

    def get_by_test_id(self, value):
        return FakeLocator([el for el in self.elements if el.attrs.get("data-testid") == value])

    def get_by_role(self, role, name=None):
        def _match(el: FakeElement):
            if el.role != role:
                return False
            if name is None:
                return True
            if isinstance(name, re.Pattern):
                return bool(name.search(el.text or el.label))
            return (el.text == name) or (el.label == name)

        return FakeLocator([el for el in self.elements if _match(el)])

    def get_by_label(self, value):
        return FakeLocator([el for el in self.elements if el.label == value or el.attrs.get("aria-label") == value])

    def get_by_placeholder(self, value):
        return FakeLocator([el for el in self.elements if el.placeholder == value])

    def get_by_text(self, value, exact: bool = False):
        if isinstance(value, re.Pattern):
            return FakeLocator([el for el in self.elements if value.search(el.text)])
        if exact:
            return FakeLocator([el for el in self.elements if el.text == value])
        return FakeLocator([el for el in self.elements if value in el.text])

    def get_by_display_value(self, value):
        return FakeLocator([el for el in self.elements if el.attrs.get("value") == value])


class NoPrimaryPage(FakePage):
    def get_by_test_id(self, value):
        return FakeLocator([])

    def get_by_role(self, role, name=None):
        return FakeLocator([])

    def get_by_label(self, value):
        return FakeLocator([])

    def get_by_placeholder(self, value):
        return FakeLocator([])

    def get_by_text(self, value, exact: bool = False):
        return FakeLocator([])

    def get_by_display_value(self, value):
        return FakeLocator([])


def _load_smart_ai(tmp_path: Path):
    lib_path = tmp_path / "generated_runs" / "src" / "lib"
    lib_path.mkdir(parents=True, exist_ok=True)
    smart_ai_path = lib_path / "smart_ai.py"
    namespace = {"__file__": str(smart_ai_path)}
    exec(smart_ai_utils.SMART_AI_CODE, namespace)
    return namespace


def test_similarity_heal_accepts(tmp_path):
    namespace = _load_smart_ai(tmp_path)
    SmartAISelfHealing = namespace["SmartAISelfHealing"]
    SmartAILocatorError = namespace["SmartAILocatorError"]

    metadata = [{"unique_name": "pay_button", "label_text": "Pay Now"}]
    healer = SmartAISelfHealing(metadata)
    page = NoPrimaryPage([FakeElement(text="Pay now", role="button", tag="button")])

    locator = healer.find_element("pay_button", page)
    assert locator._locator.inner_text() == "Pay now"


def test_similarity_rejects_low(tmp_path):
    namespace = _load_smart_ai(tmp_path)
    SmartAISelfHealing = namespace["SmartAISelfHealing"]
    SmartAILocatorError = namespace["SmartAILocatorError"]

    metadata = [{"unique_name": "transfer_button", "label_text": "Transfer"}]
    healer = SmartAISelfHealing(metadata)
    page = NoPrimaryPage([FakeElement(text="Settings", role="button", tag="button")])

    with pytest.raises(SmartAILocatorError):
        healer.find_element("transfer_button", page)


def test_similarity_ambiguity(tmp_path):
    namespace = _load_smart_ai(tmp_path)
    SmartAISelfHealing = namespace["SmartAISelfHealing"]
    SmartAILocatorError = namespace["SmartAILocatorError"]

    metadata = [{"unique_name": "pay_button", "label_text": "Pay Now"}]
    healer = SmartAISelfHealing(metadata)
    page = NoPrimaryPage(
        [
            FakeElement(text="Pay now", role="button", tag="button"),
            FakeElement(text="Pay now!", role="button", tag="button"),
        ]
    )

    with pytest.raises(SmartAILocatorError):
        healer.find_element("pay_button", page)


def test_persistence_reuse_and_isolation(tmp_path):
    namespace_a = _load_smart_ai(tmp_path / "project_a")
    SmartAISelfHealingA = namespace_a["SmartAISelfHealing"]

    metadata = [{"unique_name": "pay_button", "label_text": "Pay Now"}]
    healer_a = SmartAISelfHealingA(metadata)
    page_a = NoPrimaryPage([FakeElement(text="Pay now", role="button", tag="button")])
    healer_a.find_element("pay_button", page_a)

    cache_a = tmp_path / "project_a" / "data" / "logs" / "smartai_healed_locators.jsonl"
    assert cache_a.exists()

    namespace_b = _load_smart_ai(tmp_path / "project_b")
    SmartAISelfHealingB = namespace_b["SmartAISelfHealing"]
    SmartAILocatorErrorB = namespace_b["SmartAILocatorError"]

    healer_b = SmartAISelfHealingB([])

    class GuardedPage(FakePage):
        def get_by_text(self, *_args, **_kwargs):
            raise AssertionError("Cached locator should not be used across projects.")

    with pytest.raises(SmartAILocatorErrorB):
        healer_b.find_element("pay_button", GuardedPage([]))

    cache_b = tmp_path / "project_b" / "data" / "logs" / "smartai_healed_locators.jsonl"
    assert not cache_b.exists()


def test_runtime_rejects_generic_container_css_for_click_like_controls(tmp_path):
    namespace = _load_smart_ai(tmp_path)
    SmartAISelfHealing = namespace["SmartAISelfHealing"]

    healer = SmartAISelfHealing([])
    element = {
        "unique_name": "from_calendar_icon",
        "label_text": "From calendar icon",
        "ocr_type": "iconbutton",
        "intent": "from_calendar_icon_action",
        "css_selector": "div.muigrid-root",
    }

    assert healer._is_click_like_element(element) is True
    assert healer._is_generic_container_selector("div.muigrid-root") is True
    assert healer._should_reject_strategy(element, "locator(div.muigrid-root) [css_selector]") is True


def test_runtime_allows_specific_actionable_css_for_click_like_controls(tmp_path):
    namespace = _load_smart_ai(tmp_path)
    SmartAISelfHealing = namespace["SmartAISelfHealing"]

    healer = SmartAISelfHealing([])
    element = {
        "unique_name": "from_calendar_icon",
        "label_text": "From calendar icon",
        "ocr_type": "iconbutton",
        "intent": "from_calendar_icon_action",
        "css_selector": "button.calendar-trigger",
    }

    assert healer._is_click_like_element(element) is True
    assert healer._is_generic_container_selector("button.calendar-trigger") is False
    assert healer._should_reject_strategy(element, "locator(button.calendar-trigger) [css_selector]") is False
