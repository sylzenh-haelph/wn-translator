from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChapterContext:
    chapter_id: str
    chapter_title: str = ""
    entities: list[dict[str, Any]] = field(default_factory=list)
    character_context: dict[str, Any] = field(default_factory=dict)
    style_state: dict[str, Any] = field(default_factory=dict)
    important_references: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self):
        return {
            "chapter_id": self.chapter_id,
            "chapter_title": self.chapter_title,
            "entities": self.entities,
            "character_context": self.character_context,
            "style_state": self.style_state,
            "important_references": self.important_references,
        }


@dataclass
class ContextState:
    scene: str = ""
    active_characters: list[str] = field(default_factory=list)
    current_situation: str = ""
    references: list[str] = field(default_factory=list)
    style_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "scene": self.scene,
            "active_characters": self.active_characters,
            "current_situation": self.current_situation,
            "references": self.references,
            "style_state": self.style_state,
        }


def build_chapter_context(
    chapter_id,
    chapter_title="",
    resolved_entities=None,
    character_context=None,
    style_state=None,
    important_references=None,
):
    """
    Membuat context awal untuk satu chapter.

    Tidak membuat summary chapter.
    Context hanya berisi informasi terstruktur yang
    memang sudah tersedia dari pipeline sebelumnya.
    """

    entities = []

    if resolved_entities:
        for entity in resolved_entities:
            if hasattr(entity, "__dict__"):
                entity_data = {
                    key: value
                    for key, value in entity.__dict__.items()
                }
            elif isinstance(entity, dict):
                entity_data = dict(entity)
            else:
                continue

            entities.append(entity_data)

    return ChapterContext(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        entities=entities,
        character_context=dict(character_context or {}),
        style_state=dict(style_state or {}),
        important_references=list(important_references or []),
    )


def build_initial_context_state():
    """
    Context dinamis sebelum chunk pertama diterjemahkan.
    """

    return ContextState()


def update_context_state(
    previous_state,
    model_state,
):
    """
    Menggabungkan ContextState sebelumnya dengan state baru
    yang dikembalikan model.

    Field yang tidak diberikan model dipertahankan dari state lama.
    """

    if previous_state is None:
        previous_state = ContextState()

    if isinstance(model_state, ContextState):
        new_state = model_state.to_dict()
    elif isinstance(model_state, dict):
        new_state = model_state
    else:
        new_state = {}

    active_characters = new_state.get(
        "active_characters",
        previous_state.active_characters,
    )

    references = new_state.get(
        "references",
        previous_state.references,
    )

    style_state = new_state.get(
        "style_state",
        previous_state.style_state,
    )

    if not isinstance(active_characters, list):
        active_characters = previous_state.active_characters

    if not isinstance(references, list):
        references = previous_state.references

    if not isinstance(style_state, dict):
        style_state = previous_state.style_state

    return ContextState(
        scene=new_state.get(
            "scene",
            previous_state.scene,
        ),
        active_characters=active_characters,
        current_situation=new_state.get(
            "current_situation",
            previous_state.current_situation,
        ),
        references=references,
        style_state=style_state,
    )
