from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import AppConfig, parse_model_chain


def test_default_translation_chain_has_backup_model():
    chain = parse_model_chain(AppConfig().translation_fallbacks)
    assert chain == [("gemini", "gemini-3.1-flash-lite"), ("gemini", "gemini-3-flash-preview")]


def test_default_research_chain_has_backup_model():
    chain = parse_model_chain(AppConfig().research_fallbacks)
    assert chain == [("gemini", "gemma-4-31b-it"), ("gemini", "gemini-3-flash-preview")]
