from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from types import SimpleNamespace

from research.evidence_validator import EvidenceValidator


def test_substring_is_not_a_match():
    e = SimpleNamespace(title="Rudyard Kipling", snippet="writer", url="https://a.com", source="tavily")
    assert EvidenceValidator().validate("Rudy", "character", e).valid is False


def test_whole_word_match_is_valid():
    e = SimpleNamespace(title="Rudy the Mage", snippet="a mage from Asura", url="https://a.com", source="tavily")
    assert EvidenceValidator().validate("Rudy", "character", e).valid is True
