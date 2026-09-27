import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bs4 import BeautifulSoup
from reconstruction.xhtml_text_injector import inject_xhtml_text


def main():
    html = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<style>.important { font-weight: bold; }</style>
</head>
<body>
<p id="p1">Hello <strong class="important">world</strong>!</p>
<p id="p2"><em>Important</em> text <u>here</u>.</p>
<p id="p3">Normal <span data-test="keep">text</span>.</p>
</body>
</html>
"""

    translations = {
        "p1": "Halo dunia yang penting!",
        "p2": "Teks ini sangat penting.",
        "p3": "Teks normal yang dipertahankan.",
    }

    result = inject_xhtml_text(
        html,
        ["p1", "p2", "p3"],
        translations,
    )

    soup = BeautifulSoup(result, "html.parser")

    # ============================================================
    # 1. Semua paragraph tetap ada
    # ============================================================

    paragraphs = soup.find_all("p")

    assert len(paragraphs) == 3

    # ============================================================
    # 2. Hasil terjemahan harus menjadi isi masing-masing paragraph
    # ============================================================

    for paragraph_id, expected_text in translations.items():
        paragraph = soup.find("p", id=paragraph_id)

        assert paragraph is not None
        assert paragraph.get_text() == expected_text

    # ============================================================
    # 3. Struktur inline formatting harus tetap ada
    # ============================================================

    strong = soup.find("strong")
    em = soup.find("em")
    underline = soup.find("u")
    span = soup.find("span")

    assert strong is not None
    assert em is not None
    assert underline is not None
    assert span is not None

    # ============================================================
    # 4. Atribut inline harus tetap dipertahankan
    # ============================================================

    assert strong.get("class") == ["important"]
    assert span.get("data-test") == "keep"

    # ============================================================
    # 5. Elemen formatting tetap memiliki text
    # ============================================================

    assert strong.get_text() != ""
    assert em.get_text() != ""
    assert underline.get_text() != ""
    assert span.get_text() != ""

    # ============================================================
    # 6. Teks sumber tidak boleh tersisa
    # ============================================================

    assert "Hello" not in result
    assert "world" not in result
    assert "Important" not in result

    print("PASS: XHTML inline formatting preservation")


if __name__ == "__main__":
    main()
