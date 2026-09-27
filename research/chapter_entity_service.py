from dataclasses import dataclass, field

from models.document import Document
from research.entity_pipeline import EntityResearchPipeline


@dataclass
class ChapterEntityResult:
    chapter_id: str
    entities: list = field(default_factory=list)


class ChapterEntityService:
    """
    Adapter antara chapter-level workflow dan
    EntityResearchPipeline.

    EntityResearchPipeline bekerja pada Document,
    sedangkan orchestrator bekerja pada chapter + paragraphs.
    """

    def __init__(
        self,
        entity_pipeline: EntityResearchPipeline,
        document_title: str = "",
        author: str = "",
    ):
        self.entity_pipeline = entity_pipeline
        self.document_title = document_title
        self.author = author

    def process_chapter(self, chapter_id, paragraphs):
        """
        Proses seluruh paragraph dalam satu chapter
        menggunakan EntityResearchPipeline asli.

        Paragraph structure tetap dipertahankan.
        """

        document = Document(
            title=self.document_title,
            author=self.author,
            paragraphs=list(paragraphs),
        )

        pipeline_result = self.entity_pipeline.process_document(
            document
        )

        return ChapterEntityResult(
            chapter_id=chapter_id,
            entities=pipeline_result.entities,
        )
