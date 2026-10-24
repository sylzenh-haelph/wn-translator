"""Riset gaya bicara tokoh lewat Tavily, dirangkum model, dan disimpan per glosarium (dipakai ulang untuk seri yang sama)."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from translation.model_client import extract_json
from translation.voice_profiles import load_voice_profiles, save_voice_profiles

SUMMARY_PROMPT = (
    "Kamu merangkum gaya bicara tokoh fiksi dari cuplikan web. "
    "Tulis dalam bahasa Indonesia, maksimal 40 kata: register (formal atau kasual), "
    "kata ganti yang biasa dipakai, dan ciri bicara yang khas. "
    "Jangan menyalin kalimat dari sumber. "
    "Kalau cuplikan tidak membahas gaya bicara tokoh ini, kembalikan voice kosong. "
    'Jawab HANYA JSON: {"voice": "..."}'
)

QUOTE = re.compile(r'[“"”]')
SPEAKER = re.compile(r"^\s*([A-Z][\w'’\-]*(?:\s+[A-Z][\w'’\-]*){0,2})\s*:\s*[\[\"“‘'(]")
WEAK_MIN = 5


def voice_query(name, novel_title=""):
    query = f'"{name}" personality speech dialogue'
    if novel_title:
        query += f' "{novel_title}"'
    return query


def collect_characters(obj):
    found = []

    def walk(value, key=None):
        if isinstance(value, dict):
            kind = value.get("entity_type") or value.get("type")
            name = None
            for field in ("text", "name", "entity", "canonical"):
                candidate = value.get(field)
                if isinstance(candidate, str) and candidate.strip():
                    name = candidate.strip()
                    break
            if kind == "character":
                if name:
                    found.append(name)
                elif isinstance(key, str) and key.strip():
                    found.append(key.strip())
            for child_key, child in value.items():
                walk(child, child_key)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(obj)
    return list(dict.fromkeys(found))


def _name_forms(name):
    forms = [name]
    first = name.split()[0]
    if len(first) >= 4 and first.lower() != name.lower():
        forms.append(first)
    return forms


def _matches(name, text):
    return any(
        re.search(rf"\b{re.escape(form)}\b", text, re.IGNORECASE)
        for form in _name_forms(name)
    )


def speaker_score(name, paragraphs):
    strong = 0
    weak = 0
    for text in paragraphs:
        match = SPEAKER.match(text)
        if match and _matches(name, match.group(1)):
            strong += 1
        elif QUOTE.search(text) and _matches(name, text):
            weak += 1
    return strong, weak


def filter_speakers(names, paragraphs, weak_min=WEAK_MIN):
    kept, dropped = [], []
    for name in names:
        strong, weak = speaker_score(name, paragraphs)
        if strong >= 1 or weak >= weak_min:
            kept.append(name)
        else:
            dropped.append(name)
    return kept, dropped


def summarize_voice(client, name, results):
    snippets = "\n".join(
        f"- {item.title}: {item.snippet[:400]}"
        for item in results[:5]
        if getattr(item, "snippet", "")
    )
    if not snippets:
        return ""
    prompt = SUMMARY_PROMPT + f"\n\nTOKOH: {name}\n\nSUMBER:\n{snippets}\n"
    try:
        data = extract_json(client.generate(prompt))
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("voice", "")).strip()[:400]


def research_voices(names, provider, client, path, novel_title=""):
    profiles = load_voice_profiles(path)
    added = 0
    for name in names:
        if name in profiles:
            continue
        results = provider.search(voice_query(name, novel_title), max_results=5)
        voice = summarize_voice(client, name, results)
        profiles[name] = {"voice": voice, "checked": True}
        if voice:
            added += 1
        save_voice_profiles(path, profiles)
    return added


def main(argv=None):
    from config.settings import load_config
    from main import parse_document
    from research.research_provider import TavilyResearchProvider
    from translation.runtime import build_failover_client

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--profiles", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args(argv)

    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("TAVILY_API_KEY belum diset. Gaya bicara butuh pencarian web.")

    entities_file = Path(args.project_dir) / "research_data" / "entities.json"
    if not entities_file.exists():
        raise SystemExit("Belum ada daftar entitas. Jalankan Scan glosarium dulu untuk novel ini.")
    names = collect_characters(json.loads(entities_file.read_text(encoding="utf-8")))

    document = parse_document(Path(args.input))
    paragraphs = ["".join(run.text for run in p.runs) for p in document.paragraphs]
    kept, dropped = filter_speakers(names, paragraphs)
    print(
        f"tokoh ditemukan: {len(names)} | punya dialog: {len(kept)} | hanya disebut: {len(dropped)}",
        flush=True,
    )
    if dropped:
        print("dilewati (hanya disebut di narasi): " + ", ".join(dropped[:30]), flush=True)

    config = load_config(project_dir=Path(args.project_dir))
    client = build_failover_client(
        config,
        role="Research",
        primary_provider=config.research_provider,
        primary_model=config.research_model,
        fallbacks=config.research_fallbacks,
        max_retries=config.research_max_retries,
        timeout=config.research_timeout,
    )
    provider = TavilyResearchProvider(
        api_key=api_key,
        timeout=config.research_timeout,
        max_retries=config.research_max_retries,
    )
    added = research_voices(kept, provider, client, args.profiles, args.title)
    print(f"profil gaya bicara baru: {added}", flush=True)


if __name__ == "__main__":
    main()
