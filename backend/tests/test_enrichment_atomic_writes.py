import asyncio
import json
from pathlib import Path

from apis import enrichment_api as enrichment


def test_atomic_write_uses_replace(tmp_path, monkeypatch):
    target = tmp_path / "after_enrichment.json"
    called = {"replace": False}

    original_replace = Path.replace

    def _replace(self, target_path):
        called["replace"] = True
        return original_replace(self, target_path)

    monkeypatch.setattr(Path, "replace", _replace)

    enrichment._atomic_write_project_file(
        target, json.dumps({"ok": True}), encoding="utf-8"
    )

    assert called["replace"] is True
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload == {"ok": True}


def test_concurrent_atomic_merge_writes(tmp_path):
    output = tmp_path / "page_enrichment.json"
    pid = 123
    page = "home"

    async def _write(label: str):
        records = [{"label_text": label, "text": label}]
        return await enrichment._atomic_merge_write_enrichment_page(
            project_id=pid,
            page_name=page,
            src_directory=tmp_path,
            output_path=output,
            new_records=records,
        )

    async def _run():
        return await asyncio.gather(_write("A"), _write("B"))

    asyncio.run(_run())

    payload = json.loads(output.read_text(encoding="utf-8"))
    labels = {item.get("label_text") for item in payload if isinstance(item, dict)}
    assert "A" in labels
    assert "B" in labels
