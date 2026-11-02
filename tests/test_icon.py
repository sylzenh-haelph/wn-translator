from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_icon_is_svg_with_c_and_two_dots():
    assert server.ICON_SVG.startswith("<svg")
    assert "url(#g)" in server.ICON_SVG
    assert server.ICON_SVG.count("<circle") == 2


def test_manifest_points_to_icon():
    data = json.loads(server.MANIFEST)
    assert data["icons"][0]["src"] == "/icon.svg"
    assert data["start_url"] == "/"
