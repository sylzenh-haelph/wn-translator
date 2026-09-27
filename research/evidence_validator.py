from dataclasses import dataclass
from urllib.parse import urlparse
import re


@dataclass
class EvidenceValidation:
    valid: bool
    score: float
    reason: str


class EvidenceValidator:
    """
    Deterministic validator for research evidence.

    Tujuan:
    - memastikan evidence benar-benar menyebut entity yang diteliti;
    - memastikan evidence memiliki sumber yang dapat diidentifikasi;
    - mencegah evidence untuk entity A tersimpan sebagai evidence entity B.

    Validator ini bukan pengganti AI evaluator.
    AI tetap menentukan apakah informasi tersebut substantively relevan.
    Validator ini hanya menjadi safety gate sebelum evidence disimpan.
    """

    MIN_SCORE = 0.5

    def validate(
        self,
        entity_text: str,
        entity_type: str,
        evidence,
        query: str = "",
    ) -> EvidenceValidation:
        if not entity_text or not str(entity_text).strip():
            return EvidenceValidation(
                valid=False,
                score=0.0,
                reason="Entity text is empty.",
            )

        if evidence is None:
            return EvidenceValidation(
                valid=False,
                score=0.0,
                reason="Evidence is missing.",
            )

        title = str(getattr(evidence, "title", "") or "")
        snippet = str(getattr(evidence, "snippet", "") or "")
        url = str(getattr(evidence, "url", "") or "")
        source = str(getattr(evidence, "source", "") or "")

        combined = f"{title} {snippet}".casefold()
        entity = str(entity_text).strip().casefold()

        score = 0.0
        reasons = []

        # Exact entity mention is the strongest deterministic signal.
        if entity in combined:
            score += 0.7
            reasons.append("Entity appears in title or snippet.")
        else:
            # For multi-word names, allow all meaningful words to appear.
            words = [
                word
                for word in re.findall(r"[a-zA-Z0-9]+", entity)
                if len(word) > 2
            ]

            if words and all(word in combined for word in words):
                score += 0.5
                reasons.append("All meaningful entity words appear in evidence.")

        # A usable HTTP(S) URL is required for externally sourced evidence.
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            score += 0.2
            reasons.append("Evidence has a valid HTTP(S) URL.")

        # Snippet should contain actual information, not just a title.
        if snippet.strip():
            score += 0.1
            reasons.append("Evidence contains a snippet.")

        # Source label is useful for traceability.
        if source.strip():
            score += 0.05
            reasons.append("Evidence source is identified.")

        # Query alignment is a weak additional signal.
        if query:
            query_entity = str(entity_text).casefold()
            if query_entity in str(query).casefold():
                score += 0.05
                reasons.append("Research query contains the entity.")

        score = min(1.0, score)
        valid = score >= self.MIN_SCORE

        if valid:
            reason = " ".join(reasons)
        else:
            reason = (
                "Evidence failed deterministic relevance validation. "
                + (" ".join(reasons) if reasons else "No relevant evidence signals found.")
            )

        return EvidenceValidation(
            valid=valid,
            score=score,
            reason=reason,
        )
