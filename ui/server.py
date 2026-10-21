"""UI lokal WN Translator. Dibuka dari browser HP lewat 127.0.0.1."""

import html
import json
import re
import subprocess
import sys
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
STATUS_TEXT = {"not_started": "belum mulai", "in_progress": "belum selesai", "completed": "selesai"}
INPUT_SUFFIXES = {".epub", ".docx"}
FORMATS = ("epub", "docx")
MIME = {
    "epub": "application/epub+zip",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
GLOSSARY_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")

EXTRA_STYLE = """
progress{width:100%;height:18px;accent-color:var(--accent);margin:6px 0}
.wrap{position:relative}
.lock{position:absolute;top:0;left:0;right:0;bottom:0;z-index:2;display:flex;align-items:center;justify-content:center;text-align:center;padding:16px;background:rgba(18,18,18,.72);border-radius:10px;cursor:pointer;color:var(--fg);font-weight:bold}
button.flash{box-shadow:0 0 0 4px #f28b82}
"""

SCRIPT = """
function toStop(){
  var b=document.getElementById('stop-btn');
  if(!b){return;}
  b.scrollIntoView({behavior:'smooth',block:'center'});
  b.classList.add('flash');
  setTimeout(function(){b.classList.remove('flash');},1500);
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


def build_command(input_path, numbers, fmt, glossary_name, mode, stamp):
    source = quote(str(input_path))
    project = quote(str(project_for(input_path)))
    glossary = quote(f"glossary/{glossary_name}")
    if mode == "scan":
        args = f"--scan-glossary {glossary} --project-dir {project}"
    else:
        out = quote(f"temp/{input_path.stem}_ui_{stamp}.{fmt}")
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


def start_job(input_path, numbers, fmt, glossary_name, mode):
    # shortcut: hanya proses dari UI ini yang terdeteksi, proses tmux lain di luar UI tidak
    if fmt not in FORMATS:
        raise ValueError("format output harus epub atau docx")
    if mode == "export" and not numbers:
        raise ValueError("pilih chapter yang mau diekspor")
    if mode == "translate" and numbers is not None and (not numbers or min(numbers) < 1):
        raise ValueError("pilih minimal satu chapter")
    if job_running():
        raise RuntimeError("masih ada proses yang berjalan")
    JOB_LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    cmd = build_command(input_path, numbers, fmt, glossary_name, mode, stamp)
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


def page(selected="", choice="", message="", fmt="epub"):
    fmt = fmt if fmt in FORMATS else "epub"
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
    editor = ""
    if choice != "__new__":
        editor = f'<p><a href="/glossary?file={url_quote("glossary/" + choice)}">Edit glosarium yang dipilih</a></p>'
    stem = current.stem if current else ""
    input_param = url_quote(f"input/{current.name}") if current else ""
    rows = read_chapters(project_for(current)) if current else []
    running = job_running()
    exports = files()

    table = ""
    for r in rows:
        number = int(r["id"].split("_")[1])
        rid = html.escape(r["id"])
        have = chapter_files(stem, number, exports)
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
        label = "berjalan" if running and r["status"] == "in_progress" else STATUS_TEXT.get(r["status"], r["status"])
        table += (
            f'<tr><td><input type="checkbox" name="ch" value="{rid}"{checked}></td>'
            f"<td>{html.escape(r['title'])}</td><td>{label}</td>"
            f"<td>{r['done']}/{r['total']}</td><td>{file_cell}</td></tr>"
        )
    notice = "" if rows else "<p class='muted'>Belum ada daftar chapter. Mode Terjemahkan akan memproses semua chapter yang terdeteksi.</p>"
    listing = "".join(f'<li><a href="/file/{url_quote(key)}">{html.escape(key)}</a></li>' for key in exports)
    format_js = f"location.href='/?input={input_param}&g={url_quote(choice)}&f='+this.value"
    format_radios = "".join(
        f'<label><input type="radio" name="fmt" value="{f}"'
        f'{" checked" if f == fmt else ""} onchange="{format_js}"> {f.upper()}</label>'
        for f in FORMATS
    )

    summary = progress_summary(rows)
    if rows and summary["total"]:
        progress_block = (
            "<section><h3>Progres</h3>"
            f"<progress value='{summary['done']}' max='{summary['total']}'></progress>"
            f"<p class='muted'>{summary['done']}/{summary['total']} chunk ({summary['percent']}%) &middot; "
            f"{summary['finished']}/{summary['chapters']} chapter selesai</p>"
            + (f"<p class='muted'>Sedang: {html.escape(summary['current'])}</p>" if summary["current"] else "")
            + "</section>"
        )
    elif running:
        progress_block = "<section><h3>Progres</h3><p class='muted'>Menyiapkan proses...</p></section>"
    else:
        progress_block = ""

    state = "berjalan" if running else "berhenti"
    state_class = "run" if running else "idle"
    refresh = '<meta http-equiv="refresh" content="10">' if running else ""
    status_block = (
        f"<section><p>Status proses: <span class='{state_class}'>{state}</span></p>"
        f"<p class='muted'>{html.escape(message)}</p>"
        '<form method="post" action="/stop"><button type="submit" id="stop-btn">Berhenti</button></form></section>'
    )
    files_block = (
        "<section><h3>File hasil</h3>"
        + (f"<ul>{listing}</ul>" if listing else "<p class='muted'>Belum ada file hasil.</p>")
        + "</section>"
    )
    lock = (
        "<div class='lock' onclick='toStop()'>Proses sedang berjalan.<br>Tekan Berhenti dulu untuk mengubah pilihan.</div>"
        if running else ""
    )
    form_block = f"""<div class="wrap">{lock}<form method="post" action="/start">
<section>
<h3>Mulai proses</h3>
<label>Novel</label>
<select name="input" onchange="location.href='/?input='+encodeURIComponent(this.value)">{novel_options}</select>
<p class="muted">Arah terjemahan: hanya Inggris ke Indonesia. Novel bahasa lain belum didukung.</p>
<label>Mode</label>
<div class="opt">
<label><input type="radio" name="mode" value="translate" checked> Terjemahkan</label>
<label><input type="radio" name="mode" value="export"> Ekspor chapter selesai (tanpa menerjemahkan)</label>
<label><input type="radio" name="mode" value="scan"> Scan glosarium saja</label>
</div>
<label>Format hasil</label>
<div class="opt">{format_radios}</div>
<label>Glosarium</label>
<select name="glossary" onchange="location.href='/?input={input_param}&f={fmt}&g='+encodeURIComponent(this.value)">{options}</select>
<input type="text" name="glossary_new" value="{html.escape(stem)}" placeholder="nama glosarium baru">
{editor}
</section>
<section>
<h3>Chapter</h3>
{notice}
<table><tr><th></th><th>Judul</th><th>Status</th><th>Chunk</th><th>File</th></tr>{table}</table>
<button type="submit">Mulai</button>
</section>
</form></div>"""
    log_block = f'<details id="log"><summary>Log terbaru</summary><pre>{html.escape(tail(JOB_LOG))}</pre></details>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}
<title>WN Translator</title>
<style>{STYLE}{EXTRA_STYLE}</style>
</head><body>
<h1>WN Translator</h1>
{status_block}
{progress_block}
{files_block}
{form_block}
{log_block}
<script>{SCRIPT}</script>
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
                    {"Content-Disposition": f'attachment; filename="{target.name}"'},
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
        try:
            if self.path == "/start":
                input_path = safe_input(selected)
                glossary_name = resolve_glossary(choice, form.get("glossary_new", [""])[0])
                mode = form.get("mode", ["translate"])[0]
                if mode not in ("translate", "export", "scan"):
                    raise ValueError("mode tidak dikenal")
                rows = read_chapters(project_for(input_path))
                numbers = {int(i.split("_")[1]) for i in form.get("ch", [])} if rows else None
                start_job(input_path, numbers, fmt, glossary_name, mode)
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
        self._redirect(
            f"/?input={url_quote(selected)}&g={url_quote(choice)}&f={fmt}&msg={url_quote(msg)}"
        )


if __name__ == "__main__":
    print(f"UI: http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
