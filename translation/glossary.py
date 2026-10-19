import re
from pathlib import Path


def load_glossary(path):
    file = Path(path)
    if not file.exists():
        return []

    pairs = []
    for line in file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or " = " not in text:
            continue
        left, right = (part.strip() for part in text.split(" = ", 1))
        if left and right:
            pairs.append((left, right))
    return pairs


def apply_glossary(text, pairs):
    # shortcut: kata asal yang terpotong antar run formatting (miring/tebal) belum tergantikan
    if not pairs or not text:
        return text

    table = {}
    for left, right in pairs:
        for form in {left, left.replace("’", "'"), left.replace("'", "’")}:
            table.setdefault(form.lower(), right)

    keys = sorted(table, key=len, reverse=True)
    pattern = re.compile(
        r"(?<![A-Za-z])(" + "|".join(re.escape(k) for k in keys) + r")(?![A-Za-z])",
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: table[m.group(1).lower()], text)
