import sys
from pathlib import Path
from PIL import Image

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from logic.image_text_extractor import _append_clean_lines, _iter_focus_regions, _normalize_icon_like_label  # noqa: E402


def test_normalize_icon_like_label_maps_launcher_variants_to_app_launcher():
    label, ocr_type = _normalize_icon_like_label("9 dot menu", "image")
    assert label == "app launcher"
    assert ocr_type == "iconbutton"


def test_normalize_icon_like_label_preserves_profile_icon_behavior():
    label, ocr_type = _normalize_icon_like_label("user avatar", "label")
    assert label == "profile icon"
    assert ocr_type == "iconbutton"


def test_append_clean_lines_dedupes_case_insensitive_lines():
    target = []
    seen = set()

    _append_clean_lines(target, seen, ["Mail icon - iconbutton - mail_icon_action"])
    _append_clean_lines(target, seen, ["mail icon - iconbutton - mail_icon_action", "315 - label - notification_count_label"])

    assert target == [
        "Mail icon - iconbutton - mail_icon_action",
        "315 - label - notification_count_label",
    ]


def test_iter_focus_regions_returns_expected_named_crops():
    image = Image.new("RGB", (1920, 900), "white")

    regions = _iter_focus_regions(image)

    assert [name for name, _ in regions] == [
        "top_header",
        "left_sidebar",
        "right_rail",
        "top_right_cluster",
    ]
    assert all(region.size[0] > 0 and region.size[1] > 0 for _, region in regions)
