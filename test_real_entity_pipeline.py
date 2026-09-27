import json
from pathlib import Path

from models.document import Document, Paragraph, TextRun
from research.entity_pipeline import EntityResearchPipeline
from research.entity_db import EntityDB
from research.adaptive_research import AdaptiveResearchEngine
from research.research_provider import MockResearchProvider, ResearchResult
from research.entity_resolution_service import EntityResolutionService
from storage.glossary_db import GlossaryDB
from storage.user_rule_db import UserRuleDB


# ============================================================
# CLEAN TEST DATA
# ============================================================

for path in [
    "temp/test_real_entity_db.json",
    "temp/test_real_glossary.json",
    "temp/test_real_user_rules.json",
]:
    Path(path).unlink(missing_ok=True)


# ============================================================
# TEST DOCUMENT
# ============================================================

document = Document(
    title="Integration Test Novel",
    author="Integration Author",
    paragraphs=[
        Paragraph(
            id="p0000",
            runs=[
                TextRun(
                    text=(
                        "Alice enters the Royal Palace "
                        "with the Silver Sword."
                    )
                )
            ],
        )
    ],
)


# ============================================================
# FAKE AI ENTITY CLASSIFIER CLIENT
# ============================================================

class FakeEntityClient:
    def generate(self, prompt):
        """
        Simulates the exact interface expected by
        research.ai_entity_classifier.classify_with_ai().

        IMPORTANT:
        Read only the explicit `Entity:` field so the surrounding
        context cannot accidentally affect the classification.
        """

        entity = None

        lines = prompt.splitlines()

        for index, line in enumerate(lines):
            if line.strip() == "Entity:":
                if index + 1 < len(lines):
                    entity = lines[index + 1].strip()
                break

        classifications = {
            "Alice": {
                "entity_type": "character",
                "confidence": 0.98,
                "reason": "Alice is a person/character in the context.",
            },
            "Royal Palace": {
                "entity_type": "place",
                "confidence": 0.95,
                "reason": "Royal Palace is a named location.",
            },
            "Silver Sword": {
                "entity_type": "item",
                "confidence": 0.95,
                "reason": "Silver Sword is a named weapon/item.",
            },
        }

        result = classifications.get(
            entity,
            {
                "entity_type": "unknown",
                "confidence": 0.0,
                "reason": "Unknown test entity.",
            },
        )

        return json.dumps(result)


# ============================================================
# FAKE RESEARCH EVALUATOR CLIENT
# ============================================================

class FakeResearchClient:
    def generate(self, prompt):
        return json.dumps(
            {
                "sufficient": True,
                "confidence": 0.95,
                "selected_indices": [0],
                "reason": (
                    "The mock research result is sufficient "
                    "for this integration test."
                ),
                "needs_more_context": False,
            }
        )


# ============================================================
# MOCK RESEARCH PROVIDER
# ============================================================

class EntityAwareMockResearchProvider(MockResearchProvider):
    def search(self, query, max_results=5):
        query_lower = query.casefold()

        if "alice" in query_lower:
            results = [
                ResearchResult(
                    title="Alice - Example Novel Character",
                    url="https://example.com/alice",
                    snippet=(
                        "Alice is a character in Example Novel "
                        "and enters the Royal Palace."
                    ),
                    source="mock",
                    relevance=0.95,
                )
            ]

        elif "royal palace" in query_lower:
            results = [
                ResearchResult(
                    title="Royal Palace - Example Novel Location",
                    url="https://example.com/royal-palace",
                    snippet=(
                        "The Royal Palace is a named location "
                        "in Example Novel."
                    ),
                    source="mock",
                    relevance=0.95,
                )
            ]

        elif "silver sword" in query_lower:
            results = [
                ResearchResult(
                    title="Silver Sword - Fictional Item Reference",
                    url="https://example.com/silver-sword",
                    snippet=(
                        "Silver Sword is a named weapon used "
                        "in the novel."
                    ),
                    source="mock",
                    relevance=0.95,
                )
            ]

        else:
            results = []

        return results[:max_results]


research_provider = EntityAwareMockResearchProvider()

research_engine = AdaptiveResearchEngine(
    provider=research_provider,
    client=FakeResearchClient(),
    max_attempts=4,
)


# ============================================================
# ENTITY DATABASE
# ============================================================

