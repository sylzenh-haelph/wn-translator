"""Profil gaya bicara tokoh. File ditentukan lewat WN_VOICE_FILE; tokoh yang muncul di bab ikut masuk prompt."""
import json
import os
from pathlib import Path


def load_voice_profiles(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def save_voice_profiles(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def voice_section(paragraph_texts):
    path = os.environ.get("WN_VOICE_FILE", "").strip()
    if not path:
        return ""
    profiles = load_voice_profiles(path)
    if not profiles:
        return ""
    text = " ".join(paragraph_texts).lower()
    lines = []
    for name, data in profiles.items():
        voice = str(data.get("voice", "")).strip() if isinstance(data, dict) else ""
        if voice and name.lower() in text:
            lines.append(f"- {name}: {voice}")
    if not lines:
        return ""
    return (
        "\nCHARACTER VOICE PROFILES (pakai untuk register, kata ganti, dan ciri bicara; "
        "nama tetap sesuai ENTITY RESOLUTIONS):\n" + "\n".join(lines) + "\n"
    )
