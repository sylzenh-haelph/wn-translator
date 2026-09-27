from dataclasses import dataclass, field

from research.entity_detector import detect_entities
from research.ai_entity_classifier import classify_with_ai
from research.entity_db import EntityDB
from research.entity_resolver import ResolvedEntity
from research.adaptive_research import AdaptiveResearchEngine
from research.research_translation import ResearchTranslationInterpreter
from research.entity_resolution_service import EntityResolutionService
from research.evidence_validator import EvidenceValidator


@dataclass
class PipelineResult:
    entities: list[ResolvedEntity] = field(default_factory=list)
    new_entities: int = 0
    researched_entities: int = 0
    failed_research: int = 0
    rejected_evidence: int = 0


class EntityResearchPipeline:
    def __init__(
        self,
        db: EntityDB,
        client,
        research_engine: AdaptiveResearchEngine,
        interpreter: ResearchTranslationInterpreter | None = None,
        resolution_service: EntityResolutionService | None = None,
        evidence_validator: EvidenceValidator | None = None,
    ):
        self.db = db
        self.client = client
        self.research_engine = research_engine
        self.interpreter = interpreter
        self.resolution_service = resolution_service
        self.evidence_validator = evidence_validator or EvidenceValidator()

    def _classify(self, candidate, context):
        return classify_with_ai(self.client, candidate, context)

    def _build_context(self, document, candidate):
        parts = []

        if document.title:
            parts.append(f"Novel title: {document.title}")

        if document.author:
            parts.append(f"Author: {document.author}")

        paragraph = next(
            (
                p
                for p in document.paragraphs
                if p.id == candidate.source_paragraph_id
            ),
            None,
        )

        if paragraph is not None:
            parts.append(f"Source paragraph: {paragraph.text}")

        return "\n".join(parts)

    def _record_to_resolved(
        self,
        candidate,
        record,
        status,
        reason=None,
    ):
        return ResolvedEntity(
            text=candidate.text,
            entity_type=record.get(
                "entity_type",
                candidate.entity_type,
            ),
            source_paragraph_id=candidate.source_paragraph_id,
            status=status,
            reason=(
                reason
                if reason is not None
                else candidate.reason
            ),
            canonical_name=record.get("canonical_name"),
            translation=record.get("translation"),
            locked=record.get("locked", False),
            source=record.get("source"),
        )

    def _create_entity(self, candidate, classification):
        self.db.add(
            canonical_name=candidate.text,
            entity_type=classification.entity_type,
            translation=None,
            aliases=[],
            locked=False,
            source="ai_classifier",
            notes=classification.reason,
        )

    def _build_research_evidence(self, research_result):
        evidence = []

        for item in research_result.evidence:
            evidence.append(
                {
                    "title": item.title,
                    "url": item.url,
                    "snippet": item.snippet,
                    "source": item.source,
                    "query": research_result.final_query,
                    "confidence": research_result.confidence,
                }
            )

        return evidence

    def _filter_valid_evidence(
        self,
        entity_text,
        entity_type,
        research_evidence,
        query,
    ):
        valid = []
        rejected = []

        for evidence in research_evidence:
            evidence_object = type(
                "Evidence",
                (),
                evidence,
            )()

            validation = self.evidence_validator.validate(
                entity_text=entity_text,
                entity_type=entity_type,
                evidence=evidence_object,
                query=query,
            )

            if validation.valid:
                valid.append(evidence)
            else:
                rejected.append(
                    {
                        "evidence": evidence,
                        "reason": validation.reason,
                        "score": validation.score,
                    }
                )

        return valid, rejected

    def _interpret_research(
        self,
        candidate,
        classification,
        research_evidence,
        document,
        context,
    ):
        if self.interpreter is None:
            return None

        return self.interpreter.interpret(
            entity_text=candidate.text,
            entity_type=classification.entity_type,
            evidence=research_evidence,
            project_title=document.title,
            chapter_context=context,
        )

    def _resolve_translation(
        self,
        entity_text,
        research_candidate=None,
    ):
        if self.resolution_service is None:
            return None

        research_translation = None

        if research_candidate is not None:
            if (
                not research_candidate.preserve_original
                and research_candidate.translation_candidate
                and research_candidate.confidence >= 0.5
            ):
                research_translation = {
                    "value": research_candidate.translation_candidate,
                    "reason": research_candidate.reason,
                }

        return self.resolution_service.resolve(
            entity_text=entity_text,
            research_translation=research_translation,
        )

    def _apply_resolution(self, resolved, resolution):
        if resolution is None:
            return resolved

        resolved.translation = resolution.translation
        resolved.locked = resolution.locked
        resolved.source = resolution.source

        if resolution.reason:
            resolved.reason = resolution.reason

        return resolved

    def process_candidate(self, document, candidate):
        context = self._build_context(
            document,
            candidate,
        )

        existing = self.db.get(candidate.text)

        if existing is not None:
            resolved = self._record_to_resolved(
                candidate,
                existing,
                status="known",
            )

            resolution = self._resolve_translation(
                candidate.text
            )

            return self._apply_resolution(
                resolved,
                resolution,
            ), 0

        classification = self._classify(
            candidate,
            context,
        )

        if (
            classification.entity_type == "unknown"
            or classification.confidence < 0.5
        ):
            self.db.add(
                canonical_name=candidate.text,
                entity_type="proper_noun",
                translation=None,
                aliases=[],
                locked=False,
                source="ai_classifier",
                notes=(
                    "AI classification uncertain: "
                    + classification.reason
                ),
            )

            record = self.db.get(candidate.text)

            resolved = self._record_to_resolved(
                candidate,
                record,
                status="uncertain",
            )

            resolution = self._resolve_translation(
                candidate.text
            )

            return self._apply_resolution(
                resolved,
                resolution,
            ), 0

        self._create_entity(
            candidate,
            classification,
        )

        research_result = self.research_engine.research(
            entity_text=candidate.text,
            entity_type=classification.entity_type,
            novel_title=document.title,
            author=document.author,
            chapter_context=context,
        )

        if research_result.success:
            raw_evidence = self._build_research_evidence(
                research_result
            )

            valid_evidence, rejected_evidence = (
                self._filter_valid_evidence(
                    entity_text=candidate.text,
                    entity_type=classification.entity_type,
                    research_evidence=raw_evidence,
                    query=research_result.final_query,
                )
            )

            for evidence_data in valid_evidence:
                self.db.add_research(
                    entity_type=classification.entity_type,
                    canonical_name=candidate.text,
                    evidence=evidence_data,
                )

            if not valid_evidence:
                self.db.mark_research_failed(
                    entity_type=classification.entity_type,
                    canonical_name=candidate.text,
                )

                record = self.db.get(candidate.text)

                resolved = self._record_to_resolved(
                    candidate,
                    record,
                    status="research_failed",
                    reason=(
                        "Research succeeded, but all "
                        "evidence failed relevance validation."
                    ),
                )

                resolution = self._resolve_translation(
                    candidate.text
                )

                return (
                    self._apply_resolution(
                        resolved,
                        resolution,
                    ),
                    len(rejected_evidence),
                )

            research_candidate = self._interpret_research(
                candidate=candidate,
                classification=classification,
                research_evidence=valid_evidence,
                document=document,
                context=context,
            )

            resolution = self._resolve_translation(
                candidate.text,
                research_candidate=research_candidate,
            )

            record = self.db.get(candidate.text)

            resolved = self._record_to_resolved(
                candidate,
                record,
                status="researched",
            )

            return (
                self._apply_resolution(
                    resolved,
                    resolution,
                ),
                len(rejected_evidence),
            )

        self.db.mark_research_failed(
            entity_type=classification.entity_type,
            canonical_name=candidate.text,
        )

        record = self.db.get(candidate.text)

        resolved = self._record_to_resolved(
            candidate,
            record,
            status="research_failed",
            reason=research_result.reason,
        )

        resolution = self._resolve_translation(
            candidate.text
        )

        return (
            self._apply_resolution(
                resolved,
                resolution,
            ),
            0,
        )

    def process_document(self, document):
        candidates = detect_entities(document)

        result = PipelineResult()

        for candidate in candidates:
            before = self.db.get(
                candidate.text
            )

            resolved, rejected_count = (
                self.process_candidate(
                    document,
                    candidate,
                )
            )

            result.entities.append(resolved)
            result.rejected_evidence += rejected_count

            if before is None:
                result.new_entities += 1

            if resolved.status == "researched":
                result.researched_entities += 1

            elif resolved.status == "research_failed":
                result.failed_research += 1

        return result
