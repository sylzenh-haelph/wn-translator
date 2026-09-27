from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from urllib.parse import unquote

from bs4 import BeautifulSoup, NavigableString, Tag

from models.document import Document, Paragraph, TextRun


def _local_name(tag):
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _find_opf_path(zip_file):
    container_path = "META-INF/container.xml"
    if container_path not in zip_file.namelist():
        raise ValueError("EPUB tidak memiliki META-INF/container.xml.")

    root = ET.fromstring(zip_file.read(container_path))

    for element in root.iter():
        if _local_name(element.tag) == "rootfile":
            full_path = element.attrib.get("full-path")
            if full_path:
                return full_path

    raise ValueError("OPF path tidak ditemukan di container.xml.")


def _read_metadata(zip_file, opf_path):
    root = ET.fromstring(zip_file.read(opf_path))

    title = ""
    author = ""

    package_metadata = {
        "dc": [],
        "meta": [],
        "package_attributes": {},
    }

    for key, value in root.attrib.items():
        package_metadata["package_attributes"][_local_name(key)] = value

    metadata_element = None

    for element in root:
        if _local_name(element.tag) == "metadata":
            metadata_element = element
            break

    if metadata_element is not None:
        for element in metadata_element:
            local = _local_name(element.tag)
            text = "".join(element.itertext()).strip()

            attributes = {
                _local_name(key): value
                for key, value in element.attrib.items()
            }

            if local in {
                "title",
                "creator",
                "language",
                "identifier",
                "publisher",
                "description",
                "date",
                "subject",
                "contributor",
                "coverage",
                "format",
                "relation",
                "rights",
                "source",
                "type",
            }:
                package_metadata["dc"].append(
                    {
                        "name": local,
                        "text": text,
                        "attributes": attributes,
                    }
                )

                if local == "title" and not title:
                    title = text

                elif local == "creator" and not author:
                    author = text

            elif local == "meta":
                package_metadata["meta"].append(
                    {
                        "text": text,
                        "attributes": attributes,
                    }
                )

    return title, author, package_metadata


def _resolve_path(base_path, relative_path):
    base = Path(base_path).parent
    resolved = Path(base, unquote(relative_path))

    parts = []

    for part in resolved.as_posix().split("/"):
        if part in ("", "."):
            continue

        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)

    return "/".join(parts)


def _get_text_formatting(tag):
    formatting = {}

    if not isinstance(tag, Tag):
        return formatting

    chain = [tag]
    parent = tag.parent

    while isinstance(parent, Tag):
        chain.append(parent)
        parent = parent.parent

    names = {_local_name(t.name).lower() for t in chain}

    if names & {"strong", "b"}:
        formatting["bold"] = True

    if names & {"em", "i"}:
        formatting["italic"] = True

    if names & {"u"}:
        formatting["underline"] = True

    if names & {"sup"}:
        formatting["superscript"] = True

    if names & {"sub"}:
        formatting["subscript"] = True

    return formatting


def _normalize_text(text):
    return " ".join(text.split())


def _extract_runs(paragraph_tag):
    runs = []

    for node in paragraph_tag.descendants:
        if not isinstance(node, NavigableString):
            continue

        text = _normalize_text(str(node))

        if not text:
            continue

        formatting = _get_text_formatting(node.parent)

        runs.append(
            TextRun(
                text=text,
                formatting=formatting,
            )
        )

    return runs


def _extract_paragraph_style(paragraph_tag):
    style = {}

    if not isinstance(paragraph_tag, Tag):
        return style

    class_name = paragraph_tag.get("class")

    if class_name:
        if isinstance(class_name, list):
            style["class"] = " ".join(class_name)
        else:
            style["class"] = str(class_name)

    element_name = _local_name(paragraph_tag.name).lower()

    if element_name in {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }:
        style["heading_level"] = int(element_name[1])

    align = paragraph_tag.get("align")

    if align:
        style["alignment"] = align

    return style


