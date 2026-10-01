from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from models.document import Document, Paragraph, TextRun
from main import _safe_chapter_filename, _build_chapter_document


def test_safe_chapter_filename():
    chapter = SimpleNamespace(
        translated_title="Chapter 1: The Gate (Gerbang)"
    )

    name = _safe_chapter_filename(chapter, 1, ".epub")

    assert name == "chapter-01-The Gate (Gerbang).epub"


def test_safe_chapter_filename_falls_back_to_original_title():
    chapter = SimpleNamespace(
        translated_title=None,
        title="Chapter 2: The Ruins"
    )

    name = _safe_chapter_filename(chapter, 2, ".epub")

    assert name == "chapter-02-The Ruins.epub"


def test_build_chapter_document():
    heading = Paragraph(
        id="heading-1",
        runs=[
            TextRun(
                text="Chapter 1: The Gate (Gerbang)",
                formatting={"bold": True},
            )
        ],
        style={"heading_level": 1},
    )

    body = Paragraph(
        id="p1",
        runs=[TextRun(text="The gate stood before them.")],
    )

    chapter = SimpleNamespace(
        chapter_id="chapter-1",
        title="Chapter 1: The Gate",
        translated_title="Chapter 1: The Gate (Gerbang)",
        heading=heading,
        paragraphs=[body],
    )

    source_document = Document(
        title="Test Novel",
        author="Test Author",
        paragraphs=[heading, body],
        metadata={
            "epub": {
                "manifest": {
                    "chapter1": {
                        "href": "Text/chapter1.xhtml",
                        "media_type": "application/xhtml+xml",
                    },
                    "chapter2": {
                        "href": "Text/chapter2.xhtml",
                        "media_type": "application/xhtml+xml",
                    },
                },
                "spine": ["chapter1", "chapter2"],
                "paragraph_spine_map": {
                    "heading-1": "chapter1",
                    "p1": "chapter1",
                    "other": "chapter2",
                },
                "xhtml_sources": {
                    "chapter1": "Text/chapter1.xhtml",
                    "chapter2": "Text/chapter2.xhtml",
                },
                "spine_stylesheets": {
                    "chapter1": ["Styles/style.css"],
                    "chapter2": ["Styles/style.css"],
                },
                "navigation_items": [
                    {"idref": "chapter1", "title": "Chapter 1: The Gate"},
                    {"idref": "chapter2", "title": "Chapter 2: The Ruins"},
                ],
                "spine_attributes": {
                    "toc": "ncx",
                },
            }
        },
    )

    result = _build_chapter_document(source_document, chapter)

    assert result.title == "Test Novel"
    assert result.author == "Test Author"

    assert [p.id for p in result.paragraphs] == [
        "heading-1",
        "p1",
    ]

    assert result.metadata["epub"]["spine"] == ["chapter1"]

    assert result.metadata["epub"]["paragraph_spine_map"] == {
        "heading-1": "chapter1",
        "p1": "chapter1",
    }

    assert result.metadata["epub"]["xhtml_sources"] == {
        "chapter1": "Text/chapter1.xhtml",
    }

    assert result.metadata["epub"]["spine_stylesheets"] == {
        "chapter1": ["Styles/style.css"],
    }

    assert "navigation_items" not in result.metadata["epub"]

    assert "toc" not in result.metadata["epub"]["spine_attributes"]

    assert result.metadata["epub"]["manifest"] == {
        "chapter1": {
            "href": "Text/chapter1.xhtml",
            "media_type": "application/xhtml+xml",
        },
    }


if __name__ == "__main__":
    test_safe_chapter_filename()
    test_safe_chapter_filename_falls_back_to_original_title()
    test_build_chapter_document()
    print("CHAPTER EXPORT UNIT TESTS: PASS")
