from dataclasses import dataclass, field

from models.document import Document, Paragraph


@dataclass
class DocumentChapter:
    chapter_id: str
    title: str
    paragraphs: list[Paragraph] = field(default_factory=list)
    heading: Paragraph | None = None
    translated_title: str | None = None

    @property
    def display_title(self) -> str:
        return self.translated_title or self.title


class DocumentChapterSplitter:
    """
    Split a parsed document into chapters.

    For EPUB documents, the EPUB spine is the authoritative
    chapter boundary. Headings inside a spine document are
    content unless they are the first heading representing
    the chapter title.

    Table-of-contents documents are excluded from chapter
    processing.

    For non-EPUB documents, fall back to heading-based splitting.
    """

    TOC_TITLES = {
        "contents",
        "table of contents",
        "toc",
        "daftar isi",
        "isi",
        "daftar kandungan",
    }

    def split(
        self,
        document: Document,
    ) -> list[DocumentChapter]:
        epub_structure = document.metadata.get("epub")

        if (
            epub_structure
            and epub_structure.get("spine")
        ):
            return self._split_epub(
                document,
                epub_structure,
            )

        return self._split_heading_based(document)

    @classmethod
    def _is_toc_document(
        cls,
        title: str,
        idref: str = "",
    ) -> bool:
        normalized_title = " ".join(
            title.strip().lower().split()
        )

        if normalized_title in cls.TOC_TITLES:
            return True

        normalized_idref = idref.strip().lower()

        toc_markers = (
            "toc",
            "contents",
            "tableofcontents",
            "daftarisi",
        )

        return any(
            marker in normalized_idref
            for marker in toc_markers
        )

    def _split_epub(
        self,
        document: Document,
        structure: dict,
    ) -> list[DocumentChapter]:
        spine = structure.get("spine", [])

        paragraph_spine_map = structure.get(
            "paragraph_spine_map",
            {},
        )

        if not paragraph_spine_map:
            return self._split_heading_based(
                document
            )

        paragraphs_by_spine: dict[
            str,
            list[Paragraph],
        ] = {
            idref: []
            for idref in spine
        }

        for paragraph in document.paragraphs:
            idref = paragraph_spine_map.get(
                paragraph.id
            )

            if idref in paragraphs_by_spine:
                paragraphs_by_spine[idref].append(
                    paragraph
                )

        chapters: list[DocumentChapter] = []

        for idref in spine:
            source_paragraphs = (
                paragraphs_by_spine.get(
                    idref,
                    [],
                )
            )

            if not source_paragraphs:
                continue

            heading = None
            title = ""

            # The first heading in the spine
            # document is treated as its title.
            for paragraph in source_paragraphs:
                if (
                    paragraph.style.get(
                        "heading_level"
                    )
                    is not None
                ):
                    heading = paragraph
                    title = paragraph.text.strip()
                    break

            if not title:
                title = (
                    document.title
                    or "Untitled Chapter"
                )

            # Exclude standalone TOC documents.
            if self._is_toc_document(
                title=title,
                idref=idref,
            ):
                continue

            chapter_paragraphs = [
                paragraph
                for paragraph in source_paragraphs
                if paragraph.id
                != (
                    heading.id
                    if heading
                    else None
                )
            ]

            chapter_number = len(chapters) + 1

            chapters.append(
                DocumentChapter(
                    chapter_id=(
                        f"chapter_{chapter_number:03d}"
                    ),
                    title=title,
                    paragraphs=chapter_paragraphs,
                    heading=heading,
                )
            )

        return chapters

    def _split_heading_based(
        self,
        document: Document,
    ) -> list[DocumentChapter]:
        chapters: list[DocumentChapter] = []

        current_paragraphs: list[Paragraph] = []
        current_title = ""
        current_heading: Paragraph | None = None

        chapter_number = 1

        for paragraph in document.paragraphs:
            heading_level = paragraph.style.get(
                "heading_level"
            )

            is_heading = heading_level is not None

            if is_heading:
                if current_paragraphs:
                    chapters.append(
                        DocumentChapter(
                            chapter_id=(
                                f"chapter_"
                                f"{chapter_number:03d}"
                            ),
                            title=current_title,
                            paragraphs=current_paragraphs,
                            heading=current_heading,
                        )
                    )

                    chapter_number += 1

                current_paragraphs = []
                current_title = paragraph.text.strip()
                current_heading = paragraph
                continue

            current_paragraphs.append(paragraph)

        if current_paragraphs:
            chapters.append(
                DocumentChapter(
                    chapter_id=(
                        f"chapter_"
                        f"{chapter_number:03d}"
                    ),
                    title=current_title,
                    paragraphs=current_paragraphs,
                    heading=current_heading,
                )
            )

        if (
            not chapters
            and document.paragraphs
        ):
            chapters.append(
                DocumentChapter(
                    chapter_id="chapter_001",
                    title=document.title,
                    paragraphs=list(
                        document.paragraphs
                    ),
                    heading=None,
                )
            )

        return chapters
