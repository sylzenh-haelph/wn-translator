from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import AppConfig
from translation.refinement_engine import RefinementEngine


class WrongCountClient:
    def generate(self, prompt):
        return '{"translation": "x", "paragraph_translations": ["a"]}'


def test_refinement_count_mismatch_keeps_previous_translation():
    engine = RefinementEngine(WrongCountClient())
    result = engine.refine(
        text="s",
        translation="t",
        paragraph_translations=["p1", "p2"],
    )
    assert result.translation == "t"
    assert result.paragraph_translations == ["p1", "p2"]


def test_retry_defaults_reduced_by_one():
    cfg = AppConfig()
    assert cfg.max_retries == 2
    assert cfg.research_max_retries == 2
    assert cfg.qa_max_retries == 2
