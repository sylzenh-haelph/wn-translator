from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.entity_db import EntityDB


def test_batch_writes_once(tmp_path, monkeypatch):
    path = tmp_path / "e.json"
    db = EntityDB(path=path)
    writes = []
    original = db._save_data
    monkeypatch.setattr(db, "_save_data", lambda data: (writes.append(1), original(data)))
    with db.batch():
        db.add(entity_type="character", canonical_name="A")
        db.add(entity_type="character", canonical_name="B")
        db.add(entity_type="character", canonical_name="C")
    assert len(writes) == 1
    assert EntityDB(path=path).count() == 3


def test_without_batch_each_change_writes(tmp_path, monkeypatch):
    path = tmp_path / "e.json"
    db = EntityDB(path=path)
    writes = []
    original = db._save_data
    monkeypatch.setattr(db, "_save_data", lambda data: (writes.append(1), original(data)))
    db.add(entity_type="character", canonical_name="A")
    db.add(entity_type="character", canonical_name="B")
    assert len(writes) == 2
