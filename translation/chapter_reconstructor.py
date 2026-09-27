from dataclasses import dataclass, field
from copy import deepcopy

from models.document import Paragraph, TextRun


@dataclass
class ReconstructedChapter:
    chapter_id: str
    title: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    heading: Paragraph | None = None


class ChapterReconstructor:
    """
    Reconstruct a translated chapter while preserving the source structure.

    Invariants:
    - paragraph count/order are preserved
    - paragraph IDs are preserved
    - paragraph style is preserved
    - run formatting is preserved as far as possible
    - heading is preserved
    """

    def reconstruct(
        self,
        chapter_id: str,
        title: str,
        source_paragraphs: list[Paragraph],
        translated_paragraphs: list[str],
        heading: Paragraph | None = None,
    ) -> ReconstructedChapter:
        if len(source_paragraphs) != len(translated_paragraphs):
            raise ValueError(
                "Jumlah paragraph sumber dan hasil terjemahan harus sama: "
                f"{len(source_paragraphs)} != {len(translated_paragraphs)}"
            )

        paragraphs = []

        for source, translated_text in zip(
            source_paragraphs,
            translated_paragraphs,
        ):
            paragraphs.append(
                self._reconstruct_paragraph(
                    source,
                    translated_text,
                )
            )

        preserved_heading = (
            deepcopy(heading)
            if heading is not None
            else None
        )

        return ReconstructedChapter(
            chapter_id=chapter_id,
            title=title,
            paragraphs=paragraphs,
            heading=preserved_heading,
        )

    def _reconstruct_paragraph(
        self,
        source: Paragraph,
        translated_text: str,
    ) -> Paragraph:
        result = Paragraph(
            id=source.id,
            runs=[],
            style=deepcopy(source.style),
        )

        if not source.runs:
            result.runs.append(
                TextRun(
                    text=translated_text,
                    formatting={},
                )
            )
            return result

        if len(source.runs) == 1:
            result.runs.append(
                TextRun(
                    text=translated_text,
                    formatting=deepcopy(
                        source.runs[0].formatting
                    ),
                )
            )
            return result

        result.runs = self._redistribute_text(
            source.runs,
            translated_text,
        )

        return result

    @staticmethod
    def _redistribute_text(
        source_runs: list[TextRun],
        translated_text: str,
    ) -> list[TextRun]:
        """
        Redistribute translated text over the original run boundaries.

        This is intentionally deterministic. It does not attempt semantic
        alignment between source and translated words. Instead, it preserves
        the original formatting regions approximately by character ratio.

        Empty source runs are retained with empty text so their formatting
        remains representable.
        """
        source_lengths = [
            len(run.text)
            for run in source_runs
        ]

        total_length = sum(source_lengths)

        if total_length == 0:
            return [
                TextRun(
                    text=translated_text,
                    formatting=deepcopy(source_runs[0].formatting),
                )
            ]

        translated_length = len(translated_text)

        if translated_length == 0:
            return [
                TextRun(
                    text="",
                    formatting=deepcopy(run.formatting),
                )
                for run in source_runs
            ]

        boundaries = []
        accumulated_source = 0

        for index, source_length in enumerate(source_lengths):
            accumulated_source += source_length

            if index == len(source_runs) - 1:
                boundary = translated_length
            else:
                boundary = round(
                    translated_length
                    * accumulated_source
                    / total_length
                )

            boundaries.append(boundary)

        result = []
        start = 0

        for index, run in enumerate(source_runs):
            end = boundaries[index]

            result.append(
                TextRun(
                    text=translated_text[start:end],
                    formatting=deepcopy(run.formatting),
                )
            )

            start = end

        return result
