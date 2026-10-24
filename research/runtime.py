from __future__ import annotations

import os
from pathlib import Path

from research.adaptive_research import AdaptiveResearchEngine
from research.chapter_entity_service import ChapterEntityService
from research.entity_db import EntityDB
from research.entity_pipeline import EntityResearchPipeline
from research.research_provider import TavilyResearchProvider


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
        Tavily
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

    series_path = os.environ.get("WN_SERIES_ENTITIES", "").strip()
    entity_path = Path(series_path) if series_path else research_dir / "entities.json"
    entity_path.parent.mkdir(parents=True, exist_ok=True)
    if series_path and not entity_path.exists() and (research_dir / "entities.json").exists():
        import shutil

        shutil.copy2(research_dir / "entities.json", entity_path)
    entity_db = EntityDB(
        path=entity_path
    )

    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY belum tersedia di environment. "
            "Set TAVILY_API_KEY, atau matikan research dengan "
            "WN_RESEARCH_ENABLED=0."
        )

    provider = TavilyResearchProvider(
        api_key=tavily_api_key,
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
