import re

URL_ONLY = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)


def keep_source(text):
    # Paragraf tanpa huruf (separator simbol) dan paragraf yang hanya berisi URL dibiarkan seperti aslinya.
    stripped = (text or "").strip()
    if not re.search(r"[^\W\d_]", stripped):
        return True
    return bool(URL_ONLY.match(stripped))


def apply_keep(sources, translations):
    if len(sources) != len(translations):
        return list(translations)
    return [
        source if keep_source(source) else translation
        for source, translation in zip(sources, translations)
    ]
