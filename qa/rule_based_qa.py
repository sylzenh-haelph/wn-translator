import re
from dataclasses import dataclass, field


@dataclass
class QAIssue:
    rule: str
    message: str
    severity: str = "error"


@dataclass
class QAResult:
    passed: bool
    issues: list[QAIssue] = field(default_factory=list)

    @property
    def errors(self):
        return [
            issue
            for issue in self.issues
            if issue.severity == "error"
        ]


def _paragraph_count(text):
    if not text:
        return 0

    return len(text.split("\n"))


def _normalize_entity(text):
    return " ".join(text.strip().split()).casefold()


def _check_translation_not_empty(
    source_text,
    translation,
    issues,
):
    if not translation or not translation.strip():
        issues.append(
            QAIssue(
                rule="translation_not_empty",
                message="Translation kosong.",
            )
        )


def _check_paragraph_count(
    source_text,
    translation,
    issues,
):
    source_count = _paragraph_count(source_text)
    translation_count = _paragraph_count(translation)

    if source_count != translation_count:
        issues.append(
            QAIssue(
                rule="paragraph_count",
                message=(
                    f"Jumlah paragraph berbeda: "
                    f"source={source_count}, "
                    f"translation={translation_count}."
                ),
            )
        )


def _check_empty_paragraphs(
    source_text,
    translation,
    issues,
):
    if not translation:
        return

    source_lines = (source_text or "").split("\n")
    translation_lines = translation.split("\n")

    for index, paragraph in enumerate(translation_lines):
        if paragraph.strip():
            continue

        source_blank = (
            index < len(source_lines)
            and not source_lines[index].strip()
        )
        if source_blank:
            continue

        issues.append(
            QAIssue(
                rule="empty_paragraph",
                message=(
                    f"Paragraph output ke-{index + 1} kosong."
                ),
            )
        )


def _check_preserved_entities(
    source_text,
    translation,
    preserved_entities,
    issues,
):
    if not preserved_entities:
        return

    source_lower = source_text.casefold()
    translation_lower = translation.casefold()

    for entity in preserved_entities:
        if isinstance(entity, dict):
            entity_text = entity.get("text", "")
        else:
            entity_text = str(entity)

        if not entity_text:
            continue

        normalized = _normalize_entity(entity_text)

        if normalized not in source_lower:
            continue

        if entity_text.casefold() not in translation_lower:
            issues.append(
                QAIssue(
                    rule="preserved_entity",
                    message=(
                        f"Entity yang harus dipertahankan "
                        f"tidak ditemukan di translation: "
                        f"{entity_text}"
                    ),
                )
            )


def _check_unexpected_output(
    translation,
    issues,
):
    if not translation:
        return

    forbidden_prefixes = (
        "Translation:",
        "Here is the translation:",
        "Here is your translation:",
        "Translator's note:",
        "Note:",
    )

    stripped = translation.strip()

    for prefix in forbidden_prefixes:
        if stripped.casefold().startswith(prefix.casefold()):
            issues.append(
                QAIssue(
                    rule="unexpected_model_text",
                    message=(
                        f"Output mengandung prefix tambahan: "
                        f"{prefix}"
                    ),
                )
            )


UNTRANSLATED_WORDS = {
    "the", "and", "you", "that", "this", "what", "is", "are", "was",
    "to", "of", "it", "my", "me", "your", "with", "for", "not", "but",
    "just", "so", "want", "how", "can", "be", "do", "i",
}


def _check_untranslated_english(translation, issues):
    if not translation:
        return

    for index, paragraph in enumerate(translation.split("\n")):
        words = re.findall(r"[A-Za-z']+", paragraph.lower())
        if len(words) < 4:
            continue

        english = sum(word in UNTRANSLATED_WORDS for word in words)
        if english / len(words) >= 0.25:
            issues.append(
                QAIssue(
                    rule="untranslated_english",
                    message=(
                        f"Paragraph output ke-{index + 1} "
                        f"masih berbahasa Inggris."
                    ),
                )
            )


def _check_source_echo(translation, issues):
    # shortcut: hanya pola panah "->" atau "→", echo tanpa panah belum tertangkap, naikkan jika muncul lagi
    for index, paragraph in enumerate(translation.split("\n")):
        if "->" in paragraph or "→" in paragraph:
            issues.append(
                QAIssue(
                    rule="source_echo",
                    message=(
                        f"Paragraph output ke-{index + 1} "
                        f"memuat teks sumber."
                    ),
                )
            )


def run_qa(
    source_text,
    translation,
    preserved_entities=None,
):
    issues = []

    _check_translation_not_empty(
        source_text,
        translation,
        issues,
    )

    _check_paragraph_count(
        source_text,
        translation,
        issues,
    )

    _check_empty_paragraphs(
        source_text,
        translation,
        issues,
    )

    _check_preserved_entities(
        source_text,
        translation,
        preserved_entities,
        issues,
    )

    _check_unexpected_output(
        translation,
        issues,
    )

    _check_untranslated_english(
        translation,
        issues,
    )

    _check_source_echo(
        translation,
        issues,
    )

    return QAResult(
        passed=len(issues) == 0,
        issues=issues,
    )
