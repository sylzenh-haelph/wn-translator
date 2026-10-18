from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reconstruction.xhtml_text_injector import inject_xhtml_text


def test_heading_with_line_break_is_not_split_inside_word():
    html = "<html><body><p>Chapter 8<br/>Quagmire vs. Dragon God</p></body></html>"
    out = inject_xhtml_text(html, ["p1"], {"p1": "Bab 8\u241eQuagmire vs. Dewa Naga"}, None)
    assert "Bab 8\u241eQuagmire vs. Dewa Naga" in out
    assert "Qu<br" not in out


def test_blank_source_paragraph_keeps_its_space():
    html = "<html><body><p>&nbsp;</p><p>Satu</p></body></html>"
    out = inject_xhtml_text(html, ["p1", "p2"], {"p1": "", "p2": "Dua"}, None)
    assert "\u00a0" in out
    assert "Dua" in out
