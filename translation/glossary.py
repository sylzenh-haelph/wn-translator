import json
import re
from datetime import datetime
from pathlib import Path


TERM_PROMPT = (
    "Kamu menyusun glosarium terjemahan novel fantasi dari bahasa Inggris ke Indonesia. "
    "Untuk setiap istilah, berikan arti Indonesia yang paling tepat dan lazim dipakai pembaca novel terjemahan. "
    "Nama orang dan nama tempat yang lazim tetap ditulis seperti aslinya. "
    "Gelar, organisasi, nama benda, dan nama skill diterjemahkan. "
    "Jawab HANYA JSON berupa objek: kunci = istilah asli persis seperti yang diberikan, nilai = arti Indonesia."
)


def load_glossary(path):
    file = Path(path)
    if not file.exists():
        return []

    pairs = []
    aliases = []
    for line in file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or " = " not in text:
            continue
        left, right = (part.strip() for part in text.split(" = ", 1))
        if not left or not right:
            continue
        if left.startswith("~"):
            aliases.append((left[1:].strip(), right))
        else:
            pairs.append((left, right))

    # Alias: '~Rudy = Rudeus Greyrat' memakai terjemahan yang sama dengan 'Rudeus Greyrat'.
    table = {left.lower(): right for left, right in pairs}
    for alias, canonical in aliases:
        value = table.get(canonical.lower())
        if alias and value:
            pairs.append((alias, value))
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


def entry_name(text):
    # Baris aktif maupun nonaktif (diawali '#') dihitung sebagai entri; catatan komentar tidak.
    body = text.lstrip("#").strip() if text.startswith("#") else text
    if "=" not in body:
        return None
    left = body.split("=", 1)[0].strip().lstrip("~").strip()
    if not left or "." in left or ":" in left:
        return None
    return left


def _words(name):
    return tuple(re.findall(r"[a-z0-9]+", name.lower()))


def _contains(longer, shorter):
    n, m = len(longer), len(shorter)
    return m < n and any(longer[i:i + m] == shorter for i in range(n - m + 1))


def prune_scan_names(entries, existing_names):
    # shortcut: pembandingan per kata; ejaan beda tanpa kata yang sama (mis. 'Manggod' vs 'Man-God') belum digabung
    items, seen = [], set()
    for name, kind in entries:
        clean = name.strip()
        key = _words(clean)
        if clean and key and key not in seen:
            seen.add(key)
            items.append((clean, kind, key))

    existing = [_words(name) for name in existing_names]
    keep = []
    for clean, kind, key in items:
        if key in existing:
            continue
        if any(_contains(other, key) for _, _, other in items if other != key):
            continue
        if any(_contains(old, key) for old in existing):
            continue
        keep.append((clean, kind))
    return keep


def translate_terms(client, names):
    """Minta model memberi arti Indonesia. Kalau gagal, hasilnya kosong dan scan tetap jalan."""
    from translation.model_client import extract_json

    unique = list(dict.fromkeys(name.strip() for name in names if name.strip()))
    if not unique:
        return {}
    prompt = TERM_PROMPT + "\n\nISTILAH:\n" + json.dumps(unique, ensure_ascii=False)
    try:
        data = extract_json(client.generate(prompt))
    except Exception as exc:
        print(f"Arti otomatis dilewati: {exc}")
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(key).strip().lower(): str(value).strip()
        for key, value in data.items()
        if str(value).strip()
    }


def meta_path(path):
    path = Path(path)
    return path.parent / ".meta" / f"{path.name}.json"


def read_meta(path):
    file = meta_path(path)
    if not file.exists():
        return {}
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def write_meta(path, added):
    meta = read_meta(path)
    seen = meta.get("seen") if isinstance(meta.get("seen"), dict) else {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    for name in added:
        seen[name] = now
    file = meta_path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        json.dumps({"new": list(added), "seen": seen}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )


def merge_scan_glossary(entries, path, title, translations=None):
    # Tambah entri baru saja. Entri yang sudah ada (aktif maupun nonaktif) tidak diubah dan tidak diduplikat.
    translations = translations or {}
    path = Path(path)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = [
            f"# Glosarium: {title}",
            "# Isi bagian kanan (Indonesia). Kosong = belum diterjemahkan, tidak diterapkan.",
            "",
        ]

    existing = [name for name in (entry_name(line.strip()) for line in lines) if name]
    known = {name.lower() for name in existing}

    fresh = [(name, kind) for name, kind in entries if name.strip().lower() not in known]
    by_kind = {}
    for name, kind in prune_scan_names(fresh, existing):
        by_kind.setdefault(kind or "lainnya", []).append(name)

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
        new_lines = [
            f"{name} = {translations.get(name.lower(), '')}".rstrip()
            for name in sorted(by_kind[kind], key=str.lower)
        ]
        if kind in section_end:
            inserts.append((section_end[kind], new_lines))
        else:
            tail += ["", f"## {kind}"] + new_lines

    for pos, new_lines in sorted(inserts, key=lambda item: item[0], reverse=True):
        lines[pos:pos] = new_lines
    lines += tail

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    added = [name for names in by_kind.values() for name in names]
    write_meta(path, added)
    return len(added)
