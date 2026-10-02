from __future__ import annotations

from dataclasses import dataclass

from translation.model_client import extract_json


VALID_CLASSIFICATIONS = {
    "front_matter",
    "chapter",
    "ambiguous",
}


@dataclass
class AISpineClassificationResult:
    classification: str
    confidence: float
    reason: str = ""


def _normalize_result(data) -> AISpineClassificationResult:
    if not isinstance(data, dict):
        raise RuntimeError(
            "Output spine classifier bukan object JSON."
        )

    classification = data.get(
        "classification",
        "ambiguous",
    )

    if classification not in VALID_CLASSIFICATIONS:
        raise RuntimeError(
            "Classification spine classifier tidak valid."
        )

    try:
        confidence = float(
            data.get("confidence", 0.0)
        )
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    reason = data.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)

    return AISpineClassificationResult(
        classification=classification,
        confidence=confidence,
        reason=reason.strip(),
    )


def _build_prompt(
    paragraphs,
    document_id="",
    novel_title="",
    author="",
):
    formatted_paragraphs = []

    for paragraph in paragraphs:
        paragraph_id = getattr(
            paragraph,
            "id",
            "",
        )

        text = getattr(
            paragraph,
            "text",
            "",
        )

        if not isinstance(paragraph_id, str):
            paragraph_id = str(paragraph_id)

        if not isinstance(text, str):
            continue

        text = text.strip()

        if not text:
            continue

        heading_level = getattr(
            paragraph,
            "style",
            {},
        ).get("heading_level")

        heading_marker = (
            f"heading_level={heading_level}"
            if heading_level is not None
            else "body"
        )

        formatted_paragraphs.append(
            f"[{paragraph_id}] ({heading_marker}) {text}"
        )

    source_text = "\n".join(
        formatted_paragraphs
    )

    return f"""
You are classifying ONE EPUB spine document.

Your task is to determine whether this spine document is:
- front_matter: title page, cover-like text, metadata, dedication,
  publication information, or other non-story front matter
- chapter: actual story/chapter content intended for translation
- ambiguous: insufficient evidence to confidently classify it

Use the paragraph structure, headings, amount of content, and textual
content as evidence.

Do not classify a document as front_matter merely because it is short.
A short genuine chapter can be a chapter.

Novel title: {novel_title}
Author: {author}
Spine document id: {document_id}

SOURCE PARAGRAPHS:

{source_text}

Return ONLY valid JSON in exactly this structure:

{{
  "classification": "chapter",
  "confidence": 0.95,
  "reason": "brief contextual reason"
}}

The classification MUST be exactly one of:
"front_matter", "chapter", "ambiguous".

Confidence MUST be a number from 0.0 to 1.0.
""".strip()


def classify_spine_document_with_ai(
    client,
    paragraphs,
    document_id="",
    novel_title="",
    author="",
):
    """
    Classify one EPUB spine document using one AI request.
    """

    if not paragraphs:
        return AISpineClassificationResult(
            classification="ambiguous",
            confidence=0.0,
            reason="Spine document has no paragraphs.",
        )

    prompt = _build_prompt(
        paragraphs=paragraphs,
        document_id=document_id,
        novel_title=novel_title,
        author=author,
    )

    raw = client.generate(prompt)
    data = extract_json(raw)

    return _normalize_result(data)
