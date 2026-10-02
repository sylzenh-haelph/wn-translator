import re
from dataclasses import dataclass

from models.document import Paragraph


_CHAPTER_MARKER_RE = re.compile(
    r"^\s*(chapter|chap\.|prologue|epilogue|appendix|part)\b",
    re.IGNORECASE,
)


def _has_heading(paragraphs: list[Paragraph]) -> bool:
    return any(
        paragraph.style.get("heading_level") is not None
        for paragraph in paragraphs
    )


def _all_text(paragraphs: list[Paragraph]) -> str:
    return " ".join(
        paragraph.text.strip()
        for paragraph in paragraphs
        if paragraph.text.strip()
    )


def _is_title_like(paragraph: Paragraph) -> bool:
    text = paragraph.text.strip()

    if not text:
        return False

    if paragraph.style.get("heading_level") is not None:
        return False

    if not paragraph.runs:
        return False

    return all(
        run.formatting.get("bold") is True
        for run in paragraph.runs
    )


def _contains_chapter_marker(paragraphs: list[Paragraph]) -> bool:
    for paragraph in paragraphs:
        if _CHAPTER_MARKER_RE.search(paragraph.text.strip()):
            return True

    return False



@dataclass
class SpineClassificationResult:
    classification: str
    confidence: float
    reason: str = ""


def classify_spine_document(
    paragraphs: list[Paragraph],
) -> SpineClassificationResult:
    """
    Classify one EPUB spine document deterministically.

    Returns:
        front_matter: strong title/front-matter pattern.
        chapter: strong chapter signal.
        ambiguous: insufficient evidence; caller may use AI fallback.
    """
    if not paragraphs:
        return SpineClassificationResult(
            classification="ambiguous",
            confidence=0.0,
            reason="Spine document has no paragraphs.",
        )

    if is_likely_front_matter(paragraphs):
        return SpineClassificationResult(
            classification="front_matter",
            confidence=0.95,
            reason="Strong title-page/front-matter pattern.",
        )

    if _has_heading(paragraphs):
        return SpineClassificationResult(
            classification="chapter",
            confidence=0.95,
            reason="Contains a heading.",
        )

    if _contains_chapter_marker(paragraphs):
        return SpineClassificationResult(
            classification="chapter",
            confidence=0.95,
            reason="Contains an explicit chapter marker.",
        )

    if len(paragraphs) > 8:
        return SpineClassificationResult(
            classification="chapter",
            confidence=0.85,
            reason="Document contains substantial paragraph content.",
        )

    return SpineClassificationResult(
        classification="ambiguous",
        confidence=0.5,
        reason="No strong front-matter or chapter signal.",
    )


def is_likely_front_matter(paragraphs: list[Paragraph]) -> bool:
    """
    Conservative heuristic for spine documents that are likely
    front/title matter rather than a translatable chapter.

    Returns True only when the document has a strong title-page
    pattern and no obvious chapter marker.
    """
    if not paragraphs:
        return False

    if _has_heading(paragraphs):
        return False

    if _contains_chapter_marker(paragraphs):
        return False

    if len(paragraphs) > 8:
        return False

    nonempty = [
        paragraph
        for paragraph in paragraphs
        if paragraph.text.strip()
    ]

    if not nonempty:
        return False

    title_like_count = sum(
        _is_title_like(paragraph)
        for paragraph in nonempty
    )

    if title_like_count != len(nonempty):
        return False

    combined = _all_text(nonempty)

    # A title page should contain relatively little text.
    if len(combined) > 500:
        return False

    return True
