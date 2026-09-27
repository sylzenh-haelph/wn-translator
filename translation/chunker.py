from dataclasses import dataclass
import math


@dataclass
class Chunk:
    chunk_id: str
    paragraph_ids: list[str]
    text: str
    paragraph_texts: list[str]
    estimated_tokens: int


def estimate_tokens(text: str) -> int:
    """
    Lightweight conservative token estimate.

    Roughly estimates tokens using four characters per token.
    This is deterministic and does not require an external tokenizer.
    """
    if not text:
        return 0

    return max(1, math.ceil(len(text) / 4))


def _split_long_paragraph(text: str, max_tokens: int) -> list[str]:
    """
    Split a long paragraph into smaller word-based pieces.

    Word order is preserved.
    """
    words = text.split()

    if not words:
        return [""]

    pieces = []
    current = []

    for word in words:
        candidate = " ".join(current + [word])

        if current and estimate_tokens(candidate) > max_tokens:
            pieces.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

    if current:
        pieces.append(" ".join(current))

    return pieces


def build_chunks(
    paragraphs,
    max_tokens: int = 1200,
) -> list[Chunk]:
    """
    Build hybrid translation chunks.

    Rules:
    - Preserve paragraph order.
    - Never silently discard paragraphs.
    - Normal paragraphs may be grouped when they fit.
    - Long paragraphs use word-based fallback splitting.
    - Empty paragraphs are preserved as their own chunks.
    """
    chunks = []

    current_ids = []
    current_texts = []
    current_token_count = 0

    def flush_current():
        nonlocal current_ids
        nonlocal current_texts
        nonlocal current_token_count

        if not current_ids:
            return

        chunk_id = f"chunk_{len(chunks):04d}"

        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                paragraph_ids=list(current_ids),
                text="\n".join(current_texts),
                paragraph_texts=list(current_texts),
                estimated_tokens=current_token_count,
            )
        )

        current_ids = []
        current_texts = []
        current_token_count = 0

    for paragraph in paragraphs:
        paragraph_id = paragraph.id
        text = paragraph.text

        # Empty paragraphs must be preserved.
        if not text:
            flush_current()

            chunk_id = f"chunk_{len(chunks):04d}"

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    paragraph_ids=[paragraph_id],
                    text="",
                    paragraph_texts=[""],
                    estimated_tokens=0,
                )
            )

            continue

        paragraph_tokens = estimate_tokens(text)

        # Long paragraph fallback.
        if paragraph_tokens > max_tokens:
            flush_current()

            pieces = _split_long_paragraph(
                text,
                max_tokens,
            )

            for piece in pieces:
                chunk_id = f"chunk_{len(chunks):04d}"

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        paragraph_ids=[paragraph_id],
                        text=piece,
                        paragraph_texts=[piece],
                        estimated_tokens=estimate_tokens(piece),
                    )
                )

            continue

        # Check whether the paragraph fits into the current chunk.
        if not current_texts:
            proposed_text = text
        else:
            proposed_text = "\n".join(
                current_texts + [text]
            )

        proposed_tokens = estimate_tokens(proposed_text)

        if current_texts and proposed_tokens > max_tokens:
            flush_current()

        current_ids.append(paragraph_id)
        current_texts.append(text)

        current_token_count = estimate_tokens(
            "\n".join(current_texts)
        )

    flush_current()

    return chunks
