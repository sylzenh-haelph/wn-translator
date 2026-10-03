from translation.translation_engine import TranslationEngine


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.last_prompt = ""

    def generate(self, prompt):
        self.last_prompt = prompt
        return self.response


valid_response = """{
  "translation": "Alice masuk.\\nMarcus mengikutinya.",
  "paragraph_translations": [
    "Alice masuk.",
    "Marcus mengikutinya."
  ],
  "context_state": {
    "scene": "Entrance",
    "active_characters": ["Alice", "Marcus"],
    "current_situation": "Alice enters and Marcus follows.",
    "references": ["Royal Palace"],
    "style_state": {
      "tone": "narrative"
    }
  }
}"""

client = FakeClient(valid_response)
engine = TranslationEngine(client)

result = engine.translate(
    text="Alice enters.\nMarcus follows.",
    paragraph_texts=[
        "Alice enters.",
        "Marcus follows.",
    ],
)

assert result.translation == (
    "Alice masuk.\nMarcus mengikutinya."
)

assert result.paragraph_translations == [
    "Alice masuk.",
    "Marcus mengikutinya.",
]

assert len(result.paragraph_translations) == 2

assert result.context_state.scene == "Entrance"
assert result.context_state.active_characters == [
    "Alice",
    "Marcus",
]
assert result.context_state.current_situation == (
    "Alice enters and Marcus follows."
)
assert result.context_state.references == ["Royal Palace"]
assert result.context_state.style_state["tone"] == "narrative"

# Verify paragraph boundaries are explicitly present in the prompt.
assert "[PARAGRAPH 1]" in client.last_prompt
assert "[PARAGRAPH 2]" in client.last_prompt

# Wrong paragraph count must be rejected.
invalid_response = """{
  "translation": "Alice masuk.",
  "paragraph_translations": [
    "Alice masuk."
  ],
  "context_state": {}
}"""

bad_client = FakeClient(invalid_response)
bad_engine = TranslationEngine(bad_client)

try:
    bad_engine.translate(
        text="Alice enters.\nMarcus follows.",
        paragraph_texts=[
            "Alice enters.",
            "Marcus follows.",
        ],
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Output dengan jumlah paragraph_translations "
        "yang salah harus ditolak."
    )

print("=== TRANSLATION ENGINE ===")
print("Translation:", result.translation)
print("Paragraph translations:", len(result.paragraph_translations))
print("Scene:", result.context_state.scene)

print("=== CHECKS ===")
print("Paragraph-level output: PASS")
print("Paragraph count validation: PASS")
print("Context state parsing: PASS")
print("Paragraph boundary prompt: PASS")
print("Invalid output rejection: PASS")
print("PASS")
