from support_agent.rag import index, retrieve


def test_chunk_overlap():
    words = [f"word{i}" for i in range(465)]
    chunks = [chunk.split() for chunk in index.chunk_text(" ".join(words))]
    assert chunks == [words[:250], words[210:460], words[420:]]


def test_product_scope_ranking_and_cache(monkeypatch):
    documents = (
        ("tv-55-oled-manual.md", "The OLED TV has a 4K display."),
        ("soundbar-200-manual.md", "The soundbar supports optical audio."),
        ("warranty-policy.md", "The warranty lasts twelve months."),
    )
    calls = []

    def fake_embed(texts):
        calls.append(texts)
        return [(0.0, 1.0) if "warranty" in text else (1.0, 0.0) for text in texts]

    monkeypatch.setattr("support_agent.rag.interface.llm_enabled", lambda: True)
    monkeypatch.setattr("support_agent.rag.interface.load_documents", lambda: documents)
    monkeypatch.setattr(index, "embed", fake_embed)
    index.VectorIndex.for_documents.cache_clear()
    try:
        results = retrieve("What resolution is the display?", "tv-55-oled")
        assert [(item.source, item.score) for item in results] == [
            ("tv-55-oled-manual.md", 1.0),
            ("warranty-policy.md", 0.0),
        ]
        assert retrieve("What is the warranty?", "tv-55-oled", k=1)[0].source == "warranty-policy.md"
        assert [len(batch) for batch in calls] == [3, 1, 1]
    finally:
        index.VectorIndex.for_documents.cache_clear()


def test_offline_retrieval_returns_empty(monkeypatch):
    monkeypatch.setenv("SUPPORT_AGENT_OFFLINE", "1")
    assert retrieve("What resolution is the display?", "tv-55-oled") == []
