

from translation.translation_engine import TranslationEngine
def test_translation_engine_preserves_one_item_per_source_paragraph():
    class FakeClient:
        def generate(self, prompt):
            return """{
                "translation": "Alice memasuki ruangan.\\nMarcus mengikutinya dengan diam-diam.",
                "paragraph_translations": [
                    "Alice memasuki ruangan.",
                    "Marcus mengikutinya dengan diam-diam."
                ],
                "context_state": {
                    "scene": "",
                    "active_characters": [],
                    "current_situation": "",
                    "references": [],
                    "style_state": {}
                }
            }"""

    engine = TranslationEngine(client=FakeClient())

    result = engine.translate(
        text="Alice entered the room.\\nMarcus followed her quietly.",
        paragraph_texts=[
            "Alice entered the room.",
            "Marcus followed her quietly.",
        ],
    )

    assert len(result.paragraph_translations) == 2
    assert result.paragraph_translations == [
        "Alice memasuki ruangan.",
        "Marcus mengikutinya dengan diam-diam.",
    ]
    assert all("\n" not in item for item in result.paragraph_translations)
