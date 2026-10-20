from research.query_builder import build_adaptive_query


print("=== ADAPTIVE QUERY TEST ===")

for attempt in range(1, 5):
    query = build_adaptive_query(
        entity_text="Silver Sword",
        entity_type="item",
        novel_title="Example Novel",
        author="Example Author",
        chapter_context=(
            "The Silver Sword was lying on the table "
            "after the battle."
        ),
        attempt=attempt,
    )

    print(f"Attempt {attempt}:")
    print(query)
    print()
