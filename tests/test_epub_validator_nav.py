from pathlib import Path
import sys
from zipfile import ZIP_STORED, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reconstruction.epub_validator import validate_epub


def _write_epub(path, with_nav):
    manifest = '<item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>'
    if with_nav:
        manifest += '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    opf = (
        '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata/>'
        f"<manifest>{manifest}</manifest>"
        '<spine><itemref idref="ch1"/></spine></package>'
    )
    with ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        z.writestr(
            "META-INF/container.xml",
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
            '<rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>'
            "</container>",
        )
        z.writestr("content.opf", opf)
        z.writestr("ch1.xhtml", '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>x</p></body></html>')
        if with_nav:
            z.writestr(
                "nav.xhtml",
                '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
                '<body><nav epub:type="toc"><ol><li>a</li></ol></nav></body></html>',
            )


def test_epub3_without_nav_is_rejected(tmp_path):
    epub = tmp_path / "no_nav.epub"
    _write_epub(epub, with_nav=False)
    result = validate_epub(epub)
    assert not result.passed
    assert "NAV_EXISTS" in [issue.rule for issue in result.issues]


def test_epub3_with_nav_passes(tmp_path):
    epub = tmp_path / "with_nav.epub"
    _write_epub(epub, with_nav=True)
    result = validate_epub(epub)
    assert result.passed, [issue.message for issue in result.issues]
