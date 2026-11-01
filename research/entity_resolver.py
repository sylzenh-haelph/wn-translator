from dataclasses import dataclass



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
