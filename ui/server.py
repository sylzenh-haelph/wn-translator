"""UI lokal WN Translator. Dibuka dari browser HP lewat 127.0.0.1."""

import html
import json
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shlex import quote
from urllib.parse import parse_qs, quote as url_quote, unquote, urlparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.glossary_page import glossary_page, save_glossary  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8765
JOB = "wn_ui_job"
DOWNLOAD = Path("/storage/emulated/0/Download")
JOB_LOG = ROOT / "temp" / "ui_job.log"
STATUS_TEXT = {"not_started": "belum mulai", "in_progress": "belum selesai", "completed": "selesai"}


def safe_input(value):
    path = Path(value)
    if path.parent != Path("input") or path.suffix.lower() != ".epub":
        raise ValueError("input harus file .epub di folder input/")
    return path


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


def job_running():
    return subprocess.run(["tmux", "has-session", "-t", JOB], capture_output=True).returncode == 0


def start_job(input_path, numbers):
    # shortcut: hanya proses dari UI ini yang terdeteksi, proses tmux lain di luar UI tidak
    if numbers is not None and (not numbers or min(numbers) < 1):
        raise ValueError("pilih minimal satu chapter")
    if job_running():
        raise RuntimeError("masih ada proses yang berjalan")
    project = project_for(input_path)
    JOB_LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = f"temp/{input_path.stem}_ui_{stamp}.epub"
    chapter_dir = f"temp/{input_path.stem}_chapters"
    glossary = f"glossary/{input_path.stem}.txt"
    only = "" if numbers is None else " --chapter " + ",".join(str(n) for n in sorted(numbers))
    cmd = (
        f"cd {quote(str(ROOT))} && termux-wake-lock; "
        f"python -u main.py {quote(str(input_path))} -o {quote(out)} "
        f"--project-dir {quote(str(project))} --export-chapters "
        f"--glossary {quote(glossary)} "
        f"--chapter-output-dir {quote(chapter_dir)}{only} "
        f"2>&1 | tee -a {quote(str(JOB_LOG))}; echo SELESAI; sleep 3600"
    )
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
            for f in sorted(folder.glob("*.epub")):
                found[f"{folder.name}/{f.name}"] = f
    for folder in sorted((ROOT / "temp").glob("*_chapters")):
        for f in sorted(folder.glob("*.epub")):
            found[f"temp/{folder.name}/{f.name}"] = f
    return found


def page(selected="", message=""):
    novels = sorted((ROOT / "input").glob("*.epub"))
    current = next((p for p in novels if f"input/{p.name}" == selected), novels[0] if novels else None)
    options = "".join(
        f'<option value="input/{html.escape(p.name)}"{" selected" if p == current else ""}>'
        f"{html.escape(p.name)}</option>"
        for p in novels
    )
    rows = read_chapters(project_for(current)) if current else []
    running = job_running()
    exports = files()
    glossary_href = url_quote(f"glossary/{current.stem}.txt") if current else ""
    table = ""
    for r in rows:
        number = int(r["id"].split("_")[1])
        rid = html.escape(r["id"])
        checked = "" if r["status"] == "completed" else " checked"
        key = f"temp/{current.stem}_chapters/chapter-{number:02d}.epub"
        if r["status"] != "completed":
            file_cell = ""
        elif key in exports:
            file_cell = f'<a href="/file/{url_quote(key)}">unduh</a>'
        else:
            file_cell = "belum diekspor"
        label = "berjalan" if running and r["status"] == "in_progress" else STATUS_TEXT.get(r["status"], r["status"])
        table += (
            f'<tr><td><input type="checkbox" name="ch" value="{rid}"{checked}></td>'
            f"<td>{html.escape(r['title'])}</td><td>{label}</td>"
            f"<td>{r['done']}/{r['total']}</td><td>{file_cell}</td></tr>"
        )
    notice = "" if rows else "<p>Belum ada daftar chapter. Tekan Mulai untuk memproses semua chapter yang terdeteksi.</p>"
    listing = "".join(f'<li><a href="/file/{url_quote(key)}">{html.escape(key)}</a></li>' for key in exports)
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="10">
<title>WN Translator</title>
<style>body{{font-family:sans-serif;font-size:17px;margin:12px}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:4px;text-align:left}}
pre{{white-space:pre-wrap;font-size:13px;background:#f4f4f4;padding:8px}}
select{{font-size:17px;margin:4px 0;width:100%}}button{{font-size:17px;padding:8px 16px;margin:6px 0}}</style>
</head><body>
<h2>WN Translator</h2>
<p>Status proses: <b>{"berjalan" if running else "berhenti"}</b></p>
<p>{html.escape(message)}</p>
<form method="post" action="/start">
<label>Novel</label>
<select name="input" onchange="location.href='/?input='+encodeURIComponent(this.value)">{options}</select>
<p><a href="/glossary?file={glossary_href}">Edit glosarium novel ini</a></p>
{notice}
<table><tr><th></th><th>Judul</th><th>Status</th><th>Chunk</th><th>File</th></tr>{table}</table>
<button type="submit">Mulai</button>
</form>
<form method="post" action="/stop"><button type="submit">Berhenti</button></form>
<h3>Log terbaru</h3>
<pre>{html.escape(tail(JOB_LOG))}</pre>
<h3>File hasil</h3>
<ul>{listing}</ul>
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
        if url.path == "/glossary":
            query = parse_qs(url.query)
            self._send(200, glossary_page(query.get("file", [""])[0], query.get("msg", [""])[0]))
        elif url.path == "/":
            query = parse_qs(url.query)
            selected = query.get("input", [""])[0]
            self._send(200, page(selected, query.get("msg", [""])[0]))
        elif url.path.startswith("/file/"):
            target = files().get(unquote(url.path[len("/file/"):]))
            if target is None:
                self._send(404, "tidak ditemukan")
            else:
                self._send(
                    200,
                    target.read_bytes(),
                    "application/epub+zip",
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
        try:
            if self.path == "/start":
                input_path = safe_input(selected)
                rows = read_chapters(project_for(input_path))
                numbers = {int(i.split("_")[1]) for i in form.get("ch", [])} if rows else None
                start_job(input_path, numbers)
                msg = "Proses dimulai."
            elif self.path == "/stop":
                stop_job()
                msg = "Proses dihentikan."
            else:
                self._send(404, "tidak ditemukan")
                return
        except (ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as exc:
            msg = f"Gagal: {exc}"
        self._redirect(f"/?input={url_quote(selected)}&msg={url_quote(msg)}")


if __name__ == "__main__":
    print(f"UI: http://{HOST}:{PORT}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
