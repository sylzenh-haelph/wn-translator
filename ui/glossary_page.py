"""Editor glosarium lewat UI: isian terbaca penuh, bisa dicari, dan disimpan dari atas maupun bawah."""

import html
from pathlib import Path
from shutil import copy2
from urllib.parse import quote as url_quote

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "glossary" / ".bak"

STYLE = """
:root{color-scheme:dark;--bg:#121212;--panel:#1e1e1e;--fg:#e8e8e8;--muted:#9aa0a6;--line:#333;--accent:#8ab4f8;--ok:#81c995;--warn:#f6b26b}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font-family:sans-serif;font-size:17px;margin:0 12px 24px;line-height:1.4}
h1{font-size:22px;margin:12px 0 6px}
h3{margin:4px 0 8px;font-size:18px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;margin:12px 0}
a{color:var(--accent)}
.muted{color:var(--muted);font-size:15px}
label{display:block;color:var(--muted);font-size:15px;margin-top:8px}
input:not([type=checkbox]):not([type=radio]){width:100%;font-size:16px;margin:4px 0;padding:8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px}
input[type=checkbox]{accent-color:var(--accent);width:18px;height:18px;vertical-align:middle}
button{font-size:16px;padding:9px 16px;margin:0;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px}
button[type=submit]{background:var(--accent);color:#101418;border-color:var(--accent);font-weight:bold}
.topbar{position:sticky;top:0;z-index:9;background:var(--bg);padding:8px 12px 6px;margin:0 -12px;border-bottom:1px solid var(--line)}
.row{display:flex;gap:8px;align-items:center;justify-content:space-between}
.stats{display:flex;flex-wrap:wrap;gap:10px;align-items:center;font-size:14px;color:var(--muted);margin:6px 0}
.stats label{display:inline-flex;align-items:center;gap:6px;margin:0;color:var(--fg)}
.sec h3{color:var(--accent);margin:18px 0 0}
.ent{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:8px 0}
.ent.kosong{border-left:4px solid var(--warn)}
.ent.off .asal{color:var(--muted);text-decoration:line-through}
.ent .head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.ent .asal{font-weight:bold;word-break:break-word}
.ent .chk{display:flex;align-items:center;gap:6px;margin:0;color:var(--muted);font-size:14px;white-space:nowrap}
.ent textarea{display:block;width:100%;margin-top:6px;font-size:17px;line-height:1.4;padding:8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;resize:none;overflow:hidden;min-height:44px}
.ent textarea:focus{outline:2px solid var(--accent)}
.bottombar{display:flex;gap:8px;align-items:center;justify-content:space-between;margin:12px 0}
#q{margin:6px 0}
"""

SCRIPT_EDIT = """
function grow(el){el.style.height='auto';el.style.height=(el.scrollHeight+2)+'px';}
function noEnter(e){if(e.key==='Enter'){e.preventDefault();}}
function applyFilter(){
  var q=document.getElementById('q').value.trim().toLowerCase();
  var only=document.getElementById('onlyEmpty').checked;
  document.querySelectorAll('.sec').forEach(function(sec){
    var visible=0;
    sec.querySelectorAll('.ent').forEach(function(card){
      var ok=(!q||card.getAttribute('data-search').indexOf(q)>=0)&&(!only||card.getAttribute('data-empty')==='1');
      card.style.display=ok?'':'none';
      if(ok){visible++;}
    });
    sec.style.display=visible?'':'none';
  });
}
document.querySelectorAll('textarea').forEach(grow);
document.addEventListener('input',function(e){if(e.target.tagName==='TEXTAREA'){grow(e.target);}});
"""


def safe_glossary(value):
    path = Path(value)
    if path.parent != Path("glossary") or path.suffix.lower() != ".txt":
        raise ValueError("file glosarium harus .txt di folder glossary/")
    return ROOT / path


def _clean(value):
    return " ".join(str(value).split())


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
        right = _clean(form.get(f"r{i}", [entry["right"]])[0])
        prefix = "" if f"a{i}" in form else "# "
        lines[i] = f"{prefix}{entry['left']} = {right}"
    return lines


def save_glossary(form):
    value = form.get("file", [""])[0]
    try:
        path = safe_glossary(value)
    except ValueError as exc:
        return f"/glossary?msg={url_quote(str(exc))}"
    left = _clean(form.get("new_left", [""])[0])
    right = _clean(form.get("new_right", [""])[0])
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


def _card(entry):
    i = entry["line"]
    search = html.escape(f"{entry['left']} {entry['right']}".lower())
    classes = ["ent"]
    if not entry["right"]:
        classes.append("kosong")
    if not entry["active"]:
        classes.append("off")
    checked = " checked" if entry["active"] else ""
    empty = "1" if not entry["right"] else "0"
    return (
        f"<div class='{' '.join(classes)}' data-search='{search}' data-empty='{empty}'>"
        f"<div class='head'><span class='asal'>{html.escape(entry['left'])}</span>"
        f"<label class='chk'><input type='checkbox' name='a{i}'{checked}> aktif</label></div>"
        f"<textarea name='r{i}' rows='1' onkeydown='noEnter(event)'>{html.escape(entry['right'])}</textarea>"
        "</div>"
    )


def _page(title, message, body, top=""):
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{STYLE}</style>
</head><body>
{top}
<h1>{html.escape(title)}</h1>
<p class="muted">{html.escape(message)}</p>
{body}
<script>{SCRIPT_EDIT}</script>
</body></html>"""


def glossary_page(value, message=""):
    try:
        path = safe_glossary(value)
    except ValueError as exc:
        return _page("Glosarium", str(exc), "<section><a href='/'>← Kembali</a></section>")
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    entries = parse_entries(text)
    empty = sum(1 for e in entries if not e["right"])
    off = sum(1 for e in entries if not e["active"])

    sections = []
    for entry in entries:
        if not sections or sections[-1][0] != entry["section"]:
            sections.append((entry["section"], []))
        sections[-1][1].append(entry)
    cards = "".join(
        f"<div class='sec'><h3>{html.escape(name or 'tanpa bagian')}</h3>"
        + "".join(_card(e) for e in items)
        + "</div>"
        for name, items in sections
    )
    top = (
        "<div class='topbar'>"
        "<div class='row'>"
        "<a href='/'>← Kembali</a>"
        "<button type='submit' form='gform'>Simpan</button>"
        "</div>"
        "<input type='search' id='q' placeholder='Cari asal atau arti' oninput='applyFilter()'>"
        "<div class='stats'>"
        f"<span>{len(entries)} entri</span><span>{empty} kosong</span><span>{off} nonaktif</span>"
        "<label><input type='checkbox' id='onlyEmpty' onchange='applyFilter()'> hanya kosong</label>"
        "</div></div>"
    )
    body = (
        "<form id='gform' method='post' action='/glossary/save'>"
        f"<input type='hidden' name='file' value='{html.escape(value)}'>"
        f"{cards}"
        "<section><h3>Tambah entri</h3>"
        "<input name='new_left' placeholder='kata asal' onkeydown='noEnter(event)'>"
        "<input name='new_right' placeholder='arti' onkeydown='noEnter(event)'>"
        "<p class='muted'>Entri baru ditaruh di bagian \"tambahan\" di akhir file.</p>"
        "</section>"
        "<div class='bottombar'><a href='/'>← Kembali</a>"
        "<button type='submit'>Simpan</button></div>"
        "</form>"
    )
    return _page(f"Glosarium: {path.name}", message, body, top)
