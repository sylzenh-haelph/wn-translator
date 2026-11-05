from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_retry_deletes_progress_without_backup(tmp_path):
    progress = tmp_path / "progress"
    progress.mkdir()
    for name in ("chapter_003.json", "chapter_003.json.bak", "chapter_004.json"):
        (progress / name).write_text("{}", encoding="utf-8")
    removed = server.retire_progress(tmp_path, {3})
    assert removed == 2
    assert not (progress / "chapter_003.json").exists()
    assert not (progress / "chapter_003.json.bak").exists()
    assert (progress / "chapter_004.json").exists()
    assert not (progress / "retired").exists()
