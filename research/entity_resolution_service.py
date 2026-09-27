from dataclasses import dataclass

from research.entity_db import EntityDB
from research.priority_resolver import PriorityResolver
from storage.glossary_db import GlossaryDB
from storage.user_rule_db import UserRuleDB


@dataclass
class EntityResolutionResult:
    entity_text: str
    entity_type: str
    translation: str | None
    source: str
    priority: int
    locked: bool
    reason: str
    alternatives: list


class EntityResolutionService:
    def __init__(
        self,
        entity_db: EntityDB,
        glossary_db: GlossaryDB | None = None,
        user_rule_db: UserRuleDB | None = None,
        resolver: PriorityResolver | None = None,
    ):
        self.entity_db = entity_db
        self.glossary_db = glossary_db
        self.user_rule_db = user_rule_db
        self.resolver = resolver or PriorityResolver()

    def _get_entity_record(self, entity_text):
        return self.entity_db.get(entity_text)

    def _get_glossary_record(self, entity_text):
        if self.glossary_db is None:
            return None

        return self.glossary_db.resolve(entity_text)

    def _get_user_rules(self, entity_text):
        if self.user_rule_db is None:
            return []

        return self.user_rule_db.find_by_target(
            entity_text
        )

    def _build_sources(
        self,
        entity_text,
        entity_record,
        glossary_record,
        user_rules,
        research_translation=None,
        ai_context=None,
    ):
        user_lock = None
        user_rule = None
        character_db = None
        glossary = None
        research = None

        # --------------------------------------------------
        # ENTITY DB
        # --------------------------------------------------
        if entity_record is not None:
            translation = entity_record.get(
                "translation"
            )

            if translation:
                if entity_record.get("locked"):
                    user_lock = translation

                elif (
                    entity_record.get("entity_type")
                    == "character"
                ):
                    character_db = translation

        # --------------------------------------------------
        # USER RULES
        # --------------------------------------------------
        unlocked_rules = []

        for rule in user_rules:
            value = rule.get("value")

            if not value:
                continue

            if rule.get("locked"):
                if user_lock is None:
                    user_lock = value
            else:
                unlocked_rules.append(value)

        if unlocked_rules:
            user_rule = unlocked_rules[0]

        # --------------------------------------------------
        # GLOSSARY
        # --------------------------------------------------
        if glossary_record is not None:
            translation = glossary_record.get(
                "translation"
            )

            if translation:
                glossary = translation

        # --------------------------------------------------
        # RESEARCH
        # --------------------------------------------------
        if research_translation:
            research = research_translation

        # --------------------------------------------------
        # AI CONTEXT
        # --------------------------------------------------
        ai_value = None

        if ai_context:
            if isinstance(ai_context, dict):
                ai_value = ai_context.get(
                    entity_text
                )

        return {
            "user_lock": user_lock,
            "user_rule": user_rule,
            "character_db": character_db,
            "glossary": glossary,
            "research": research,
            "ai_context": ai_value,
        }

    def resolve(
        self,
        entity_text,
        research_translation=None,
        ai_context=None,
    ):
        entity_record = self._get_entity_record(
            entity_text
        )

        glossary_record = self._get_glossary_record(
            entity_text
        )

        user_rules = self._get_user_rules(
            entity_text
        )

        # --------------------------------------------------
        # ENTITY TYPE
        # --------------------------------------------------
        if entity_record is not None:
            entity_type = entity_record.get(
                "entity_type",
                "proper_noun",
            )

        elif glossary_record is not None:
            entity_type = "proper_noun"

        else:
            entity_type = "proper_noun"

        sources = self._build_sources(
            entity_text=entity_text,
            entity_record=entity_record,
            glossary_record=glossary_record,
            user_rules=user_rules,
            research_translation=research_translation,
            ai_context=ai_context,
        )

        resolution = self.resolver.resolve(
            entity_text=entity_text,
            user_lock=sources["user_lock"],
            user_rule=sources["user_rule"],
            character_db=sources["character_db"],
            glossary=sources["glossary"],
            research=sources["research"],
            ai_context=sources["ai_context"],
        )

        is_locked = (
            resolution.source == "user_lock"
        )

        return EntityResolutionResult(
            entity_text=entity_text,
            entity_type=entity_type,
            translation=resolution.value,
            source=resolution.source,
            priority=resolution.priority,
            locked=is_locked,
            reason=resolution.reason,
            alternatives=resolution.alternatives,
        )
