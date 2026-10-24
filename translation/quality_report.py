import re

ENGLISH_WORDS = {
    "the", "and", "was", "were", "he", "she", "they", "is", "are", "of", "to", "in",
    "that", "it", "with", "for", "on", "had", "have", "not", "his", "her", "you",
    "this", "but", "at", "from", "i",
}
SPEAKER = re.compile(r"^\s*([A-Z][\w'’\-]*(?:\s+[A-Z][\w'’\-]*){0,2})\s*:\s*[\[\"“‘'(]")


def english_ratio(sentence):
    words = re.findall(r"[A-Za-z']+", sentence.lower())
    if len(words) < 6:
        return 0.0
    hits = sum(1 for word in words if word in ENGLISH_WORDS)
    return hits / len(words)


def check_quality(chunks):
    """chunks: (chapter_id, paragraf_sumber, paragraf_terjemahan). Tidak memanggil model."""
    issues = []
    for chapter_id, sources, targets in chunks:
        for source, target in zip(sources, targets):
            if not target or not target.strip():
                continue
            match = SPEAKER.match(source)
            if match and not target.strip().startswith(match.group(1)):
                issues.append({"chapter": chapter_id, "kind": "dialog_hilang", "sample": target[:120]})
            for sentence in re.split(r"(?<=[.!?])\s+", target):
                if english_ratio(sentence) >= 0.3:
                    issues.append({"chapter": chapter_id, "kind": "inggris_lolos", "sample": sentence[:160]})
    return issues
