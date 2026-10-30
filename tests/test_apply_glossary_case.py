from translation.glossary import apply_glossary


def test_title_is_case_sensitive():
    assert apply_glossary("Lady Roxy said hi", [("Lady", "Nyonya")]) == "Nyonya Roxy said hi"
    assert apply_glossary("a lady came", [("Lady", "Nyonya")]) == "a lady came"


def test_title_with_period_keeps_name():
    assert apply_glossary("Mrs. Greyrat", [("Mrs.", "Nyonya")]) == "Nyonya Greyrat"
