"""UI lokal WN Translator. Dibuka dari browser HP lewat 127.0.0.1."""

import html
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shlex import quote
from urllib.parse import parse_qs, quote as url_quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ui.glossary_page import STYLE, glossary_page, save_glossary  # noqa: E402

HOST = "127.0.0.1"
PORT = 8765
JOB = "wn_ui_job"
DOWNLOAD = Path("/storage/emulated/0/Download")
JOB_LOG = ROOT / "temp" / "ui_job.log"
JOB_MODE = ROOT / "temp" / "ui_job_mode.txt"
STATUS_TEXT = {"not_started": "belum mulai", "in_progress": "belum selesai", "completed": "selesai"}
INPUT_SUFFIXES = {".epub", ".docx"}
FORMATS = ("epub", "docx")
MODES = ("translate", "export", "scan")
MODE_LABELS = (("translate", "Terjemahkan"), ("export", "Ekspor"), ("scan", "Scan"))
HINTS = {
    "translate": "Menerjemahkan chapter yang dicentang, lalu membuat hasil penuh dalam format yang dipilih.",
    "export": "Mengekspor chapter yang sudah selesai dan dicentang ke format yang dipilih, tanpa menerjemahkan ulang.",
    "scan": "Hanya mencari nama dan istilah untuk glosarium. Tidak membuat EPUB atau DOCX.",
}
MIME = {
    "epub": "application/epub+zip",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
GLOSSARY_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")
OUTPUT_NAME = re.compile(r"^[A-Za-z0-9 _.\-()]+$")
RENAME_KEY = "if(event.key==='Enter'){event.preventDefault();renameGlossary();}"
NO_ENTER = "if(event.key==='Enter'){event.preventDefault();}"

EXTRA_STYLE = """
.wrap{position:relative}
.lock{position:absolute;inset:0;z-index:5;display:flex;align-items:center;justify-content:center;text-align:center;padding:16px;background:rgba(18,18,18,.8);border-radius:10px;cursor:pointer;color:var(--fg);font-weight:bold}
button.flash{box-shadow:0 0 0 4px #f28b82}
button:disabled{opacity:.45;cursor:not-allowed}
.seg{position:relative;display:flex;background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:4px;margin:6px 0}
.seg input{position:absolute;opacity:0;pointer-events:none}
.seg label{position:relative;z-index:1;flex:1;text-align:center;margin:0;padding:9px 6px;font-size:16px;color:var(--muted);cursor:pointer;transition:color .3s}
.seg input:checked + label{color:#101418;font-weight:bold}
.seg .thumb{position:absolute;z-index:0;top:4px;bottom:4px;left:4px;width:calc((100% - 8px)/3);border-radius:999px;background:var(--accent);transition:transform .35s cubic-bezier(.4,0,.2,1)}
.seg.duo .thumb{width:calc((100% - 8px)/2)}
#m-translate:checked ~ .thumb{transform:translateX(0)}
#m-export:checked ~ .thumb{transform:translateX(100%)}
#m-scan:checked ~ .thumb{transform:translateX(200%)}
#f-epub:checked ~ .thumb{transform:translateX(0)}
#f-docx:checked ~ .thumb{transform:translateX(100%)}
.bar{height:16px;border-radius:999px;background:var(--bg);border:1px solid var(--line);overflow:hidden}
.fill{height:100%;width:0;border-radius:999px;background:var(--accent);transition:width .6s ease}
.running .fill{background-image:linear-gradient(45deg,rgba(255,255,255,.22) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.22) 50%,rgba(255,255,255,.22) 75%,transparent 75%,transparent);background-size:24px 24px;animation:stripes 1s linear infinite}
@keyframes stripes{from{background-position:0 0}to{background-position:24px 0}}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--ok);margin-right:8px;vertical-align:middle;animation:pulse 1.2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:.3;transform:scale(.8)}50%{opacity:1;transform:scale(1.15)}}
.spin{display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--accent);border-radius:50%;margin-right:8px;vertical-align:middle;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.rowbox{display:flex;gap:8px;align-items:center}
.rowbox input{flex:1}
.sub{color:var(--muted);font-size:15px;margin:-4px 0 14px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

SCRIPT = """
function toStop(){
  var b=document.getElementById('stop-btn');
  if(!b){return;}
  b.scrollIntoView({behavior:'smooth',block:'center'});
  b.classList.add('flash');
  setTimeout(function(){b.classList.remove('flash');},1500);
}
function setMode(v){
  var out=document.getElementById('outsec');
  if(out){out.style.display=(v==='scan')?'none':'';}
  var h=document.getElementById('modehint');
  if(h){h.textContent=HINTS[v]||'';}
}
function setFormat(v){
  document.querySelectorAll('tr[data-id]').forEach(function(tr){
    var cb=tr.querySelector('input[name=ch]');
    if(!cb){return;}
    var have=(tr.getAttribute('data-have')||'').split(',');
    var done=tr.getAttribute('data-done')==='1';
    cb.checked=(!done)||(have.indexOf(v)<0);
  });
}
function pickGlossary(v){
  var isNew=v==='__new__';
  var n=document.getElementById('newg');
  if(n){n.style.display=isNew?'':'none';}
  var r=document.getElementById('renamebox');
  if(r){r.style.display=isNew?'none':'';}
  var a=document.getElementById('editlink');
  if(a){
    if(isNew){a.style.display='none';}
    else{a.style.display='';a.href='/glossary?file='+encodeURIComponent('glossary/'+v);}
  }
}
function go(extra){
  var m=document.querySelector('input[name=mode]:checked');
  var f=document.querySelector('input[name=fmt]:checked');
  var o=document.getElementById('out_name');
  var q='&m='+(m?m.value:'translate')+'&f='+(f?f.value:'epub');
  if(o&&o.value){q+='&o='+encodeURIComponent(o.value);}
  location.href='/?'+extra+q;
}
function renameGlossary(){
  var form=document.getElementById('mainform');
  var old=document.getElementById('gsel').value;
  var to=document.getElementById('rename_to').value;
  var data=new FormData(form);
  data.delete('ch');
  data.set('glossary',old);
  data.set('rename_to',to);
  var f=document.createElement('form');
  f.method='post';
  f.action='/glossary/rename';
  data.forEach(function(value,key){
    var i=document.createElement('input');
    i.type='hidden';
    i.name=key;
    i.value=value;
    f.appendChild(i);
  });
  document.body.appendChild(f);
  f.submit();
}
(function(){
  var log=document.getElementById('log');
  if(log){
    if(localStorage.getItem('logOpen')!=='0'){log.open=true;}
    log.addEventListener('toggle',function(){localStorage.setItem('logOpen',log.open?'1':'0');});
    var pre=log.querySelector('pre');
    if(pre){pre.scrollTop=pre.scrollHeight;}
  }
  window.addEventListener('beforeunload',function(){sessionStorage.setItem('scrollY',String(window.scrollY));});
  var y=sessionStorage.getItem('scrollY');
  if(y){window.scrollTo(0,parseInt(y,10));}
})();
"""


def scan_progress(project):
    path = project / "scan_progress.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return data if data.get("total") else None


def scan_bar(state):
    total = state.get("total", 0)
    done = state.get("done", 0)
    percent = round(100 * done / total) if total else 0
    text = f"{done}/{total} chapter ({percent}%)"
    current = state.get("current", "")
    if current and not state.get("finished"):
        text += f" &middot; Sedang: {html.escape(current)}"
    return (
        "<section class='running'><h3>Progres scan</h3>"
        f"<div class='bar'><div class='fill' style='width:{percent}%'></div></div>"
        f"<p class='muted'>{text}</p></section>"
    )


def novel_title(stem):
    for path in (ROOT / "input").glob(f"{stem}.epub"):
        try:
            with zipfile.ZipFile(path) as archive:
                for name in archive.namelist():
                    if name.lower().endswith(".opf"):
                        text = archive.read(name).decode("utf-8", "ignore")
                        match = re.search(r"<dc:title[^>]*>([^<]+)</dc:title>", text)
                        if match:
                            return html.unescape(match.group(1)).strip()
        except (OSError, zipfile.BadZipFile):
            return None
    return None


def download_name(key, target):
    match = re.match(r"temp/(.+)_chapters/chapter-(\d+)\.(epub|docx)$", key)
    if not match:
        return target.name
    stem, number, ext = match.group(1), int(match.group(2)), match.group(3)
    title = novel_title(stem) or stem
    safe = re.sub(r'[\\/:*?"<>|]+', " ", title)
    safe = re.sub(r"\s+", " ", safe).strip()
    return f"{safe} - Chapter {number:02d}.{ext}"


def disposition(name):
    ascii_name = name.encode("ascii", "replace").decode("ascii").replace('"', "")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{url_quote(name)}"


def safe_input(value):
    path = Path(value)
    if path.parent != Path("input") or path.suffix.lower() not in INPUT_SUFFIXES:
        raise ValueError("input harus file .epub atau .docx di folder input/")
    return path


def novel_files():
    return sorted(p for p in (ROOT / "input").iterdir() if p.is_file() and p.suffix.lower() in INPUT_SUFFIXES)


def glossary_files():
    return sorted(p.name for p in (ROOT / "glossary").glob("*.txt"))


def default_glossary(input_path):
    name = f"{input_path.stem}.txt"
    return name if name in glossary_files() else "__new__"


def resolve_glossary(choice, new_name):
    if choice == "__new__":
        name = new_name.strip()
        if not GLOSSARY_NAME.match(name):
            raise ValueError("nama glosarium baru hanya huruf, angka, _ atau -")
        return f"{name}.txt"
    if choice not in glossary_files():
        raise ValueError("glosarium tidak ditemukan")
    return choice


def rename_glossary(old, new_name):
    if old not in glossary_files():
        raise ValueError("glosarium tidak ditemukan")
    name = new_name.strip()
    if not GLOSSARY_NAME.match(name):
        raise ValueError("nama baru hanya huruf, angka, _ atau -")
    target = f"{name}.txt"
    if target == old:
        return old
    if target in glossary_files():
        raise ValueError("nama itu sudah dipakai glosarium lain")
    if job_running():
        raise RuntimeError("berhenti dulu sebelum mengganti nama glosarium")
    (ROOT / "glossary" / old).rename(ROOT / "glossary" / target)
    return target


def clean_output_name(value):
    name = value.strip()
    for ext in (".epub", ".docx"):
        if name.lower().endswith(ext):
            name = name[: -len(ext)].rstrip()
    if not name:
        return ""
    if not OUTPUT_NAME.match(name) or name.startswith(".") or ".." in name or len(name) > 80:
        raise ValueError("nama file output hanya huruf, angka, spasi, _ - . ( ), maks 80 karakter")
    return name


def project_for(input_path):
    # shortcut: mt_v15 memakai folder lama temp/mt_project, novel lain punya folder sendiri
    if input_path.stem == "mt_v15":
        return Path("temp/mt_project")
    return Path(f"temp/{input_path.stem}_project")


def read_chapters(project):
    listing = project / "chapters.json"
    if not listing.exists():
        return []
    rows = []
    for item in json.loads(listing.read_text(encoding="utf-8")):
        status, done, total = "not_started", 0, 0
        progress = project / "progress" / f"{item['id']}.json"
        if progress.exists():
            data = json.loads(progress.read_text(encoding="utf-8"))
            status = data.get("status", "not_started")
            chunks = data.get("chunks", {})
            total = len(chunks)
            done = sum(1 for c in chunks.values() if c.get("qa_passed") is True)
        rows.append({"id": item["id"], "title": item["title"], "status": status, "done": done, "total": total})
    return rows


def progress_summary(rows):
    # shortcut: total chunk hanya dari chapter yang sudah punya progres; chapter yang belum mulai belum ikut
    done = sum(r["done"] for r in rows)
    total = sum(r["total"] for r in rows)
    return {
        "done": done,
        "total": total,
        "percent": round(100 * done / total) if total else 0,
        "finished": sum(1 for r in rows if r["status"] == "completed"),
        "chapters": len(rows),
        "current": next((r["title"] for r in rows if r["status"] == "in_progress"), ""),
    }


def job_running():
    return subprocess.run(["tmux", "has-session", "-t", JOB], capture_output=True).returncode == 0


def build_command(input_path, numbers, fmt, glossary_name, mode, stamp, out_name=""):
    source = quote(str(input_path))
    project = quote(str(project_for(input_path)))
    glossary = quote(f"glossary/{glossary_name}")
    if mode == "scan":
        args = f"--scan-glossary {glossary} --project-dir {project}"
    else:
        base = out_name or f"{input_path.stem}_ui_{stamp}"
        out = quote(f"temp/{base}.{fmt}")
        chapters_dir = quote(f"temp/{input_path.stem}_chapters")
        only = "" if numbers is None else " --chapter " + ",".join(str(n) for n in sorted(numbers))
        export_only = " --export-only" if mode == "export" else ""
        args = (
            f"-o {out} --project-dir {project} --export-chapters "
            f"--chapter-output-dir {chapters_dir} --glossary {glossary}{only}{export_only}"
        )
    return (
        f"cd {quote(str(ROOT))} && termux-wake-lock; "
        f"python -u main.py {source} {args} "
        f"2>&1 | tee -a {quote(str(JOB_LOG))}; echo SELESAI; sleep 3600"
    )


def start_job(input_path, numbers, fmt, glossary_name, mode, out_name=""):
    # shortcut: hanya proses dari UI ini yang terdeteksi, proses tmux lain di luar UI tidak
    if fmt not in FORMATS:
        raise ValueError("format output harus epub atau docx")
    if mode not in MODES:
        raise ValueError("mode tidak dikenal")
    if mode == "export" and not numbers:
        raise ValueError("pilih chapter yang mau diekspor")
    if mode == "translate" and numbers is not None and (not numbers or min(numbers) < 1):
        raise ValueError("pilih minimal satu chapter")
    name = clean_output_name(out_name)
    if job_running():
        raise RuntimeError("masih ada proses yang berjalan")
    JOB_LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    JOB_MODE.write_text(mode, encoding="utf-8")
    cmd = build_command(input_path, numbers, fmt, glossary_name, mode, stamp, name)
    subprocess.run(["tmux", "new-session", "-d", "-s", JOB, cmd], check=True)


def stop_job():
    subprocess.run(["tmux", "kill-session", "-t", JOB], capture_output=True)


def tail(path, lines=40):
    if not path.exists():
        return ""
    return "\n".join(path.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:])


def files():
    found = {}
    for folder in (ROOT / "temp", DOWNLOAD):
        if folder.exists():
            for f in sorted(folder.glob("*.epub")) + sorted(folder.glob("*.docx")):
                found[f"{folder.name}/{f.name}"] = f
    for folder in sorted((ROOT / "temp").glob("*_chapters")):
        for f in sorted(folder.glob("*.epub")) + sorted(folder.glob("*.docx")):
            found[f"temp/{folder.name}/{f.name}"] = f
    return found


def chapter_files(stem, number, exports):
    """Format file ekspor yang sudah ada untuk satu chapter, misalnya epub dan docx."""
    found = {}
    for fmt in FORMATS:
        key = f"temp/{stem}_chapters/chapter-{number:02d}.{fmt}"
        if key in exports:
            found[fmt] = key
    return found


def state_location(selected, choice, fmt, mode, out_name, msg):
    return (
        f"/?input={url_quote(selected)}&g={url_quote(choice)}&f={fmt}&m={mode}"
        f"&o={url_quote(out_name)}&msg={url_quote(msg)}"
    )


def page(selected="", choice="", message="", fmt="epub", mode="translate", out_name=""):
    fmt = fmt if fmt in FORMATS else "epub"
    mode = mode if mode in MODES else "translate"
    novels = novel_files()
    current = next((p for p in novels if f"input/{p.name}" == selected), novels[0] if novels else None)
    novel_options = "".join(
        f'<option value="input/{html.escape(p.name)}"{" selected" if p == current else ""}>'
        f"{html.escape(p.name)}</option>"
        for p in novels
    )
    choices = glossary_files()
    valid = choice == "__new__" or choice in choices or (choice.endswith(".txt") and GLOSSARY_NAME.match(choice[:-4]))
    if not valid:
        choice = default_glossary(current) if current else "__new__"
    options = "".join(
        f'<option value="{html.escape(name)}"{" selected" if name == choice else ""}>{html.escape(name)}</option>'
        for name in choices
    )
    if choice not in choices and choice != "__new__":
        options += f'<option value="{html.escape(choice)}" selected>{html.escape(choice)} (baru)</option>'
    options += f'<option value="__new__"{" selected" if choice == "__new__" else ""}>(glosarium baru)</option>'
    is_new = choice == "__new__"
    editor_style = "display:none" if is_new else ""
    editor = (
        f'<p><a id="editlink" style="{editor_style}" '
        f'href="/glossary?file={url_quote("glossary/" + choice)}">Edit glosarium yang dipilih</a></p>'
    )
    new_style = "" if is_new else "display:none"
    rename_style = "display:none" if is_new else ""
    stem = current.stem if current else ""
    input_param = url_quote(f"input/{current.name}") if current else ""
    rows = read_chapters(project_for(current)) if current else []
    running = job_running()
    job_mode = JOB_MODE.read_text(encoding="utf-8").strip() if JOB_MODE.exists() else ""
    exports = files()

    table = ""
    for r in rows:
        number = int(r["id"].split("_")[1])
        rid = html.escape(r["id"])
        have = chapter_files(stem, number, exports)
        have_attr = ",".join(have)
        done = r["status"] == "completed"
        checked = " checked" if not done or fmt not in have else ""
        if not done:
            file_cell = ""
        elif have:
            file_cell = " ".join(f'<a href="/file/{url_quote(have[f])}">unduh {f}</a>' for f in have)
            if fmt not in have:
                file_cell += f"<br><i class='muted'>belum ada {fmt}</i>"
        else:
            file_cell = "belum diekspor"
        if running and r["status"] == "in_progress":
            label = "<span class='spin'></span>berjalan"
        else:
            label = STATUS_TEXT.get(r["status"], r["status"])
        done_attr = "1" if done else "0"
        table += (
            f'<tr data-id="{rid}" data-done="{done_attr}" data-have="{have_attr}">'
            f'<td><input type="checkbox" name="ch" value="{rid}"{checked}></td>'
            f"<td>{html.escape(r['title'])}</td><td>{label}</td>"
            f"<td>{r['done']}/{r['total']}</td><td>{file_cell}</td></tr>"
        )
    notice = "" if rows else "<p class='muted'>Belum ada daftar chapter. Mode Terjemahkan akan memproses semua chapter yang terdeteksi.</p>"
    listing = "".join(f'<li><a href="/file/{url_quote(key)}">{html.escape(key)}</a></li>' for key in exports)

    mode_inputs = "".join(
        f'<input type="radio" id="m-{key}" name="mode" value="{key}"'
        f'{" checked" if key == mode else ""} onchange="setMode(this.value)">'
        f'<label for="m-{key}">{text}</label>'
        for key, text in MODE_LABELS
    )
    format_inputs = "".join(
        f'<input type="radio" id="f-{f}" name="fmt" value="{f}"'
        f'{" checked" if f == fmt else ""} onchange="setFormat(this.value)">'
        f'<label for="f-{f}">{f.upper()}</label>'
        for f in FORMATS
    )

    summary = progress_summary(rows)
    spinner = "<span class='spin'></span>" if running else ""
    scan_state = scan_progress(project_for(current)) if (running and job_mode == "scan" and current) else None
    if scan_state:
        progress_block = scan_bar(scan_state)
    elif rows and summary["total"] and not (running and job_mode == "scan"):
        run_class = "running" if running else ""
        current_line = (
            f"<p class='muted'>{spinner}Sedang: {html.escape(summary['current'])}</p>"
            if running and summary["current"] else ""
        )
        progress_block = (
            f"<section class='{run_class}'><h3>Progres</h3>"
            f"<div class='bar'><div class='fill' style='width:{summary['percent']}%'></div></div>"
            f"<p class='muted'>{summary['done']}/{summary['total']} chunk ({summary['percent']}%) "
            f"&middot; {summary['finished']}/{summary['chapters']} chapter selesai</p>"
            f"{current_line}</section>"
        )
    elif running:
        progress_block = (
            "<section class='running'><h3>Progres</h3>"
            f"<p class='muted'>{spinner}Menyiapkan proses...</p></section>"
        )
    else:
        progress_block = ""

    state = "berjalan" if running else "berhenti"
    state_class = "run" if running else "idle"
    dot = "<span class='dot'></span>" if running else ""
    refresh = '<meta http-equiv="refresh" content="10">' if running else ""
    disabled = " disabled" if running else ""
    status_block = (
        f"<section><p>{dot}Status proses: <span class='{state_class}'>{state}</span></p>"
        f"<p class='muted'>{html.escape(message)}</p>"
        '<form method="post" action="/stop"><button type="submit" id="stop-btn">Berhenti</button></form></section>'
    )
    files_block = (
        "<section><h3>File hasil</h3>"
        + (f"<ul>{listing}</ul>" if listing else "<p class='muted'>Belum ada file hasil.</p>")
        + "</section>"
    )
    lock = (
        "<div class='lock' onclick='toStop()'>Proses sedang berjalan.<br>"
        "Ketuk untuk menuju tombol Berhenti.</div>"
        if running else ""
    )
    outsec_style = " style='display:none'" if mode == "scan" else ""
    form_block = f"""<form method="post" action="/start" id="mainform">
<section class="wrap">{lock}
<h3>Mulai proses</h3>
<label>Novel</label>
<select name="input" onchange="go('input='+encodeURIComponent(this.value))">{novel_options}</select>
<p class="muted">Arah terjemahan: hanya Inggris ke Indonesia. Novel bahasa lain belum didukung.</p>
<label>Mode</label>
<div class="seg tri">{mode_inputs}<span class="thumb"></span></div>
<p class="muted" id="modehint">{html.escape(HINTS[mode])}</p>
<div id="outsec"{outsec_style}>
<label>Format output</label>
<div class="seg duo">{format_inputs}<span class="thumb"></span></div>
<label>Nama file output</label>
<input type="text" id="out_name" name="out_name" value="{html.escape(out_name)}" placeholder="kosong = otomatis" onkeydown="{NO_ENTER}">
<p class="muted">Berlaku untuk file hasil penuh. Nama file ekspor per chapter tidak berubah.</p>
</div>
<label>Glosarium</label>
<select name="glossary" id="gsel" onchange="pickGlossary(this.value)">{options}</select>
<div id="newg" style="{new_style}">
<input type="text" name="glossary_new" value="{html.escape(stem)}" placeholder="nama glosarium baru" onkeydown="{NO_ENTER}">
<p class="muted">Nama untuk glosarium baru. Dibuat saat proses dimulai.</p>
</div>
<div id="renamebox" style="{rename_style}">
<div class="rowbox">
<input type="text" id="rename_to" placeholder="nama baru untuk glosarium ini" onkeydown="{RENAME_KEY}">
<button type="button" onclick="renameGlossary()">Ganti nama</button>
</div>
</div>
{editor}
</section>
<section>
<h3>Chapter</h3>
{notice}
<table><tr><th></th><th>Judul</th><th>Status</th><th>Chunk</th><th>File</th></tr>{table}</table>
<button type="submit"{disabled}>Mulai</button>
</section>
</form>"""
    log_block = f'<details id="log"><summary>Log terbaru</summary><pre>{html.escape(tail(JOB_LOG))}</pre></details>'
    script = f"<script>var HINTS={json.dumps(HINTS, ensure_ascii=False)};{SCRIPT}</script>"
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}
<title>Converise EN»ID</title>
<style>{STYLE}{EXTRA_STYLE}</style>
</head><body>
<h1>Converise EN»ID</h1>
<p class="sub">Terjemahan novel Inggris ke Indonesia</p>
{status_block}
{progress_block}
{files_block}
{form_block}
{log_block}
{script}
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def _send(self, code, body, kind="text/html; charset=utf-8", extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/":
            self._send(
                200,
                page(
                    query.get("input", [""])[0],
                    query.get("g", [""])[0],
                    query.get("msg", [""])[0],
                    query.get("f", ["epub"])[0],
                    query.get("m", ["translate"])[0],
                    query.get("o", [""])[0],
                ),
            )
        elif url.path == "/glossary":
            self._send(200, glossary_page(query.get("file", [""])[0], query.get("msg", [""])[0]))
        elif url.path.startswith("/file/"):
            target = files().get(unquote(url.path[len("/file/"):]))
            if target is None:
                self._send(404, "tidak ditemukan")
            else:
                self._send(
                    200,
                    target.read_bytes(),
                    MIME.get(target.suffix.lower()[1:], "application/octet-stream"),
                    {"Content-Disposition": disposition(download_name(unquote(url.path[len("/file/"):]), target))},
                )
        else:
            self._send(404, "tidak ditemukan")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        if self.path == "/glossary/save":
            self._redirect(save_glossary(form))
            return
        selected = form.get("input", [""])[0]
        choice = form.get("glossary", ["__new__"])[0]
        fmt = form.get("fmt", ["epub"])[0]
        fmt = fmt if fmt in FORMATS else "epub"
        mode = form.get("mode", ["translate"])[0]
        mode = mode if mode in MODES else "translate"
        out_name = form.get("out_name", [""])[0]

        if self.path == "/glossary/rename":
            try:
                choice = rename_glossary(choice, form.get("rename_to", [""])[0])
                msg = f"Glosarium diganti namanya menjadi {choice}."
            except (ValueError, RuntimeError) as exc:
                msg = f"Gagal: {exc}"
            self._redirect(state_location(selected, choice, fmt, mode, out_name, msg))
            return

        try:
            if self.path == "/start":
                input_path = safe_input(selected)
                glossary_name = resolve_glossary(choice, form.get("glossary_new", [""])[0])
                rows = read_chapters(project_for(input_path))
                numbers = {int(i.split("_")[1]) for i in form.get("ch", [])} if rows else None
                start_job(input_path, numbers, fmt, glossary_name, mode, out_name)
                choice = glossary_name
                msg = "Proses dimulai."
            elif self.path == "/stop":
                stop_job()
                msg = "Proses dihentikan."
            else:
                self._send(404, "tidak ditemukan")
                return
        except (ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
            msg = f"Gagal: {exc}"
        self._redirect(state_location(selected, choice, fmt, mode, out_name, msg))


if __name__ == "__main__":
    print(f"UI: http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
