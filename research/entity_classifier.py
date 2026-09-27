from dataclasses import dataclass


VALID_TYPES = {
    "character",
    "place",
    "organization",
    "item",
    "skill",
    "race",
    "title",
    "proper_noun",
    "unknown",
}


@dataclass
class EntityClassification:
    text: str
    entity_type: str
    confidence: float
    reason: str


def classify_candidate(candidate, paragraph_text):
    """
    Heuristik awal sebelum AI classifier.

    Tujuan tahap ini bukan menentukan kebenaran final,
    tetapi menangani kasus yang sudah cukup jelas.

    AI classifier akan menggantikan/meningkatkan tahap ini
    ketika model provider sudah terpasang.
    """

    text = candidate.text

    # Detector sudah mengenali pola title + name
    # sebagai character.
    if candidate.entity_type == "character":
        return EntityClassification(
            text=text,
            entity_type="character",
            confidence=0.95,
            reason="Detected as title + personal name.",
        )

    lower_text = text.casefold()
    lower_paragraph = paragraph_text.casefold()

    # Beberapa indikator sederhana dari konteks.
    place_words = {
        "palace",
        "castle",
        "kingdom",
        "city",
        "town",
        "village",
        "forest",
        "mountain",
        "river",
        "temple",
        "academy",
    }

    item_words = {
        "sword",
        "blade",
        "staff",
        "ring",
        "shield",
        "armor",
        "dagger",
        "bow",
    }

    skill_words = {
        "spell",
        "magic",
        "skill",
        "technique",
        "ability",
    }

    words = set(lower_text.split())

    if words & place_words:
        return EntityClassification(
            text=text,
            entity_type="place",
            confidence=0.80,
            reason="Name contains a common place indicator.",
        )

    if words & item_words:
        return EntityClassification(
            text=text,
            entity_type="item",
            confidence=0.80,
            reason="Name contains a common item indicator.",
        )

    if words & skill_words:
        return EntityClassification(
            text=text,
            entity_type="skill",
            confidence=0.75,
            reason="Name contains a common skill indicator.",
        )

    # Belum cukup bukti.
    return EntityClassification(
        text=text,
        entity_type="unknown",
        confidence=0.0,
        reason="Insufficient evidence from the current context.",
    )
