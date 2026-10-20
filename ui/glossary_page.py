"""Edit glosarium lewat UI: ubah isian, aktif/nonaktif, dan tambah entri. Baris lain tidak disentuh."""

import html
from pathlib import Path
from shutil import copy2
from urllib.parse import quote as url_quote

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "glossary" / ".bak"

STYLE = """
:root{color-scheme:dark;--bg:#121212;--panel:#1e1e1e;--fg:#e8e8e8;--muted:#9aa0a6;--line:#333;--accent:#8ab4f8;--ok:#81c995}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:sans-serif;font-size:17px;margin:12px;line-height:1.4}
h1{font-size:24px;margin:8px 0 12px}
h3{margin:4px 0 8px;font-size:18px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;margin:12px 0}
a{color:var(--accent)}
.muted{color:var(--muted);font-size:15px}
.run{color:var(--ok);font-weight:bold}
.idle{color:var(--muted);font-weight:bold}
label{display:block;color:var(--muted);font-size:15px;margin-top:8px}
.opt label{color:var(--fg);font-size:17px;margin-top:0;padding:4px 0}
select,input:not([type=checkbox]):not([type=radio]){width:100%;font-size:17px;margin:4px 0;padding:8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px}
input[type=checkbox],input[type=radio]{accent-color:var(--accent);width:18px;height:18px;vertical-align:middle}
button{font-size:17px;padding:10px 18px;margin:8px 0;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px}
button[type=submit]{background:var(--accent);color:#101418;border-color:var(--accent);font-weight:bold}
table{border-collapse:collapse;width:100%;font-size:15px}
td,th{border-bottom:1px solid var(--line);padding:8px 4px;text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:normal}
ul{padding-left:20px}
li{margin:6px 0;word-break:break-all}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px}
summary{cursor:pointer;font-weight:bold}
pre{white-space:pre-wrap;font-size:13px;background:var(--bg);color:var(--fg);padding:8px;border-radius:8px}
"""


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
        # shortcut: catatan komentar yang memuat titik atau titik dua dianggap bukan entri; nama asal dengan titik perlu dicek
        if not left or "." in left or ":" in left:
            continue
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
    if "=" in left:
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
<style>{STYLE}</style>
</head><body>
<h1>{html.escape(title)}</h1>
<p class="muted">{html.escape(message)}</p>
{body}
</body></html>"""


def glossary_page(value, message=""):
    try:
        path = safe_glossary(value)
    except ValueError as exc:
        return _page("Glosarium", str(exc), "<section><a href='/'>Kembali</a></section>")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    rows = ""
    for entry in parse_entries(text):
        i = entry["line"]
        checked = " checked" if entry["active"] else ""
        rows += (
            f"<tr><td class='muted'>{html.escape(entry['section'])}</td>"
            f"<td>{html.escape(entry['left'])}</td>"
            f"<td><input name='r{i}' value='{html.escape(entry['right'])}'></td>"
            f"<td><input type='checkbox' name='a{i}'{checked}></td></tr>"
        )
    body = (
        "<form method='post' action='/glossary/save'>"
        f"<input type='hidden' name='file' value='{html.escape(value)}'>"
        "<section><h3>Isian</h3>"
        f"<table><tr><th>Bagian</th><th>Asal</th><th>Indonesia</th><th>Aktif</th></tr>{rows}</table></section>"
        "<section><h3>Tambah entri</h3>"
        "<input name='new_left' placeholder='kata asal'>"
        "<input name='new_right' placeholder='arti'>"
        "<button type='submit'>Simpan</button></section>"
        "</form>"
        "<section><a href='/'>Kembali</a></section>"
    )
    return _page(f"Glosarium: {path.name}", message, body)
