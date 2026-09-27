from bs4 import BeautifulSoup, NavigableString


class XHTMLTextInjector:
    """
    Replace paragraph text while preserving the existing inline XHTML
    structure and attributes.

    Also supports updating the XHTML <title> element separately.
    """

    INLINE_TAGS = {
        "a",
        "abbr",
        "b",
        "bdi",
        "bdo",
        "cite",
        "code",
        "del",
        "dfn",
        "em",
        "i",
        "ins",
        "kbd",
        "mark",
        "q",
        "s",
        "samp",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "time",
        "u",
        "var",
    }

    def inject(
        self,
        html,
        paragraph_ids,
        paragraph_texts,
        title_text=None,
    ):
        soup = BeautifulSoup(html, "html.parser")

        targets = soup.find_all(
            ["p", "h1", "h2", "h3", "h4", "h5", "h6"]
        )

        if len(targets) != len(paragraph_ids):
            raise ValueError(
                "Jumlah elemen XHTML tidak cocok dengan paragraph IDs: "
                f"{len(targets)} != {len(paragraph_ids)}"
            )

        for tag, paragraph_id in zip(targets, paragraph_ids):
            if paragraph_id not in paragraph_texts:
                raise ValueError(
                    f"Tidak ada hasil terjemahan untuk paragraph ID: "
                    f"{paragraph_id}"
                )

            translated_text = paragraph_texts[paragraph_id]

            self._replace_text_preserving_structure(
                tag,
                translated_text,
            )

        if title_text is not None:
            title_tag = soup.find("title")

            if title_tag is not None:
                title_tag.clear()
                title_tag.append(title_text)

        return str(soup)

    @classmethod
    def _replace_text_preserving_structure(
        cls,
        paragraph_tag,
        translated_text,
    ):
        text_nodes = [
            node
            for node in paragraph_tag.descendants
            if isinstance(node, NavigableString)
        ]

        if not text_nodes:
            paragraph_tag.append(translated_text)
            return

        if len(text_nodes) == 1:
            text_nodes[0].replace_with(translated_text)
            return

        source_lengths = [
            len(str(node))
            for node in text_nodes
        ]

        total_source_length = sum(source_lengths)

        if total_source_length == 0:
            text_nodes[0].replace_with(translated_text)

            for node in text_nodes[1:]:
                node.replace_with("")

            return

        allocations = cls._allocate_text(
            translated_text,
            source_lengths,
        )

        for node, replacement in zip(
            text_nodes,
            allocations,
        ):
            node.replace_with(replacement)

    @staticmethod
    def _allocate_text(text, source_lengths):
        if not source_lengths:
            return []

        if len(source_lengths) == 1:
            return [text]

        total = sum(source_lengths)

        if total <= 0:
            result = [""] * len(source_lengths)
            result[0] = text
            return result

        target_length = len(text)

        raw_positions = []
        cumulative = 0

        for length in source_lengths[:-1]:
            cumulative += length

            position = round(
                target_length * cumulative / total
            )

            raw_positions.append(position)

        positions = []
        previous = 0

        for position in raw_positions:
            position = max(
                previous,
                min(position, target_length),
            )

            positions.append(position)
            previous = position

        result = []
        start = 0

        for position in positions:
            result.append(text[start:position])
            start = position

        result.append(text[start:])

        return result


def inject_xhtml_text(
    html,
    paragraph_ids,
    paragraph_texts,
    title_text=None,
):
    return XHTMLTextInjector().inject(
        html,
        paragraph_ids,
        paragraph_texts,
        title_text=title_text,
    )
