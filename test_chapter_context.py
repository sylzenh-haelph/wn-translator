from translation.chapter_context import (
    ContextState,
    build_chapter_context,
    build_initial_context_state,
    update_context_state,
)


class FakeEntity:
    def __init__(self, text, entity_type, translation=None):
        self.text = text
        self.entity_type = entity_type
        self.translation = translation


print("=== CHAPTER CONTEXT ===")

entities = [
    FakeEntity(
        "Alice",
        "character",
        None,
    ),
    FakeEntity(
        "Silver Sword",
        "item",
        "Pedang Perak",
    ),
]

context = build_chapter_context(
    chapter_id="chapter_001",
    chapter_title="Chapter 1",
    resolved_entities=entities,
    character_context={
        "Alice": {
            "role": "protagonist",
        }
    },
    style_state={
        "dialogue_style": "source",
    },
    important_references=[
        {
            "text": "Silver Sword",
            "translation": "Pedang Perak",
        }
    ],
)

print(context.to_dict())

assert context.chapter_id == "chapter_001"
assert context.chapter_title == "Chapter 1"
assert len(context.entities) == 2
assert context.character_context["Alice"]["role"] == "protagonist"
assert context.style_state["dialogue_style"] == "source"


print("\n=== INITIAL CONTEXT STATE ===")

state = build_initial_context_state()

print(state.to_dict())

assert state.scene == ""
assert state.active_characters == []
assert state.current_situation == ""
assert state.references == []
assert state.style_state == {}


print("\n=== UPDATE CONTEXT STATE ===")

state = update_context_state(
    state,
    {
        "scene": "Alice enters the Royal Palace.",
        "active_characters": ["Alice", "Marcus"],
        "current_situation": "Alice is looking for Marcus.",
        "references": ["Royal Palace"],
        "style_state": {
            "dialogue_style": "source"
        },
    },
)

print(state.to_dict())

assert state.scene == "Alice enters the Royal Palace."
assert state.active_characters == ["Alice", "Marcus"]
assert state.current_situation == "Alice is looking for Marcus."
assert state.references == ["Royal Palace"]
assert state.style_state["dialogue_style"] == "source"


print("\n=== PARTIAL UPDATE ===")

state = update_context_state(
    state,
    {
        "scene": "Alice talks to Marcus."
    },
)

print(state.to_dict())

assert state.scene == "Alice talks to Marcus."
assert state.active_characters == ["Alice", "Marcus"]
assert state.current_situation == "Alice is looking for Marcus."
assert state.references == ["Royal Palace"]


print("\nPASS")
