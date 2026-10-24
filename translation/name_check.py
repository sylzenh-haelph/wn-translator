import re


def _has_term(term, text):
    return re.search(rf"(?<![A-Za-z]){re.escape(term.lower())}(?![A-Za-z])", text) is not None


def check_names(chunks, pairs):
    """chunks: (chapter_id, teks_sumber, teks_terjemahan). pairs: (asal, arti) dari glosarium.
    Hanya mengembalikan daftar isu; tidak memanggil model dan tidak mengubah apa pun."""
    issues = []
    seen = set()
    for chapter_id, source, target in chunks:
        src = source.lower()
        tgt = target.lower()
        for left, right in pairs:
            if not right or left.lower() == right.lower():
                continue
            if not _has_term(left, src):
                continue
            if right.lower() not in tgt:
                kind = "tidak_konsisten"
            elif _has_term(left, tgt):
                kind = "masih_inggris"
            else:
                continue
            key = (chapter_id, kind, left)
            if key in seen:
                continue
            seen.add(key)
            issues.append({"chapter": chapter_id, "kind": kind, "term": left, "expected": right})
    return issues
