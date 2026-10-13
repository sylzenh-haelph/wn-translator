from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

import pytest

import research.runtime as runtime


class FakeProvider:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeEngine:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakePipeline:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeEntityDB:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeChapterEntityService:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def _patch_stack(monkeypatch):
    monkeypatch.setattr(runtime, "TavilyResearchProvider", FakeProvider)
    monkeypatch.setattr(runtime, "AdaptiveResearchEngine", FakeEngine)
    monkeypatch.setattr(runtime, "EntityResearchPipeline", FakePipeline)
    monkeypatch.setattr(runtime, "EntityDB", FakeEntityDB)
    monkeypatch.setattr(
        runtime, "ChapterEntityService", FakeChapterEntityService
    )


def test_research_runtime_uses_tavily(monkeypatch, tmp_path):
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    _patch_stack(monkeypatch)

    service = runtime.build_research_service(
        project_dir=tmp_path,
        client=object(),
        document_title="The Silver Gate",
        author="Elias North",
        research_timeout=7,
        research_max_retries=0,
        max_attempts=2,
    )

    pipeline = service.kwargs["entity_pipeline"]
    engine = pipeline.kwargs["research_engine"]
    provider = engine.kwargs["provider"]

    assert provider.kwargs["api_key"] == "test-key"
    assert provider.kwargs["timeout"] == 7
    assert provider.kwargs["max_retries"] == 0
    assert engine.kwargs["max_attempts"] == 2


def test_research_runtime_requires_tavily_key(monkeypatch, tmp_path):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    _patch_stack(monkeypatch)

    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        runtime.build_research_service(
            project_dir=tmp_path,
            client=object(),
        )
