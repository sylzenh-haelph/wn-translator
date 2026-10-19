from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.glossary import apply_glossary, load_glossary


def test_longest_match_and_word_boundary():
    pairs = [("Dragon God", "Dewa Naga"), ("Dragon God Orsted", "Dewa Naga Orsted")]
    assert apply_glossary("Dragon God Orsted datang.", pairs) == "Dewa Naga Orsted datang."
    assert apply_glossary("Dragon Godly", pairs) == "Dragon Godly"


def test_curly_apostrophe_variant():
    pairs = [("Adventurers’ Guild", "Guild Petualang")]
    assert apply_glossary("Adventurers' Guild", pairs) == "Guild Petualang"


def test_lowercase_term_is_matched():
    pairs = [("Dragon God", "Dewa Naga")]
    assert apply_glossary("dragon god datang.", pairs) == "Dewa Naga datang."


def test_load_skips_comments_and_blank_lines(tmp_path):
    file = tmp_path / "g.txt"
    file.write_text("# komentar\n\n## Bagian\nDragon God = Dewa Naga\n# Earth = Tanah\n", encoding="utf-8")
    assert load_glossary(file) == [("Dragon God", "Dewa Naga")]
