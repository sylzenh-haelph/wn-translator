from pathlib import Path
from zipfile import ZipFile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_repair import repair_epub, repair_text


def test_repair_text_closes_missing_quote():
    text, count = repair_text('<img src="../Images/a.jpg/>')
    assert text == '<img src="../Images/a.jpg"/>'
    assert count == 1


def test_valid_markup_is_untouched():
    text, count = repair_text('<img src="a.jpg"/>')
    assert text == '<img src="a.jpg"/>'
    assert count == 0


def test_repair_epub_writes_fixed_copy(tmp_path):
    src = tmp_path / "bad.epub"
    with ZipFile(src, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/Text/s.html", '<img src="../Images/a.jpg/>')
    dst = tmp_path / "out" / "bad.epub"
    assert repair_epub(src, dst) == 1
    with ZipFile(dst) as z:
        assert z.read("OEBPS/Text/s.html").decode("utf-8") == '<img src="../Images/a.jpg"/>'
    assert src.exists()
