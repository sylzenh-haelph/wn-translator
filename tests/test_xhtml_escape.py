from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Paragraph, TextRun
from reconstruction.epub_reconstructor import _build_xhtml


def test_ampersand_and_angle_brackets_are_escaped():
    paragraph = Paragraph(id="p1", runs=[TextRun(text="Subaru & Al: [x] <y>")], style={})
    html = _build_xhtml([paragraph])
    root = ET.fromstring(html.encode("utf-8"))
    assert "Subaru & Al: [x] <y>" in "".join(root.itertext())
