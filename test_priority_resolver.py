from research.priority_resolver import PriorityResolver


def show(label, result):
    print(f"\n=== {label} ===")
    print("Value       :", result.value)
    print("Source      :", result.source)
    print("Priority    :", result.priority)
    print("Locked      :", result.locked)
    print("Reason      :", result.reason)
    print("Alternatives:", result.alternatives)


def main():
    resolver = PriorityResolver()

    # --------------------------------------------------
    # TEST 1
    # Research saja
    # --------------------------------------------------
    result = resolver.resolve(
        "Silver Sword",
        research={
            "value": "Pedang Perak",
            "reason": "Research evidence",
        },
    )

    show("RESEARCH ONLY", result)

    assert result.value == "Pedang Perak"
    assert result.source == "research"

    # --------------------------------------------------
    # TEST 2
    # User Rule mengalahkan Research
    # --------------------------------------------------
    result = resolver.resolve(
        "Silver Sword",
        user_rule={
            "value": "Pedang Perak Sakti",
            "reason": "User translation rule",
        },
        research={
            "value": "Pedang Perak",
            "reason": "Research evidence",
        },
    )

    show("USER RULE > RESEARCH", result)

    assert result.value == "Pedang Perak Sakti"
    assert result.source == "user_rule"

    # --------------------------------------------------
    # TEST 3
    # Character DB mengalahkan Glossary
    # --------------------------------------------------
    result = resolver.resolve(
        "Alice",
        character_db={
            "value": "Alice",
            "reason": "Character database",
        },
        glossary={
            "value": "Alisa",
            "reason": "Glossary entry",
        },
    )

    show("CHARACTER DB > GLOSSARY", result)

    assert result.value == "Alice"
    assert result.source == "character_db"

    # --------------------------------------------------
    # TEST 4
    # User Lock mengalahkan semuanya
    # --------------------------------------------------
    result = resolver.resolve(
        "Silver Sword",
        user_lock={
            "value": "Pedang Perak",
            "locked": True,
            "reason": "Manually locked by user",
        },
        user_rule={
            "value": "Pedang Perak Sakti",
            "reason": "User rule",
        },
        character_db={
            "value": "Silver Sword",
            "reason": "Character DB",
        },
        glossary={
            "value": "Pedang Perak",
            "reason": "Glossary",
        },
        research={
            "value": "Pedang Perak Milik Protagonis",
            "reason": "Research",
        },
        ai_context={
            "value": "Pedang Perak",
            "reason": "Chapter context",
        },
    )

    show("USER LOCK > EVERYTHING", result)

    assert result.value == "Pedang Perak"
    assert result.source == "user_lock"
    assert result.locked is True

    # --------------------------------------------------
    # TEST 5
    # AI Context menjadi fallback terakhir
    # --------------------------------------------------
    result = resolver.resolve(
        "Unknown Term",
        ai_context={
            "value": "Istilah Tidak Dikenal",
            "reason": "Current chapter context",
        },
    )

    show("AI CONTEXT FALLBACK", result)

    assert result.value == "Istilah Tidak Dikenal"
    assert result.source == "ai_context"

    # --------------------------------------------------
    # TEST 6
    # Tidak ada sumber
    # --------------------------------------------------
    result = resolver.resolve(
        "Unknown Entity"
    )

    show("NO SOURCE", result)

    assert result.value is None
    assert result.source == "none"

    print("\nPASS")


if __name__ == "__main__":
    main()
