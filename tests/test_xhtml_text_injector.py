from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reconstruction.xhtml_text_injector import (
    inject_xhtml_text,
)


def main():
    html = """\
<html>
<head>
  <title>Test</title>
</head>
<body>
  <div class="scene" id="scene-1">
    <p class="narration">
      Alice entered the room.
      <strong>Very quietly.</strong>
    </p>

    <blockquote>
      <p>
        Marcus said something.
        <em>Then he smiled.</em>
      </p>
    </blockquote>
  </div>
</body>
</html>
"""

    result = inject_xhtml_text(
        html,
        ["p0000", "p0001"],
        {
            "p0000": "Alice memasuki ruangan.",
            "p0001": "Marcus mengatakan sesuatu.",
        },
    )

    # Struktur HTML tetap ada.
    assert '<div class="scene"' in result
    assert 'id="scene-1"' in result
    assert "<blockquote>" in result
    assert '<p class="narration">' in result

    # Elemen formatting tetap ada.
    assert "<strong>" in result
    assert "<em>" in result

    # Teks terjemahan masuk.
    assert "Alice memasuki ruangan." in result
    assert "Marcus mengatakan sesuatu." in result

    # Teks sumber tidak boleh tersisa.
    assert "Alice entered the room." not in result
    assert "Marcus said something." not in result

    # Text node lama di dalam markup juga harus dibersihkan.
    assert "Very quietly." not in result
    assert "Then he smiled." not in result

    print("PASS: XHTML text injection")


if __name__ == "__main__":
    main()
