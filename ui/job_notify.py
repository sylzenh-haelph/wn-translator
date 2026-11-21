"""Notifikasi job WN Translator: teks dan pengiriman ke Termux."""
import json
import subprocess
import sys
from pathlib import Path

NAMES = {"translate": "Forge", "scan": "Radar"}


def label(mode):
    return NAMES.get(mode, mode)


def duration_text(seconds):
    seconds = int(float(seconds or 0))
    hours, rest = divmod(seconds, 3600)
    minutes = rest // 60
    if hours:
        return f"{hours} jam {minutes} mnt"
    if minutes:
        return f"{minutes} mnt"
    return f"{seconds} dtk"


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def forge_facts(project):
    listing = _read_json(project / "chapters.json") or []
    statuses = []
    for item in listing:
        data = _read_json(project / "progress" / f"{item['id']}.json") or {}
        statuses.append(data.get("status", "not_started"))
    stats = _read_json(project / "stats" / "translation_stats.json") or {}
    return {
        "total": len(listing),
        "done": statuses.count("completed"),
        "stuck": statuses.count("in_progress"),
        "duration": stats.get("duration_seconds"),
    }


def radar_facts(project):
    data = _read_json(project / "scan_progress.json") or {}
    return {"total": data.get("total", 0), "done": data.get("done", 0)}


def build_message(mode, code, project, novel, output=""):
    name = label(mode)
    lines = [novel] if novel else []
    if mode == "scan":
        facts = radar_facts(project)
        lines.append(f"{facts['done']}/{facts['total']} chapter dipindai")
        high = code != 0
        title = f"{name} berhenti dengan error" if code != 0 else f"{name} selesai"
    else:
        facts = forge_facts(project)
        lines.append(f"{facts['done']}/{facts['total']} chapter selesai")
        if facts["duration"]:
            lines.append(f"Waktu: {duration_text(facts['duration'])}")
        if facts["stuck"]:
            lines.append(f"{facts['stuck']} chapter perlu diulang (lihat UI)")
        if output and output != "-" and Path(output).exists():
            lines.append(f"File: {Path(output).name}")
        if code != 0:
            title = f"{name} berhenti dengan error"
        elif facts["stuck"]:
            title = f"{name} selesai, ada chapter gagal"
        else:
            title = f"{name} selesai"
        high = code != 0 or facts["stuck"] > 0
    return title, "\n".join(lines), high


def send(title, content="", ongoing=False, high=False):
    args = ["termux-notification", "--id", "wn_job", "--group", "wn_translator",
            "--title", title, "--content", content or " "]
    if ongoing:
        args.append("--ongoing")
    if high:
        args += ["--priority", "high"]
    try:
        subprocess.run(args, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass


def main(argv):
    # python -m ui.job_notify done <mode> <code> <project> <novel> [output]
    if len(argv) < 6 or argv[1] != "done":
        return 0
    mode, code, project, novel = argv[2], argv[3], Path(argv[4]), argv[5]
    output = argv[6] if len(argv) > 6 else ""
    try:
        code_value = int(code)
    except ValueError:
        code_value = 1
    title, content, high = build_message(mode, code_value, project, novel, output)
    send(title, content, high=high)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
