from qa.rule_based_qa import run_qa


print("=== PASS CASE ===")

source = (
    "Alice enters the palace.\n"
    "Marcus follows her."
)

translation = (
    "Alice memasuki istana.\n"
    "Marcus mengikutinya."
)

result = run_qa(
    source_text=source,
    translation=translation,
    preserved_entities=["Alice", "Marcus"],
)

print(result)

assert result.passed is True
assert len(result.issues) == 0


print("\n=== EMPTY TRANSLATION ===")

result = run_qa(
    source_text=source,
    translation="",
)

print(result)

assert result.passed is False
assert any(
    issue.rule == "translation_not_empty"
    for issue in result.issues
)


print("\n=== PARAGRAPH COUNT FAILURE ===")

translation = (
    "Alice memasuki istana."
)

result = run_qa(
    source_text=source,
    translation=translation,
)

print(result)

assert result.passed is False
assert any(
    issue.rule == "paragraph_count"
    for issue in result.issues
)


print("\n=== EMPTY PARAGRAPH FAILURE ===")

translation = (
    "Alice memasuki istana.\n"
    "\n"
    "Marcus mengikutinya."
)

source_three = (
    "Alice enters the palace.\n"
    "They stop.\n"
    "Marcus follows her."
)

result = run_qa(
    source_text=source_three,
    translation=translation,
)

print(result)

assert result.passed is False
assert any(
    issue.rule == "empty_paragraph"
    for issue in result.issues
)


print("\n=== PRESERVED ENTITY FAILURE ===")

translation = (
    "Alice memasuki istana.\n"
    "Markus mengikutinya."
)

result = run_qa(
    source_text=source,
    translation=translation,
    preserved_entities=["Alice", "Marcus"],
)

print(result)

assert result.passed is False
assert any(
    issue.rule == "preserved_entity"
    for issue in result.issues
)


print("\n=== UNEXPECTED MODEL TEXT ===")

translation = (
    "Here is the translation:\n"
    "Alice memasuki istana."
)

source_one = "Alice enters the palace."

result = run_qa(
    source_text=source_one,
    translation=translation,
)

print(result)

assert result.passed is False
assert any(
    issue.rule == "unexpected_model_text"
    for issue in result.issues
)


print("\n=== MULTIPLE ISSUES ===")

result = run_qa(
    source_text=source,
    translation="",
    preserved_entities=["Alice", "Marcus"],
)

print(result)

assert result.passed is False
assert len(result.issues) >= 1


print("\nPASS")
