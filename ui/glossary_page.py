"""Edit glosarium lewat UI: ubah isian, aktif/nonaktif, dan tambah entri. Baris lain tidak disentuh."""

import html
from pathlib import Path
from shutil import copy2
from urllib.parse import quote as url_quote

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "glossary" / ".bak"


def safe_glossary(value):
    path = Path(value)
    if path.parent != Path("glossary") or path.suffix.lower() != ".txt":
        raise ValueError("file glosarium harus .txt di folder glossary/")
    return ROOT / path


def parse_entries(text):
    entries = []
    section = ""
    for index, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            continue
        active = not stripped.startswith("#")
        body = stripped if active else stripped.lstrip("#").strip()
        if "=" not in body:
            continue
        left, right = (part.strip() for part in body.split("=", 1))
        if left:
            entries.append({"line": index, "section": section, "left": left, "right": right, "active": active})
    return entries


def rebuild(text, form):
    lines = text.splitlines()
    for entry in parse_entries(text):
        i = entry["line"]
        right = form.get(f"r{i}", [entry["right"]])[0].strip()
        prefix = "" if f"a{i}" in form else "# "
        lines[i] = f"{prefix}{entry['left']} = {right}"
    return lines


def save_glossary(form):
    value = form.get("file", [""])[0]
    try:
        path = safe_glossary(value)
    except ValueError as exc:
        return f"/glossary?msg={url_quote(str(exc))}"
    left = form.get("new_left", [""])[0].strip()
    right = form.get("new_right", [""])[0].strip()
    if " = " in left:
        return f"/glossary?file={url_quote(value)}&msg={url_quote('Kata asal tidak boleh memuat tanda sama dengan.')}"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if path.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        copy2(path, BACKUP_DIR / path.name)
    lines = rebuild(text, form) if text else []
    if left:
        lines += ["", "## tambahan", f"{left} = {right}"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"/glossary?file={url_quote(value)}&msg={url_quote('Tersimpan.')}"


def _page(title, message, body):
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>body{{font-family:sans-serif;font-size:17px;margin:12px}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:4px;text-align:left}}
input{{font-size:16px;margin:4px 0;width:100%}}button{{font-size:17px;padding:8px 16px;margin:6px 0}}</style>
</head><body>
<h2>{html.escape(title)}</h2>
<p>{html.escape(message)}</p>
{body}
</body></html>"""


def glossary_page(value, message=""):
    try:
        path = safe_glossary(value)
    except ValueError as exc:
        return _page("Glosarium", str(exc), "<p><a href='/'>Kembali</a></p>")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    rows = ""
    for entry in parse_entries(text):
        i = entry["line"]
        checked = " checked" if entry["active"] else ""
        rows += (
            f"<tr><td>{html.escape(entry['section'])}</td>"
            f"<td>{html.escape(entry['left'])}</td>"
            f"<td><input name='r{i}' value='{html.escape(entry['right'])}'></td>"
            f"<td><input type='checkbox' name='a{i}'{checked}></td></tr>"
        )
    body = (
        f"<form method='post' action='/glossary/save'>"
        f"<input type='hidden' name='file' value='{html.escape(value)}'>"
        f"<table><tr><th>Bagian</th><th>Asal</th><th>Indonesia</th><th>Aktif</th></tr>{rows}</table>"
        "<h3>Tambah entri</h3>"
        "<input name='new_left' placeholder='kata asal'>"
        "<input name='new_right' placeholder='arti'>"
        "<button type='submit'>Simpan</button></form>"
        "<p><a href='/'>Kembali</a></p>"
    )
    return _page(f"Glosarium: {path.name}", message, body)
