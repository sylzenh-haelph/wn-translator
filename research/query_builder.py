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
        entity + type + novel title (jika ada)

    attempt 2:
        + author

    attempt 3+:
        sama dengan attempt 2. Teks paragraf sumber tidak dimasukkan ke query,
        karena membuat hasil Tavily menyimpang.
    """

    query = build_initial_query(
        entity_text,
        entity_type,
    )

    if novel_title:
        query += f' "{novel_title}"'

    if attempt >= 2 and author:
        query += f' "{author}"'


    return query
