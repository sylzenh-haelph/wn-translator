from dataclasses import dataclass

from research.entity_db import EntityDB
from research.entity_types import EntityCandidate


@dataclass
class ResolvedEntity:
    text: str
    entity_type: str
    source_paragraph_id: str
    status: str
    reason: str
    canonical_name: str | None = None
    translation: str | None = None
    locked: bool = False
    source: str | None = None


def resolve_candidate(candidate: EntityCandidate, db: EntityDB):
    """
    Hubungkan satu kandidat dari Entity Detector
    dengan Entity DB.

    status:
        known    -> ditemukan di DB
        unknown  -> belum ada di DB
    """

    record = db.get(candidate.text)

    if record is None:
        return ResolvedEntity(
            text=candidate.text,
            entity_type=candidate.entity_type,
            source_paragraph_id=candidate.source_paragraph_id,
            status="unknown",
            reason=candidate.reason,
        )

    return ResolvedEntity(
        text=candidate.text,
        entity_type=record["entity_type"],
        source_paragraph_id=candidate.source_paragraph_id,
        status="known",
        reason=candidate.reason,
        canonical_name=record["canonical_name"],
        translation=record["translation"],
        locked=record["locked"],
        source=record["source"],
    )


def resolve_entities(candidates, db: EntityDB):
    return [
        resolve_candidate(candidate, db)
        for candidate in candidates
    ]
