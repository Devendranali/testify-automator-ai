import asyncio
import os
from pathlib import Path

from apis import enrichment_api as enrichment


def test_debug_snapshots_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("SMARTAI_ENRICH_DEBUG", raising=False)

    debug_dir = tmp_path / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)

    def _fake_dirs(_src=None):
        return {"debug": debug_dir, "meta": tmp_path}

    monkeypatch.setattr(enrichment, "_ensure_dirs", _fake_dirs)
    monkeypatch.setattr(enrichment, "_safe_log", lambda *a, **k: None)

    class DummyPage:
        async def evaluate(self, _js):
            return True

        async def screenshot(self, path: str, full_page: bool = True):
            Path(path).write_text("x", encoding="utf-8")

    asyncio.run(enrichment.__snapshot_if_blank(DummyPage(), "blank"))
    assert not any(debug_dir.glob("blank_*.png"))
