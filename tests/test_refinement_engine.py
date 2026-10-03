import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from translation.chapter_context import ContextState
from translation.refinement_engine import RefinementEngine


class FakeClient:
    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)

        return """{
            "translation": "Alice akhirnya masuk.",
            "paragraph_translations": [
                "Alice akhirnya masuk."
            ],
            "context_state": {
                "scene": "refined scene",
                "active_characters": ["Alice"],
                "current_situation": "Alice enters",
                "references": [],
                "style_state": {}
            }
        }"""


def test_refinement_engine_passes_previous_translation_and_qa_issues():
    client = FakeClient()
    engine = RefinementEngine(client)

    result = engine.refine(
        text="Alice enters.",
        translation="Alice masuk.",
        paragraph_translations=["Alice masuk."],
        chapter_context={"tone": "fiction"},
        context_state=ContextState(
            scene="initial scene",
        ),
        entity_resolutions=[
            {"text": "Alice"}
        ],
        qa_issues=[
            {
                "rule": "test_rule",
                "message": "Perbaiki terjemahan.",
                "severity": "error",
            }
        ],
    )

    assert result.translation == (
        "Alice akhirnya masuk."
    )

    assert result.paragraph_translations == [
        "Alice akhirnya masuk."
    ]

    assert result.context_state.scene == (
        "refined scene"
    )

    assert len(client.prompts) == 1

    prompt = client.prompts[0]

    assert "Alice masuk." in prompt
    assert "Perbaiki terjemahan." in prompt
    assert "Alice enters." in prompt
    assert "Alice" in prompt


def test_refinement_engine_rejects_wrong_paragraph_count():
    class BadClient:
        def generate(self, prompt):
            return """{
                "translation": "Satu.",
                "paragraph_translations": [],
                "context_state": {}
            }"""

    engine = RefinementEngine(BadClient())

    try:
        engine.refine(
            text="Alice enters.",
            translation="Alice masuk.",
            paragraph_translations=[
                "Alice masuk."
            ],
        )
    except ValueError as exc:
        assert (
            "paragraph_translations" in str(exc)
        )
    else:
        raise AssertionError(
            "RefinementEngine seharusnya menolak "
            "jumlah paragraph yang tidak sesuai."
        )