entity_db = EntityDB(
    path="temp/test_real_entity_db.json"
)


# ============================================================
# REAL ENTITY RESEARCH PIPELINE
# ============================================================

pipeline = EntityResearchPipeline(
    db=entity_db,
    client=FakeEntityClient(),
    research_engine=research_engine,
)


# ============================================================
# RUN REAL PIPELINE
# ============================================================

print("=== REAL ENTITY PIPELINE ===")

result = pipeline.process_document(document)

print(f"Entity count: {len(result.entities)}")
print(f"New entities: {result.new_entities}")
print(f"Researched entities: {result.researched_entities}")
print(f"Failed research: {result.failed_research}")

for entity in result.entities:
    print(
        entity.text,
        "|",
        entity.entity_type,
        "|",
        entity.status,
        "|",
        entity.translation,
    )


# ============================================================
# ASSERT ENTITY RESULTS
# ============================================================

assert len(result.entities) == 3

entities = {
    entity.text: entity
    for entity in result.entities
}

assert "Alice" in entities
assert "Royal Palace" in entities
assert "Silver Sword" in entities

assert entities["Alice"].entity_type == "character"
assert entities["Royal Palace"].entity_type == "place"
assert entities["Silver Sword"].entity_type == "item"

assert entities["Alice"].status == "researched"
assert entities["Royal Palace"].status == "researched"
assert entities["Silver Sword"].status == "researched"


# ============================================================
# CHECK DATABASE
# ============================================================

print("\n=== ENTITY DATABASE ===")

alice = entity_db.get("Alice")
palace = entity_db.get("Royal Palace")
sword = entity_db.get("Silver Sword")

assert alice is not None
assert palace is not None
assert sword is not None

assert alice["entity_type"] == "character"
assert palace["entity_type"] == "place"
assert sword["entity_type"] == "item"

print(alice)
print(palace)
print(sword)


# ============================================================
# CHECK RESEARCH EVIDENCE
# ============================================================

print("\n=== RESEARCH EVIDENCE ===")

sword_research = entity_db.get("Silver Sword")

assert sword_research is not None

research_evidence = sword_research.get("research", [])

print(f"Research entries: {len(research_evidence)}")

for evidence in research_evidence:
    print(evidence)

assert len(research_evidence) >= 1

assert (
    research_evidence[0]["title"]
    == "Silver Sword - Fictional Item Reference"
)


# ============================================================
# ENTITY RESOLUTION SERVICE
# ============================================================

print("\n=== ENTITY RESOLUTION ===")

glossary_db = GlossaryDB(
    path="temp/test_real_glossary.json"
)

user_rule_db = UserRuleDB(
    path="temp/test_real_user_rules.json"
)

resolution_service = EntityResolutionService(
    entity_db=entity_db,
    glossary_db=glossary_db,
    user_rule_db=user_rule_db,
)


# ============================================================
# RESEARCH TRANSLATION
# ============================================================

resolution = resolution_service.resolve(
    "Silver Sword",
    research_translation="Pedang Perak",
)

print(resolution)

assert resolution.translation == "Pedang Perak"
assert resolution.source == "research"


# ============================================================
# USER RULE OVERRIDE
# ============================================================

print("\n=== USER RULE OVERRIDE ===")

user_rule_db.add(
    rule_id="rule_silver_sword_001",
    rule_type="translation",
    target="Silver Sword",
    value="Pedang Perak Perak",
    locked=False,
    notes="Test user rule",
)

resolution = resolution_service.resolve(
    "Silver Sword",
    research_translation="Pedang Perak",
)

print(resolution)

assert resolution.translation == "Pedang Perak Perak"
assert resolution.source == "user_rule"


# ============================================================
# LOCKED USER RULE
# ============================================================

print("\n=== LOCKED USER RULE ===")

rules = user_rule_db.find_by_target("Silver Sword")

assert len(rules) >= 1

rule_id = rules[0]["rule_id"]

user_rule_db.lock(rule_id)

resolution = resolution_service.resolve(
    "Silver Sword",
    research_translation="Terjemahan Lain",
)

print(resolution)

assert resolution.translation == "Pedang Perak Perak"
assert resolution.source == "user_lock"
assert resolution.locked is True


# ============================================================
# FINAL
# ============================================================

print("\nPASS")
