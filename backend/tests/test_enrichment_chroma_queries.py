import asyncio

from apis import enrichment_api as enrichment


class _FakeCollection:
    def __init__(self):
        self.where_calls = []
        self.full_calls = 0

    def get(self, **kwargs):
        if "where" in kwargs:
            self.where_calls.append(kwargs["where"])
            return {
                "metadatas": [
                    {
                        "project_id": 1,
                        "page_name": "home",
                        "type": "ocr",
                        "source_url": "https://example.com/home",
                    }
                ]
            }
        self.full_calls += 1
        raise AssertionError("Unexpected full collection.get() call")


def test_candidate_urls_uses_filtered_get(monkeypatch):
    collection = _FakeCollection()

    monkeypatch.setattr(enrichment, "_get_chroma_collection", lambda _p: collection)
    monkeypatch.setattr(enrichment, "get_request_project_id", lambda: 1)
    monkeypatch.setattr(enrichment, "filter_metadata_by_project", lambda metas: metas)

    async def _run():
        return await enrichment._candidate_urls_for_page("home", object())

    urls = asyncio.run(_run())
    assert any("project_id" in w for w in collection.where_calls)
    assert collection.full_calls == 0
    assert "https://example.com/home" in urls


def test_get_ocr_data_uses_filtered_get(monkeypatch):
    collection = _FakeCollection()

    monkeypatch.setattr(enrichment, "_get_chroma_collection", lambda _p: collection)
    monkeypatch.setattr(enrichment, "get_request_project_id", lambda: 1)
    monkeypatch.setattr(enrichment, "filter_metadata_by_project", lambda metas: metas)

    async def _run():
        return await enrichment._get_ocr_data_by_canonical("home", object())

    records = asyncio.run(_run())
    assert any("project_id" in w for w in collection.where_calls)
    assert collection.full_calls == 0
    assert records
