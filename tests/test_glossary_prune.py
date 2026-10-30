from translation.glossary import prune_scan_names


def test_honorific_and_title_variants_collapse_to_plain_name():
    kept = prune_scan_names([("Subaru", "orang"), ("Subaru-kun", "orang"), ("Mr. Subaru", "orang")], [])
    assert [name for name, _ in kept] == ["Subaru"]


def test_existing_name_blocks_honorific_variant():
    assert prune_scan_names([("Subaru-san", "orang")], ["Subaru"]) == []


def test_longer_name_replaces_shorter_part():
    kept = prune_scan_names([("Natsuki Subaru", "orang"), ("Subaru", "orang")], [])
    assert [name for name, _ in kept] == ["Natsuki Subaru"]
