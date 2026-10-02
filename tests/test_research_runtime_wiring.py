from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from pathlib import Path

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


def test_research_runtime_wiring(monkeypatch):
    monkeypatch.setattr(
        runtime,
        "DuckDuckGoResearchProvider",
        FakeProvider,
    )
    monkeypatch.setattr(
        runtime,
        "AdaptiveResearchEngine",
        FakeEngine,
    )
    monkeypatch.setattr(
        runtime,
        "EntityResearchPipeline",
        FakePipeline,
    )
    monkeypatch.setattr(
        runtime,
        "EntityDB",
        FakeEntityDB,
    )
    monkeypatch.setattr(
        runtime,
        "ChapterEntityService",
        FakeChapterEntityService,
    )

    service = runtime.build_research_service(
        project_dir=Path("test_research_runtime_project"),
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

    assert provider.kwargs["timeout"] == 7
    assert provider.kwargs["max_retries"] == 0
    assert engine.kwargs["max_attempts"] == 2
