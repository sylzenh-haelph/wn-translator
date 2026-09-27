from dataclasses import dataclass, field
from typing import Any


PRIORITY_ORDER = (
    "user_lock",
    "user_rule",
    "character_db",
    "glossary",
    "research",
    "ai_context",
)


@dataclass
class Resolution:
    entity_text: str
    value: Any
    source: str
    priority: int
    locked: bool = False
    reason: str = ""
    alternatives: list[dict] = field(
        default_factory=list
    )


class PriorityResolver:
    """
    Menentukan nilai entity berdasarkan prioritas:

        User Lock
        > User Rule
        > Character DB
        > Glossary
        > Research
        > AI Context
    """

    def __init__(self):
        self._priority = {
            source: index
            for index, source
            in enumerate(PRIORITY_ORDER)
        }

    def _valid_candidate(self, candidate):
        if candidate is None:
            return False

        if isinstance(candidate, dict):
            return candidate.get("value") is not None

        return True

    def _normalize_candidate(
        self,
        source,
        candidate,
    ):
        if isinstance(candidate, dict):
            value = candidate.get("value")

            locked = bool(
                candidate.get("locked", False)
            )

            reason = candidate.get(
                "reason",
                "",
            )

        else:
            value = candidate
            locked = False
            reason = ""

        return {
            "source": source,
            "value": value,
            "locked": locked,
            "reason": reason,
            "priority": self._priority[source],
        }

    def resolve(
        self,
        entity_text,
        *,
        user_lock=None,
        user_rule=None,
        character_db=None,
        glossary=None,
        research=None,
        ai_context=None,
    ):
        candidates = {
            "user_lock": user_lock,
            "user_rule": user_rule,
            "character_db": character_db,
            "glossary": glossary,
            "research": research,
            "ai_context": ai_context,
        }

        normalized = []

        for source in PRIORITY_ORDER:
            candidate = candidates[source]

            if not self._valid_candidate(candidate):
                continue

            normalized.append(
                self._normalize_candidate(
                    source,
                    candidate,
                )
            )

        if not normalized:
            return Resolution(
                entity_text=entity_text,
                value=None,
                source="none",
                priority=-1,
                locked=False,
                reason="No usable resolution source.",
            )

        # Karena PRIORITY_ORDER sudah dari
        # tertinggi ke terendah, kandidat pertama
        # adalah pemenang.
        winner = normalized[0]

        alternatives = [
            {
                "source": candidate["source"],
                "value": candidate["value"],
                "priority": candidate["priority"],
            }
            for candidate in normalized[1:]
        ]

        return Resolution(
            entity_text=entity_text,
            value=winner["value"],
            source=winner["source"],
            priority=winner["priority"],
            locked=winner["locked"],
            reason=winner["reason"],
            alternatives=alternatives,
        )

    def resolve_from_sources(
        self,
        entity_text,
        sources,
    ):
        """
        Versi praktis jika sumber sudah tersedia
        sebagai dictionary.

        Contoh:

        {
            "user_lock": {...},
            "user_rule": {...},
            "research": {...}
        }
        """

        return self.resolve(
            entity_text,
            user_lock=sources.get(
                "user_lock"
            ),
            user_rule=sources.get(
                "user_rule"
            ),
            character_db=sources.get(
                "character_db"
            ),
            glossary=sources.get(
                "glossary"
            ),
            research=sources.get(
                "research"
            ),
            ai_context=sources.get(
                "ai_context"
            ),
        )
