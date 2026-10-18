from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import _slim_chapter_epub


def test_slim_chapter_epub_drops_unused_media_and_adds_nav(tmp_path):
    epub = tmp_path / "ch.epub"
    with ZipFile(epub, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<container><rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>')
        z.writestr(
            "OEBPS/content.opf",
            '<package><metadata><meta name="cover" content="img_unused"/></metadata><manifest>'
            '<item id="ch1" href="Text/ch1.xhtml" media-type="application/xhtml+xml"/>'
            '<item id="img_used" href="Images/used.jpg" media-type="image/jpeg"/>'
            '<item id="img_unused" href="Images/unused.jpg" media-type="image/jpeg"/>'
            '</manifest><spine><itemref idref="ch1"/></spine></package>',
        )
        z.writestr("OEBPS/Text/ch1.xhtml", '<html><body><img src="../Images/used.jpg"/></body></html>')
        z.writestr("OEBPS/Images/used.jpg", b"a")
        z.writestr("OEBPS/Images/unused.jpg", b"b")

    _slim_chapter_epub(epub, "Bab 1 (Judul)")

    with ZipFile(epub) as z:
        names = set(z.namelist())
        opf = z.read("OEBPS/content.opf").decode("utf-8")
        nav = z.read("OEBPS/chapter-nav.xhtml").decode("utf-8")
    assert "OEBPS/Images/used.jpg" in names
    assert "OEBPS/Images/unused.jpg" not in names
    assert "unused.jpg" not in opf
    assert 'name="cover"' not in opf
    assert 'properties="nav"' in opf
    assert 'href="Text/ch1.xhtml"' in nav
