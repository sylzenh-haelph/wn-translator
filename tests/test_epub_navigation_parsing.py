from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parsers.epub_parser import parse_epub


FIXTURE = ROOT / "test_navigation_fixture.epub"


def main():
    document = parse_epub(FIXTURE)
    epub = document.metadata["epub"]

    assert epub["spine_attributes"]["toc"] == "ncx"

    navigation_items = epub["navigation_items"]

    assert "nav" in navigation_items

    nav = navigation_items["nav"]

    assert nav["href"] == "nav.xhtml"
    assert nav["media_type"] == "application/xhtml+xml"
    assert "nav" in nav["properties"].split()

    print("PASS: EPUB navigation parsing")


if __name__ == "__main__":
    main()
