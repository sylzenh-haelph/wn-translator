from dataclasses import dataclass


@dataclass
class EntityCandidate:
    text: str
    entity_type: str
    source_paragraph_id: str
    reason: str


COMMON_WORDS = {
    "The",
    "A",
    "An",
    "And",
    "But",
    "Or",
    "So",
    "Then",
    "This",
    "That",
    "These",
    "Those",
    "He",
    "She",
    "They",
    "It",
    "His",
    "Her",
    "Their",
    "Wait",
    "Story",
    "Highlights",
    "Entity",
    "Variations",
    "Standard",
    "Text",
    "Formatted",
}


TITLE_WORDS = {
    "King",
    "Queen",
    "Prince",
    "Princess",
    "Lord",
    "Lady",
    "Sir",
    "Saint",
    "General",
    "Captain",
    "Professor",
    "Doctor",
    "Master",
    "Miss",
    "Mrs",
    "Mr",
}


def _clean_word(word):
    return word.strip(
        " \t\n\r.,!?;:()[]{}\"'“”‘’"
    )


def _is_capitalized_word(word):
    word = _clean_word(word)

    if not word:
        return False

    return (
        word[0].isupper()
        and any(character.isalpha() for character in word)
    )


def _is_possible_name(word):
    word = _clean_word(word)

    if not _is_capitalized_word(word):
        return False

    if word in COMMON_WORDS:
        return False

    return True


def _detect_title_entities(words):
    results = []

    index = 0

    while index < len(words):
        title = _clean_word(words[index])

        if title not in TITLE_WORDS:
            index += 1
            continue

        if index + 1 >= len(words):
            index += 1
            continue

        name = _clean_word(words[index + 1])

        if not _is_possible_name(name):
            index += 1
            continue

        results.append(
            {
                "start": index,
                "end": index + 2,
                "text": f"{title} {name}",
                "entity_type": "character",
                "reason": "title_before_name",
            }
        )

        index += 2

    return results


def _detect_multiword_entities(words, occupied):
    results = []

    index = 0

    while index < len(words):
        if index in occupied:
            index += 1
            continue

        word = _clean_word(words[index])

        if not _is_possible_name(word):
            index += 1
            continue

        next_index = index + 1
        sequence = [word]

        while next_index < len(words):
            if next_index in occupied:
                break

            next_word = _clean_word(words[next_index])

            if not _is_possible_name(next_word):
                break

            sequence.append(next_word)
            next_index += 1

        if len(sequence) >= 2:
            results.append(
                {
                    "start": index,
                    "end": next_index,
                    "text": " ".join(sequence),
                    "entity_type": "candidate",
                    "reason": "capitalized_sequence",
                }
            )

            for position in range(index, next_index):
                occupied.add(position)

            index = next_index
        else:
            index += 1

    return results


def _detect_single_word_entities(words, occupied):
    results = []

    for index, raw_word in enumerate(words):
        if index in occupied:
            continue

        word = _clean_word(raw_word)

        if not _is_possible_name(word):
            continue

        results.append(
            {
                "start": index,
                "end": index + 1,
                "text": word,
                "entity_type": "candidate",
                "reason": "capitalized_word",
            }
        )

        occupied.add(index)

    return results


def _detect_paragraph_entities(text):
    words = text.split()

    if not words:
        return []

    results = []

    occupied = set()

    title_entities = _detect_title_entities(words)

    for entity in title_entities:
        results.append(entity)

        for position in range(
            entity["start"],
            entity["end"],
        ):
            occupied.add(position)

    multiword_entities = _detect_multiword_entities(
        words,
        occupied,
    )

    results.extend(multiword_entities)

    single_word_entities = _detect_single_word_entities(
        words,
        occupied,
    )

    results.extend(single_word_entities)

    results.sort(
        key=lambda entity: entity["start"]
    )

    return results


def detect_entities(document):
    candidates = []

    seen = set()

    for paragraph in document.paragraphs:
        text = paragraph.text

        if not text.strip():
            continue

        detected = _detect_paragraph_entities(text)

        for entity in detected:
            text_value = entity["text"]
            key = text_value.lower()

            if key in seen:
                continue

            seen.add(key)

            candidates.append(
                EntityCandidate(
                    text=text_value,
                    entity_type=entity["entity_type"],
                    source_paragraph_id=paragraph.id,
                    reason=entity["reason"],
                )
            )

    return candidates
