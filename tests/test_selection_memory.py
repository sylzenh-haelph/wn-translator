from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_selection_round_trip(tmp_path):
    server.save_selection(tmp_path, {2, 5})
    assert server.load_selection(tmp_path) == {"chapter_002", "chapter_005"}
    server.save_selection(tmp_path, None)
    assert server.load_selection(tmp_path) == "all"
