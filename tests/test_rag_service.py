from __future__ import annotations

import importlib
import os
import sys
import types


class _FakeEmbeddingModel:
    def encode(self, texts, convert_to_numpy=True):
        return [[0.1, 0.2, 0.3] for _ in texts]


class _FakeCollection:
    def query(self, **kwargs):
        return {"ids": [["chunk-1"]], "documents": [["Resume evidence"]], "metadatas": [[{"source_id": "source-1"}]], "distances": [[0.2]]}


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def get_or_create_collection(self, name):
        return _FakeCollection()


class _FakeSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texts, convert_to_numpy=True):
        return [[0.1, 0.2, 0.3] for _ in texts]


class _FakeLLMProvider:
    def __init__(self):
        self.backends = [types.SimpleNamespace(provider="openai", base_url="https://example.com", api_key="key")]

    def ask(self, *args, **kwargs):
        return "Generated draft"


def _load_rag_service(monkeypatch):
    fake_sentence_mod = types.ModuleType("sentence_transformers")
    fake_sentence_mod.SentenceTransformer = _FakeSentenceTransformer
    fake_chroma_mod = types.ModuleType("chromadb")
    fake_chroma_mod.PersistentClient = _FakeClient
    fake_llm_mod = types.ModuleType("core.llm_provider")
    fake_llm_mod.LLMProvider = _FakeLLMProvider
    fake_llm_mod.is_fallback_mode_enabled = lambda: True

    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_sentence_mod)
    monkeypatch.setitem(sys.modules, "chromadb", fake_chroma_mod)
    monkeypatch.setitem(sys.modules, "core.llm_provider", fake_llm_mod)

    module = importlib.import_module("core.rag_service")
    return importlib.reload(module)


def test_rag_helpers_format_and_save_cover_letter(tmp_path, monkeypatch):
    rag_service = _load_rag_service(monkeypatch)
    RetrievedChunk = rag_service.RetrievedChunk

    output_dir = tmp_path / "cover_letters"
    assert rag_service.ensure_output_dir(str(output_dir)) == str(output_dir)

    chunk = RetrievedChunk(id="1", text="Python and SQL", metadata={"source_id": "src-1"}, distance=0.25)
    cover_letter, source_ids, chunks = rag_service._fallback_cover_letter(
        "Build APIs",
        "Summary text",
        [chunk],
        company_name="Acme",
        role="Backend Engineer",
        tone="professional",
    )
    assert "Backend Engineer" in cover_letter
    assert source_ids == ["src-1"]
    assert chunks[0].text == "Python and SQL"

    result = rag_service.save_cover_letter_artifacts(
        7,
        cover_letter,
        source_ids,
        [chunk],
        output_dir=str(output_dir),
        metadata={"company": "Acme"},
    )
    assert os.path.exists(result["text_path"])
    assert os.path.exists(result["json_path"])


def test_rag_hybrid_and_prompt_helpers(monkeypatch):
    rag_service = _load_rag_service(monkeypatch)
    RetrievedChunk = rag_service.RetrievedChunk

    normalized = rag_service._normalize_scores([2.0, 4.0, 6.0])
    assert normalized[0] == 0.0
    assert normalized[-1] == 1.0

    prompt = rag_service.build_cover_letter_prompt(
        "Build APIs",
        "Resume summary",
        [RetrievedChunk(id="1", text="Python and SQL", metadata={"source_id": "src-1"})],
        company_name="Acme",
        role="Backend Engineer",
        tone="warm",
    )
    assert "Acme" in prompt
    assert "Backend Engineer" in prompt
