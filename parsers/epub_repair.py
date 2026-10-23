"""Perbaikan kecil pada EPUB sumber: tanda kutip atribut yang hilang sebelum '/>'."""
import re
import sys
import zipfile
from pathlib import Path

PATTERN = re.compile(r'(="[^"<>\n]*?)/>')


def repair_text(text):
    return PATTERN.subn(r'\1"/>', text)


def repair_epub(src, dst):
    fixed = 0
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as source, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.lower().endswith((".xhtml", ".html", ".htm")):
                text = data.decode("utf-8", "ignore")
                repaired, count = repair_text(text)
                if count:
                    fixed += count
                    data = repaired.encode("utf-8")
            target.writestr(info, data)
    return fixed


if __name__ == "__main__":
    print(repair_epub(sys.argv[1], sys.argv[2]))
