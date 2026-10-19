"""UI lokal WN Translator. Dibuka dari browser HP lewat 127.0.0.1."""

import html
import json
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shlex import quote
from urllib.parse import parse_qs, quote as url_quote, unquote, urlparse

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


def start_job(input_path, start, end):
    # shortcut: hanya proses dari UI ini yang terdeteksi, proses tmux lain di luar UI tidak
    if not 1 <= start <= end:
        raise ValueError("rentang chapter tidak valid")
    if job_running():
        raise RuntimeError("masih ada proses yang berjalan")
    project = project_for(input_path)
    JOB_LOG.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = f"temp/{input_path.stem}_ui_{stamp}.epub"
    cmd = (
        f"cd {quote(str(ROOT))} && termux-wake-lock; "
        f"python -u main.py {quote(str(input_path))} -o {quote(out)} "
        f"--project-dir {quote(str(project))} --chapter {start}-{end} "
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
    return found


def page(selected="", message=""):
    novels = sorted((ROOT / "input").glob("*.epub"))
    current = next((p for p in novels if f"input/{p.name}" == selected), novels[0] if novels else None)
    options = []
    for p in novels:
        mark = " selected" if p == current else ""
        options.append(f'<option value="input/{html.escape(p.name)}"{mark}>{html.escape(p.name)}</option>')
    rows = read_chapters(project_for(current)) if current else []
    running = job_running()
    table = ""
    for r in rows:
        label = "berjalan" if running and r["status"] == "in_progress" else STATUS_TEXT.get(r["status"], r["status"])
        table += (
            f"<tr><td>{html.escape(r['id'])}</td><td>{html.escape(r['title'])}</td>"
            f"<td>{label}</td><td>{r['done']}/{r['total']}</td></tr>"
        )
    links = "".join(
        f'<li><a href="/file/{url_quote(key)}">{html.escape(key)}</a></li>'
        for key in files()
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="10">
<title>WN Translator</title>
<style>body{{font-family:sans-serif;font-size:17px;margin:12px}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ccc;padding:4px;text-align:left}}
pre{{white-space:pre-wrap;font-size:13px;background:#f4f4f4;padding:8px}}
input,select{{font-size:17px;margin:4px 0;width:100%}}button{{font-size:17px;padding:8px 16px;margin:6px 0}}</style>
</head><body>
<h2>WN Translator</h2>
<p>Status proses: <b>{"berjalan" if running else "berhenti"}</b></p>
<p>{html.escape(message)}</p>
<form method="post" action="/start">
<label>Novel</label><select name="input" onchange="location.href='/?input='+encodeURIComponent(this.value)">{"".join(options)}</select>
<label>Chapter dari</label><input name="start" type="number" value="2" min="1">
<label>sampai</label><input name="end" type="number" value="15" min="1">
<button type="submit">Mulai</button>
</form>
<form method="post" action="/stop"><button type="submit">Berhenti</button></form>
<h3>Chapter</h3>
<table><tr><th>ID</th><th>Judul</th><th>Status</th><th>Chunk</th></tr>{table}</table>
<h3>Log terbaru</h3>
<pre>{html.escape(tail(JOB_LOG))}</pre>
<h3>File hasil</h3>
<ul>{links}</ul>
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
        if url.path == "/":
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
        selected = form.get("input", [""])[0]
        try:
            if self.path == "/start":
                start_job(safe_input(selected), int(form["start"][0]), int(form["end"][0]))
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
