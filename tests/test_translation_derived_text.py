from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.translation_engine import TranslationEngine


class FakeClient:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.reply


def test_chunk_text_is_derived_from_paragraphs():
    client = FakeClient('{"paragraph_translations": ["Alice masuk.", "Marcus mengikuti."], "context_state": {}}')
    result = TranslationEngine(client).translate(
        text="Alice enters.\nMarcus follows.",
        paragraph_texts=["Alice enters.", "Marcus follows."],
    )
    assert result.translation == "Alice masuk.\nMarcus mengikuti."
    assert result.paragraph_translations == ["Alice masuk.", "Marcus mengikuti."]


def test_explicit_translation_still_accepted():
    client = FakeClient('{"translation": "A.\\nB.", "paragraph_translations": ["A.", "B."], "context_state": {}}')
    result = TranslationEngine(client).translate(text="a\nb", paragraph_texts=["a", "b"])
    assert result.translation == "A.\nB."


def test_prompt_no_longer_asks_for_translation_field():
    client = FakeClient('{"paragraph_translations": ["A."], "context_state": {}}')
    TranslationEngine(client).translate(text="a", paragraph_texts=["a"])
    assert '"translation": "..."' not in client.prompts[0]
