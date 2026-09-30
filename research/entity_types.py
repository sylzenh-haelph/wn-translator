from dataclasses import dataclass


@dataclass
class EntityCandidate:
    text: str
    entity_type: str
    source_paragraph_id: str
    reason: str
