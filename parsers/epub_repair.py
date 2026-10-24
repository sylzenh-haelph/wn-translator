"""Perbaikan kecil pada EPUB sumber sebelum dibangun ulang. File baru hanya dibuat kalau ada yang diperbaiki."""
import re
import sys
import zipfile
from pathlib import Path

QUOTE_PATTERN = re.compile(r'(="[^"<>\n]*?)/>')
IMG_PATTERN = re.compile(r"<img\b([^>]*?)(/?)>")
IMG_CSS = "display:block;margin:0 auto;width:100%;height:auto"


def repair_text(text):
    return QUOTE_PATTERN.subn(r'\1"/>', text)


def center_images(text):
    def fix(match):
        attrs, slash = match.group(1), match.group(2)
        if re.search(r'\sstyle="', attrs):
            attrs = re.sub(r'(\sstyle=")', r"\1" + IMG_CSS + ";", attrs, count=1)
        else:
            attrs = attrs + f' style="{IMG_CSS}"'
        return f"<img{attrs}{slash}>"

    return IMG_PATTERN.subn(fix, text)


def repair_epub(src, dst):
    fixed = 0
    changed = False
    entries = []
    with zipfile.ZipFile(src) as source:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename.lower().endswith((".xhtml", ".html", ".htm")):
                text = data.decode("utf-8", "ignore")
                repaired, count = repair_text(text)
                centered, _ = center_images(repaired)
                fixed += count
                if centered != text:
                    data = centered.encode("utf-8")
                    changed = True
            entries.append((info, data))
    if not changed:
        return 0
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in entries:
            target.writestr(info, data)
    return fixed


if __name__ == "__main__":
    print(repair_epub(sys.argv[1], sys.argv[2]))
