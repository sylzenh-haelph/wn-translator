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


def write_scan_glossary(entries, path, title):
    # Kanan kosong = belum diterjemahkan, jadi tidak diterapkan sampai diisi.
    seen = {}
    for name, kind in entries:
        clean = name.strip()
        if clean and clean.lower() not in seen:
            seen[clean.lower()] = (clean, kind or "lainnya")

    by_kind = {}
    for clean, kind in seen.values():
        by_kind.setdefault(kind, []).append(clean)

    lines = [
        f"# Glosarium: {title}",
        "# Isi bagian kanan (Indonesia). Kosong = belum diterjemahkan, tidak diterapkan.",
        "",
    ]
    for kind in sorted(by_kind):
        lines.append(f"## {kind}")
        lines.extend(f"{name} = " for name in sorted(by_kind[kind], key=str.lower))
        lines.append("")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
