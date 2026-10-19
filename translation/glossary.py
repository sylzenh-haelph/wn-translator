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


def merge_scan_glossary(entries, path, title):
    # Tambah entri baru saja. Yang sudah ada (termasuk isian Indonesia dan komentar) tidak diubah.
    path = Path(path)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            f"# Glosarium: {title}",
            "# Isi bagian kanan (Indonesia). Kosong = belum diterjemahkan, tidak diterapkan.",
            "",
        ]

    known = set()
    for line in lines:
        text = line.strip()
        if text and not text.startswith("#") and "=" in text:
            known.add(text.split("=", 1)[0].strip().lower())

    by_kind = {}
    for name, kind in entries:
        clean = name.strip()
        if clean and clean.lower() not in known:
            known.add(clean.lower())
            by_kind.setdefault(kind or "lainnya", []).append(clean)

    section_end = {}
    current = None
    for i, line in enumerate(lines):
        text = line.strip()
        if text.startswith("## "):
            current = text[3:].strip()
            section_end[current] = i + 1
        elif current and text and not text.startswith("#") and "=" in text:
            section_end[current] = i + 1

    tail = []
    inserts = []
    for kind in sorted(by_kind):
        new_lines = [f"{name} = " for name in sorted(by_kind[kind], key=str.lower)]
        if kind in section_end:
            inserts.append((section_end[kind], new_lines))
        else:
            tail += ["", f"## {kind}"] + new_lines

    for pos, new_lines in sorted(inserts, key=lambda item: item[0], reverse=True):
        lines[pos:pos] = new_lines
    lines += tail

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sum(len(v) for v in by_kind.values())
