from __future__ import annotations

from pathlib import Path

from research.adaptive_research import AdaptiveResearchEngine
from research.chapter_entity_service import ChapterEntityService
from research.entity_db import EntityDB
from research.entity_pipeline import EntityResearchPipeline
from research.research_provider import DuckDuckGoResearchProvider


def build_research_service(
    project_dir,
    client,
    document_title="",
    author="",
    research_timeout=20,
    research_max_retries=1,
    max_attempts=4,
):
    """
    Membuat seluruh research stack production.

    Alur:
        DuckDuckGo
            ↓
        AdaptiveResearchEngine
            ↓
        EntityResearchPipeline
            ↓
        ChapterEntityService
    """

    project_dir = Path(project_dir)

    research_dir = project_dir / "research_data"
    research_dir.mkdir(parents=True, exist_ok=True)

    entity_db = EntityDB(
        path=research_dir / "entities.json"
    )

    provider = DuckDuckGoResearchProvider(
        timeout=research_timeout,
        max_retries=research_max_retries,
    )

    research_engine = AdaptiveResearchEngine(
        provider=provider,
        client=client,
        max_attempts=max_attempts,
    )

    pipeline = EntityResearchPipeline(
        db=entity_db,
        client=client,
        research_engine=research_engine,
    )

    service = ChapterEntityService(
        entity_pipeline=pipeline,
        document_title=document_title,
        author=author,
    )

    return service
