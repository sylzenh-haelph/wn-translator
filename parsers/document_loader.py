from pathlib import Path

from parsers.docx_parser import parse_docx
from parsers.epub_parser import parse_epub


SUPPORTED_EXTENSIONS = {
    ".epub",
    ".docx",
}


def load_document(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"File tidak ditemukan: {path}"
        )

    extension = path.suffix.lower()

    if extension == ".epub":
        return parse_epub(path)

    if extension == ".docx":
        return parse_docx(path)

    supported = ", ".join(
        sorted(SUPPORTED_EXTENSIONS)
    )

    raise ValueError(
        f"Format tidak didukung: {extension}. "
        f"Format yang didukung: {supported}"
    )
