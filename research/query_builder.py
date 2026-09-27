def build_initial_query(entity_text, entity_type):
    """
    Query awal yang sederhana.

    Belum menggunakan judul novel/author karena informasi tersebut
    baru ditambahkan jika hasil awal tidak cukup jelas.
    """

    if entity_type == "character":
        return f'"{entity_text}" character'

    if entity_type == "place":
        return f'"{entity_text}" location'

    if entity_type == "organization":
        return f'"{entity_text}" organization'

    if entity_type == "item":
        return f'"{entity_text}" item'

    if entity_type == "skill":
        return f'"{entity_text}" skill'

    if entity_type == "race":
        return f'"{entity_text}" race'

    if entity_type == "title":
        return f'"{entity_text}" title'

    return f'"{entity_text}"'


def build_adaptive_query(
    entity_text,
    entity_type,
    novel_title=None,
    author=None,
    chapter_context=None,
    attempt=1,
):
    """
    Membuat query berdasarkan tingkat kebutuhan konteks.

    attempt 1:
        entity + type

    attempt 2:
        + novel title

    attempt 3:
        + author

    attempt 4+:
        + chapter context
    """

    query = build_initial_query(
        entity_text,
        entity_type,
    )

    if attempt >= 2 and novel_title:
        query += f' "{novel_title}"'

    if attempt >= 3 and author:
        query += f' "{author}"'

    if attempt >= 4 and chapter_context:
        # Batasi context agar query tidak menjadi terlalu panjang.
        context = " ".join(
            chapter_context.split()
        )

        if len(context) > 300:
            context = context[:300]

        query += f' "{context}"'

    return query
