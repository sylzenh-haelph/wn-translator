from dataclasses import dataclass, field
from copy import deepcopy

from models.document import Document, Paragraph


@dataclass
class AssembledDocument:
    title: str
    author: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class DocumentAssembler:
    """
    Menggabungkan hasil rekonstruksi setiap chapter menjadi satu Document.

    Invariant:
    - urutan chapter dipertahankan
    - heading chapter dipertahankan
    - urutan paragraph dipertahankan
    - paragraph ID tidak diubah
    - style dan formatting berasal dari hasil reconstruction
    """

    def assemble(
        self,
        source_document,
        chapter_results,
    ):
        if len(chapter_results) == 0:
            return AssembledDocument(
                title=source_document.title,
                author=source_document.author,
                paragraphs=[],
                metadata=deepcopy(source_document.metadata),
            )

        paragraphs = []
        seen_ids = set()

        for chapter_index, chapter in enumerate(chapter_results):
            heading = getattr(chapter, "heading", None)

            if heading is not None:
                self._append_paragraph(
                    paragraphs,
                    seen_ids,
                    heading,
                    f"chapter {chapter_index + 1} heading",
                )

            chapter_paragraphs = getattr(
                chapter,
                "paragraphs",
                None,
            )

            if chapter_paragraphs is None:
                raise ValueError(
                    f"Chapter {chapter_index + 1} tidak memiliki "
                    "'paragraphs'."
                )

            for paragraph in chapter_paragraphs:
                self._append_paragraph(
                    paragraphs,
                    seen_ids,
                    paragraph,
                    f"chapter {chapter_index + 1}",
                )

        return AssembledDocument(
            title=source_document.title,
            author=source_document.author,
            paragraphs=paragraphs,
            metadata=deepcopy(source_document.metadata),
        )

    @staticmethod
    def _append_paragraph(
        target,
        seen_ids,
        paragraph,
        location,
    ):
        if not isinstance(paragraph, Paragraph):
            raise TypeError(
                f"Item pada {location} bukan Paragraph."
            )

        if paragraph.id in seen_ids:
            raise ValueError(
                f"Duplicate paragraph ID ditemukan: "
                f"{paragraph.id}"
            )

        seen_ids.add(paragraph.id)
        target.append(deepcopy(paragraph))
