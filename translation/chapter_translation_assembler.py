from dataclasses import dataclass

from translation.chunker import Chunk


@dataclass
class AssembledParagraph:
    paragraph_id: str
    translated_text: str


class ChapterTranslationAssembler:
    """
    Assemble translated chunk results back into paragraph order.

    Invariants:
    - every source paragraph must appear exactly once
    - paragraph order follows the source chapter
    - no chunk boundary may alter paragraph order
    """

    def assemble(
        self,
        chunks: list[Chunk],
        processed_chunks: list,
        paragraph_ids: list[str],
    ) -> list[AssembledParagraph]:
        if len(chunks) != len(processed_chunks):
            raise ValueError(
                "Jumlah chunks dan processed_chunks harus sama: "
                f"{len(chunks)} != {len(processed_chunks)}"
            )

        expected_ids = list(paragraph_ids)
        translated_by_id: dict[str, str] = {}

        for chunk, processed in zip(chunks, processed_chunks):
            translation = self._get_translation(processed)

            chunk_ids = list(chunk.paragraph_ids)

            if len(chunk_ids) == 1:
                self._add_translation(
                    translated_by_id,
                    chunk_ids[0],
                    translation,
                )
                continue

            paragraph_translations = self._extract_paragraph_translations(
                processed,
                len(chunk_ids),
            )

            for paragraph_id, paragraph_text in zip(
                chunk_ids,
                paragraph_translations,
            ):
                self._add_translation(
                    translated_by_id,
                    paragraph_id,
                    paragraph_text,
                )

        actual_ids = list(translated_by_id)

        if set(actual_ids) != set(expected_ids):
            missing = [
                paragraph_id
                for paragraph_id in expected_ids
                if paragraph_id not in translated_by_id
            ]
            unexpected = [
                paragraph_id
                for paragraph_id in actual_ids
                if paragraph_id not in expected_ids
            ]

            raise ValueError(
                "Paragraph assembly tidak lengkap. "
                f"Missing={missing}, Unexpected={unexpected}"
            )

        return [
            AssembledParagraph(
                paragraph_id=paragraph_id,
                translated_text=translated_by_id[paragraph_id],
            )
            for paragraph_id in expected_ids
        ]

    @staticmethod
    def _get_translation(processed) -> str:
        if hasattr(processed, "translation"):
            return str(processed.translation)

        if isinstance(processed, dict):
            return str(processed.get("translation", ""))

        raise TypeError(
            "Processed chunk harus memiliki field 'translation'."
        )

    @classmethod
    def _extract_paragraph_translations(
        cls,
        processed,
        expected_count: int,
    ) -> list[str]:
        """
        Multi-paragraph chunks must provide paragraph-level translations.

        We intentionally do not split translated text heuristically because
        doing so could violate the immutable paragraph invariant.
        """
        if hasattr(processed, "paragraph_translations"):
            values = processed.paragraph_translations
        elif isinstance(processed, dict):
            values = processed.get("paragraph_translations")
        else:
            values = None

        if values is None:
            raise ValueError(
                "Chunk berisi lebih dari satu paragraph tetapi hasil model "
                "tidak menyediakan 'paragraph_translations'."
            )

        values = list(values)

        if len(values) != expected_count:
            raise ValueError(
                "Jumlah paragraph_translations tidak sesuai: "
                f"{len(values)} != {expected_count}"
            )

        return [str(value) for value in values]

    @staticmethod
    def _add_translation(
        target: dict[str, str],
        paragraph_id: str,
        translation: str,
    ):
        if paragraph_id in target:
            raise ValueError(
                f"Paragraph ID diterjemahkan lebih dari sekali: "
                f"{paragraph_id}"
            )

        target[paragraph_id] = translation
