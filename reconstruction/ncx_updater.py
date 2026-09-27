from xml.etree import ElementTree as ET


def _local_name(tag):
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


class NCXUpdater:
    """
    Update labels in an EPUB 2 NCX table of contents.

    href_to_title maps normalized target hrefs to translated titles.
    The NCX structure, navPoint hierarchy, playOrder, and content src
    attributes are preserved.
    """

    def update(self, xml_text, href_to_title):
        if not xml_text:
            return xml_text

        root = ET.fromstring(xml_text)

        for nav_point in root.iter():
            if _local_name(nav_point.tag) != "navPoint":
                continue

            content = None
            nav_label = None

            for child in nav_point:
                name = _local_name(child.tag)

                if name == "content":
                    content = child
                elif name == "navLabel":
                    nav_label = child

            if content is None or nav_label is None:
                continue

            src = content.get("src")
            if not src:
                continue

            # NCX src can contain a fragment, e.g. chapter1.xhtml#section.
            base_href = src.split("#", 1)[0]

            title = href_to_title.get(src)
            if title is None:
                title = href_to_title.get(base_href)

            if title is None:
                continue

            text_element = None

            for child in nav_label:
                if _local_name(child.tag) == "text":
                    text_element = child
                    break

            if text_element is None:
                text_element = ET.SubElement(
                    nav_label,
                    "text",
                )

            text_element.text = title

        return ET.tostring(
            root,
            encoding="unicode",
            xml_declaration=True,
        )


def update_ncx(xml_text, href_to_title):
    return NCXUpdater().update(
        xml_text,
        href_to_title,
    )
