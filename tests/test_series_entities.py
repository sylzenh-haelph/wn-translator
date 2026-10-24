from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server
from research.entity_db import EntityDB
from research.runtime import build_research_service


def test_build_command_points_to_series_entities():
    cmd = server.build_command(Path("input/novel.epub"), None, "epub", "mt_v15.txt", "translate", "20260101_0000")
    assert "WN_SERIES_ENTITIES=glossary/.entities/mt_v15.json" in cmd


def test_series_entities_seeded_from_project(tmp_path, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "dummy")
    project_db = tmp_path / "proj" / "research_data" / "entities.json"
    EntityDB(path=project_db)
    series = tmp_path / "glossary" / ".entities" / "mt.json"
    monkeypatch.setenv("WN_SERIES_ENTITIES", str(series))

    build_research_service(project_dir=tmp_path / "proj", client=None)

    assert series.exists()
    assert series.read_bytes() == project_db.read_bytes()


def test_existing_series_is_not_overwritten(tmp_path, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "dummy")
    EntityDB(path=tmp_path / "proj" / "research_data" / "entities.json")
    series = tmp_path / "series.json"
    EntityDB(path=series)
    before = series.read_bytes()
    monkeypatch.setenv("WN_SERIES_ENTITIES", str(series))

    build_research_service(project_dir=tmp_path / "proj", client=None)

    assert series.read_bytes() == before
