from translation.chapter_title_translator import ChapterTitleTranslator


class FakeClient:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt):
        return self.response


def test_valid_translation():
    client = FakeClient(
        '{"title": "Chapter 1: The Gate (Gerbang)"}'
    )

    translator = ChapterTitleTranslator(client)

    result = translator.translate(
        "Chapter 1: The Gate"
    )

    assert result == "Chapter 1: The Gate (Gerbang)"


def test_number_must_be_preserved():
    client = FakeClient(
        '{"title": "Chapter 2: The Silver Sword (Pedang Perak)"}'
    )

    translator = ChapterTitleTranslator(client)

    result = translator.translate(
        "Chapter 2: The Silver Sword"
    )

    assert result == (
        "Chapter 2: The Silver Sword (Pedang Perak)"
    )


def test_invalid_number_is_rejected():
    client = FakeClient(
        '{"title": "Chapter 3: The Gate (Gerbang)"}'
    )

    translator = ChapterTitleTranslator(client)

    try:
        translator.translate("Chapter 1: The Gate")
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Nomor chapter yang berubah harus ditolak."
        )


def test_missing_indonesian_translation_is_rejected():
    client = FakeClient(
        '{"title": "Chapter 1: The Gate"}'
    )

    translator = ChapterTitleTranslator(client)

    try:
        translator.translate("Chapter 1: The Gate")
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Judul tanpa terjemahan Indonesia harus ditolak."
        )


def test_chapter_label_must_remain_chapter():
    client = FakeClient(
        '{"title": "Bab 1: The Gate (Gerbang)"}'
    )

    translator = ChapterTitleTranslator(client)

    try:
        translator.translate("Chapter 1: The Gate")
    except ValueError:
        pass
    else:
        raise AssertionError(
            "'Chapter' tidak boleh berubah menjadi 'Bab'."
        )


class ExplodingClient:
    def generate(self, prompt):
        raise AssertionError(
            "Model tidak boleh dipanggil untuk label chapter saja."
        )


def test_label_only_title_skips_model():
    translator = ChapterTitleTranslator(ExplodingClient())

    assert translator.translate("Chapter 1") == "Chapter 1 (Bab 1)"


def test_echoed_chapter_label_is_rejected():
    client = FakeClient(
        '{"title": "Chapter 1: The Gate (Chapter 1)"}'
    )

    translator = ChapterTitleTranslator(client)

    try:
        translator.translate("Chapter 1: The Gate")
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Label chapter yang diulang harus ditolak."
        )


class ExplodingClient:
    def generate(self, prompt):
        raise AssertionError(
            "Model tidak boleh dipanggil untuk label chapter saja."
        )


def test_label_only_title_skips_model():
    translator = ChapterTitleTranslator(ExplodingClient())

    assert translator.translate("Chapter 1") == "Chapter 1 (Bab 1)"


def test_echoed_chapter_label_is_rejected():
    client = FakeClient(
        '{"title": "Chapter 1: The Gate (Chapter 1)"}'
    )

    translator = ChapterTitleTranslator(client)

    try:
        translator.translate("Chapter 1: The Gate")
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Label chapter yang diulang harus ditolak."
        )


if __name__ == "__main__":
    test_valid_translation()
    test_number_must_be_preserved()
    test_invalid_number_is_rejected()
    test_missing_indonesian_translation_is_rejected()
    test_chapter_label_must_remain_chapter()

    print("CHAPTER TITLE TRANSLATOR TEST: PASS")