def _extract_paragraphs(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for tag in soup.find_all(
        [
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ]
    ):
        runs = _extract_runs(tag)
        style = _extract_paragraph_style(tag)

        results.append((runs, style))

    return results


def _read_epub_structure(zip_file, opf_path):
    root = ET.fromstring(zip_file.read(opf_path))

    manifest = {}
    spine = []
    spine_attributes = {}

    for key, value in root.find(".").attrib.items():
        spine_attributes[_local_name(key)] = value

    for element in root.iter():
        if _local_name(element.tag) == "item":
            item_id = element.attrib.get("id")
            href = element.attrib.get("href")
            media_type = element.attrib.get("media-type", "")
            properties = element.attrib.get("properties", "")

            if item_id and href:
                manifest[item_id] = {
                    "href": href,
                    "media_type": media_type,
                    "properties": properties,
                }

        elif _local_name(element.tag) == "spine":
            spine_attributes = {
                _local_name(key): value
                for key, value in element.attrib.items()
            }

        elif _local_name(element.tag) == "itemref":
            idref = element.attrib.get("idref")

            if idref:
                spine.append(idref)

    navigation_items = {}

    for item_id, item in manifest.items():
        properties = item.get("properties", "")
        property_values = set(properties.split())

        if "nav" in property_values:
            navigation_items[item_id] = {
                "href": item.get("href", ""),
                "media_type": item.get("media_type", ""),
                "properties": properties,
            }

    return {
        "opf_path": opf_path,
        "manifest": manifest,
        "spine": spine,
        "spine_attributes": spine_attributes,
        "navigation_items": navigation_items,
        "paragraph_spine_map": {},
        "spine_stylesheets": {},
        "xhtml_sources": {},
    }


def _extract_stylesheet_links(html):
    soup = BeautifulSoup(html, "html.parser")

    links = []

    for link in soup.find_all("link"):
        rel = link.get("rel") or []

        if isinstance(rel, str):
            rel_values = rel.lower().split()
        else:
            rel_values = [
                str(value).lower()
                for value in rel
            ]

        if "stylesheet" not in rel_values:
            continue

        href = link.get("href")

        if href:
            links.append(href)

    return links


def parse_epub(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"EPUB tidak ditemukan: {path}"
        )

    with ZipFile(path, "r") as zip_file:
        opf_path = _find_opf_path(zip_file)

        title, author, package_metadata = _read_metadata(
            zip_file,
            opf_path,
        )

        epub_structure = _read_epub_structure(
            zip_file,
            opf_path,
        )

        epub_structure["package_metadata"] = package_metadata

        manifest = epub_structure["manifest"]
        spine = epub_structure["spine"]

        document = Document(
            title=title,
            author=author,
            paragraphs=[],
            metadata={},
        )

        paragraph_spine_map = {}
        spine_stylesheets = {}
        xhtml_sources = {}

        paragraph_number = 0

        for idref in spine:
            item = manifest.get(idref)

            if item is None:
                continue

            href = item.get("href")

            if not href:
                continue

            xhtml_path = _resolve_path(
                opf_path,
                href,
            )

            if xhtml_path not in zip_file.namelist():
                continue

            html = zip_file.read(
                xhtml_path
            ).decode(
                "utf-8",
                errors="replace",
            )

            # Simpan XHTML asli secara utuh.
            # Ini menjadi sumber struktur ketika reconstruction
            # mulai menggunakan XHTML preservation layer.
            xhtml_sources[idref] = {
                "path": xhtml_path,
                "html": html,
            }

            stylesheet_links = _extract_stylesheet_links(
                html
            )

            resolved_stylesheets = []

            for stylesheet_href in stylesheet_links:
                resolved_stylesheets.append(
                    _resolve_path(
                        xhtml_path,
                        stylesheet_href,
                    )
                )

            spine_stylesheets[idref] = {
                "links": stylesheet_links,
                "resolved_paths": resolved_stylesheets,
            }

            for runs, style in _extract_paragraphs(html):
                paragraph_id = f"p{paragraph_number:04d}"

                document.paragraphs.append(
                    Paragraph(
                        id=paragraph_id,
                        runs=runs,
                        style=style,
                    )
                )

                paragraph_spine_map[
                    paragraph_id
                ] = idref

                paragraph_number += 1

        epub_structure[
            "paragraph_spine_map"
        ] = paragraph_spine_map

        epub_structure[
            "spine_stylesheets"
        ] = spine_stylesheets

        # Simpan navigation XHTML juga, meskipun tidak
        # termasuk spine.
        navigation_items = epub_structure.get(
            "navigation_items",
            {},
        )

        for nav_id, nav_info in navigation_items.items():
            href = nav_info.get("href")

            if not href:
                continue

            nav_path = _resolve_path(
                opf_path,
                href,
            )

            if nav_path not in zip_file.namelist():
                continue

            nav_html = zip_file.read(
                nav_path
            ).decode(
                "utf-8",
                errors="replace",
            )

            xhtml_sources[nav_id] = {
                "path": nav_path,
                "html": nav_html,
            }

        epub_structure[
            "xhtml_sources"
        ] = xhtml_sources

        document.metadata["epub"] = epub_structure

        return document
