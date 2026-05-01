import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

import utils.file_utils as file_utils_module  # noqa: E402
from utils.file_utils import build_standard_metadata  # noqa: E402
from apis import generate_page_methods  # noqa: E402


def test_build_standard_metadata_adds_icon_context_fields():
    metadata = build_standard_metadata(
        {
            "label_text": "From calendar icon",
            "ocr_type": "iconbutton",
            "intent": "from_calendar_icon_action",
            "field_context_label": "From",
            "related_input_label": "From",
            "container_context": "leave-form",
            "aria_label": "Open calendar",
            "x": 120,
            "y": 48,
            "detected_confidence": 0.8,
            "dom_matched": True,
        },
        "leave_form",
    )
    assert metadata["icon_family"] == "calendar"
    assert metadata["field_context_label"] == "From"
    assert metadata["related_input_label"] == "From"
    assert metadata["container_context"] == "leave-form"
    assert metadata["dom_accessible_name"] == "Open calendar"
    assert metadata["position_context"] == "x120_y48"
    assert metadata["disambiguation_key"] == "from_calendar"
    assert metadata["icon_source"] == "ocr+dom"
    assert float(metadata["final_confidence"]) >= 0.8


def test_generate_page_methods_prefers_icon_context_label_when_present():
    code = generate_page_methods.build_method(
        {
            "label_text": "calendar icon",
            "ocr_type": "iconbutton",
            "intent": "calendar_icon_action",
            "field_context_label": "From",
            "related_input_label": "From",
            "icon_family": "calendar",
            "disambiguation_key": "from_calendar",
            "unique_name": "leave_form_calendar_icon_iconbutton_calendar_icon_action",
        },
        {},
    )
    assert "def click_from_calendar(page):" in code
    assert "_click_icon(page, 'From calendar'" in code


def test_build_standard_metadata_canonicalizes_placeholder_style_input_labels(monkeypatch):
    monkeypatch.setattr(file_utils_module, "assign_intent_semantic", lambda _label: "")
    metadata = build_standard_metadata(
        {
            "label_text": "Enter email",
            "placeholder": "Enter email",
            "ocr_type": "textbox",
            "intent": "",
        },
        "login",
    )
    assert metadata["label_text"] == "email"
    assert metadata["canonical_label_text"] == "email"
    assert metadata["raw_label_text"] == "Enter email"
    assert metadata["placeholder"] == "Enter email"
    assert metadata["intent"] == "email_field"


def test_generate_page_methods_prefers_canonical_input_label_over_placeholder_text():
    code = generate_page_methods.build_method(
        {
            "label_text": "Enter email",
            "canonical_label_text": "email",
            "placeholder": "Enter email",
            "ocr_type": "textbox",
            "intent": "email_field",
            "unique_name": "login_email_textbox_email_field",
        },
        {},
    )
    assert "def enter_email(page, value):" in code
    assert "_enter_value(page, 'email', value, placeholder='Enter email')" in code
