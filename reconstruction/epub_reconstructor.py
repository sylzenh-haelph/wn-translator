from copy import deepcopy
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from models.document import Document, Paragraph
from reconstruction.xhtml_text_injector import inject_xhtml_text
from reconstruction.navigation_updater import update_navigation
from reconstruction.ncx_updater import update_ncx


def _local_name(tag):
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _format_run(run):
    text = run.text

    if run.formatting.get("superscript"):
        text = f"<sup>{text}</sup>"

    elif run.formatting.get("subscript"):
        text = f"<sub>{text}</sub>"

    if run.formatting.get("bold"):
        text = f"<strong>{text}</strong>"

    if run.formatting.get("italic"):
        text = f"<em>{text}</em>"

    if run.formatting.get("underline"):
        text = f"<u>{text}</u>"

    return text


def _paragraph_html(paragraph):
    if not paragraph.runs:
        return "<p></p>"

    content = "".join(
        _format_run(run)
        for run in paragraph.runs
    )

    heading_level = paragraph.style.get(
        "heading_level"
    )

    if heading_level:
        return (
            f"<h{heading_level}>"
            f"{content}"
            f"</h{heading_level}>"
        )

    return f"<p>{content}</p>"


def _build_xhtml(
    paragraphs,
    stylesheet_paths=None,
):
    stylesheet_paths = stylesheet_paths or []

    links = ""

    for stylesheet_path in stylesheet_paths:
        links += (
            f'<link rel="stylesheet" '
            f'href="{stylesheet_path}" '
            f'type="text/css"/>'
        )

    body = "\n".join(
        _paragraph_html(paragraph)
        for paragraph in paragraphs
    )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
{links}
</head>
<body>
{body}
</body>
</html>
"""


def _build_content_opf(document, structure):
    package_metadata = structure.get(
        "package_metadata",
        {},
    )

    package_attributes = package_metadata.get(
        "package_attributes",
        {},
    )

    root_attributes = {
        "version": "3.0",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
    }

    if package_attributes.get(
        "unique-identifier"
    ):
        root_attributes[
            "unique-identifier"
        ] = package_attributes[
            "unique-identifier"
        ]

    root = ET.Element(
        "package",
        root_attributes,
    )

    metadata = ET.SubElement(
        root,
        "metadata",
    )

    dc_entries = package_metadata.get(
        "dc",
        [],
    )

    if dc_entries:
        for entry in dc_entries:
            name = entry["name"]
            text = entry.get("text", "")
            attributes = entry.get(
                "attributes",
                {},
            )

            element = ET.SubElement(
                metadata,
                f"dc:{name}",
                attributes,
            )
            element.text = text

        for entry in package_metadata.get(
            "meta",
            [],
        ):
            element = ET.SubElement(
                metadata,
                "meta",
                entry.get("attributes", {}),
            )
            text = entry.get("text", "")
            if text:
                element.text = text

    else:
        title = ET.SubElement(
            metadata,
            "dc:title",
        )
        title.text = document.title

        creator = ET.SubElement(
            metadata,
            "dc:creator",
        )
        creator.text = document.author

        identifier = ET.SubElement(
            metadata,
            "dc:identifier",
            {"id": "bookid"},
        )
        identifier.text = "urn:uuid:wn-translator"

        language = ET.SubElement(
            metadata,
            "dc:language",
        )
        language.text = "id"

    manifest = ET.SubElement(
        root,
        "manifest",
    )

    manifest_data = structure.get(
        "manifest",
        {},
    )

    for item_id, item in manifest_data.items():
        attributes = {
            "id": item_id,
            "href": item["href"],
            "media-type": item.get(
                "media_type",
                "",
            ),
        }

        properties = item.get(
            "properties",
            "",
        )

        if properties:
            attributes["properties"] = properties

        ET.SubElement(
            manifest,
            "item",
            attributes,
        )

    spine_attributes = structure.get(
        "spine_attributes",
        {},
    )

    spine = ET.SubElement(
        root,
        "spine",
        spine_attributes,
    )

    for idref in structure.get(
        "spine",
        [],
    ):
        ET.SubElement(
            spine,
            "itemref",
            {"idref": idref},
        )

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


def _build_container_xml(opf_path):
    root = ET.Element(
        "container",
        {
            "version": "1.0",
            "xmlns": (
                "urn:oasis:names:tc:opendocument:"
                "xmlns:container"
            ),
        },
    )

    rootfiles = ET.SubElement(
        root,
        "rootfiles",
    )

    ET.SubElement(
        rootfiles,
        "rootfile",
        {
            "full-path": opf_path,
            "media-type": (
                "application/oebps-package+xml"
            ),
        },
    )

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


def _build_default_structure(document):
    return {
        "opf_path": "OEBPS/content.opf",
        "manifest": {
            "content": {
                "href": "content.xhtml",
                "media_type": (
                    "application/xhtml+xml"
                ),
                "properties": "",
            }
        },
        "spine": ["content"],
        "paragraph_spine_map": {
            paragraph.id: "content"
            for paragraph in document.paragraphs
        },
        "spine_stylesheets": {},
        "xhtml_sources": {},
        "package_metadata": {},
    }


def _group_paragraphs_by_spine(
    document,
    structure,
):
    paragraph_map = structure.get(
        "paragraph_spine_map",
        {},
    )

    grouped = {}

    for paragraph in document.paragraphs:
        idref = paragraph_map.get(
            paragraph.id
        )

        if idref is None:
            continue

        grouped.setdefault(
            idref,
            [],
        ).append(paragraph)

    return grouped


def _normalize_zip_path(path):
    parts = []

    for part in Path(path).as_posix().split("/"):
        if part in ("", "."):
            continue

        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)

    return "/".join(parts)


def _opf_directory(opf_path):
    path = Path(opf_path).parent.as_posix()

    if path == ".":
        return ""

    return path


def _resolve_resource_path(
    opf_path,
    href,
):
    base = _opf_directory(opf_path)

    return _normalize_zip_path(
        f"{base}/{unquote(href)}"
    )


def _is_generated_entry(
    path,
    generated_paths,
):
    return path in generated_paths


def _build_navigation_titles(
    document,
    structure,
):
    """
    Membuat mapping href chapter -> judul hasil.

    Prioritas:
    1. heading paragraph yang memang menjadi heading chapter
    2. judul dari paragraph pertama jika heading tidak tersedia
    3. tidak membuat entry jika chapter kosong
    """

    manifest = structure.get(
        "manifest",
        {},
    )

    paragraph_map = structure.get(
        "paragraph_spine_map",
        {},
    )

    result = {}

    for idref in structure.get(
        "spine",
        [],
    ):
        item = manifest.get(idref)

        if not item:
            continue

        href = item.get("href")

        if not href:
            continue

        paragraphs = [
            paragraph
            for paragraph in document.paragraphs
            if paragraph_map.get(
                paragraph.id
            ) == idref
        ]

        if not paragraphs:
            continue

        title = ""

        for paragraph in paragraphs:
            if paragraph.style.get(
                "heading_level"
            ):
                title = paragraph.text.strip()
                break

        if not title:
            title = paragraphs[0].text.strip()

        if title:
            result[href] = title

    return result


def _update_navigation_source(
    structure,
    document,
):
    """
    Mengambil nav.xhtml asli dan memperbarui label
    berdasarkan judul chapter hasil translation.
    """

    navigation_items = structure.get(
        "navigation_items",
        {},
    )

    sources = structure.get(
        "xhtml_sources",
        {},
    )

    for nav_id, nav_info in navigation_items.items():
        original = sources.get(nav_id)

        if not original:
            continue

        href_to_title = _build_navigation_titles(
            document,
            structure,
        )

        return (
            original.get("path"),
            update_navigation(
                original.get("html", ""),
                href_to_title,
            ),
        )

    return None, None


def _get_paragraph_ids_for_spine(
    document,
    structure,
    idref,
):
    paragraph_map = structure.get(
        "paragraph_spine_map",
        {},
    )

    return [
        paragraph.id
        for paragraph in document.paragraphs
        if paragraph_map.get(
            paragraph.id
        ) == idref
    ]


def _get_original_xhtml(
    structure,
    idref,
):
    sources = structure.get(
        "xhtml_sources",
        {},
    )

    source = sources.get(idref)

    if not source:
        return None

    return source.get("html")


def _can_use_xhtml_source(
    document,
    structure,
    idref,
    paragraphs,
):
    original = _get_original_xhtml(
        structure,
        idref,
    )

    if original is None:
        return False

    # XHTML tanpa paragraph document tidak boleh dikirim ke injector.
    # Contohnya nav.xhtml: file ini dapat memiliki <nav>/<p>, tetapi
    # elemen tersebut bukan bagian dari paragraph translation.
    if not paragraphs:
        return False

    expected_ids = _get_paragraph_ids_for_spine(
        document,
        structure,
        idref,
    )

    if len(expected_ids) != len(paragraphs):
        return False

    return True


def _inject_translated_xhtml(
    document,
    structure,
    idref,
    paragraphs,
):
    original = _get_original_xhtml(
        structure,
        idref,
    )

    if original is None:
        return None

    paragraph_ids = [
        paragraph.id
        for paragraph in paragraphs
    ]

    paragraph_texts = {
        paragraph.id: paragraph.text
        for paragraph in paragraphs
    }

    title_text = None

    for paragraph in paragraphs:
        if paragraph.style.get("heading_level") is not None:
            title_text = paragraph.text
            break

    return inject_xhtml_text(
        original,
        paragraph_ids,
        paragraph_texts,
        title_text=title_text,
    )


def _update_ncx_source(
    structure,
    document,
    source_path,
):
    """
    Mengambil toc.ncx asli dari EPUB sumber dan memperbarui
    label navPoint berdasarkan judul chapter hasil translation.

    EPUB dapat mereferensikan NCX melalui spine@toc tanpa
    mendaftarkan file NCX di manifest, jadi kedua bentuk
    didukung.
    """
    if source_path is None:
        return None, None

    source_path = Path(source_path)

    if not source_path.exists():
        return None, None

    opf_path = structure.get(
        "opf_path",
        "OEBPS/content.opf",
    )

    manifest = structure.get(
        "manifest",
        {},
    )

    ncx_path = None

    # EPUB dengan manifest item untuk NCX.
    spine_attributes = structure.get(
        "spine_attributes",
        {},
    )

    toc_id = spine_attributes.get("toc")

    if toc_id and toc_id in manifest:
        ncx_href = manifest[toc_id].get("href")

        if ncx_href:
            ncx_path = _resolve_resource_path(
                opf_path,
                ncx_href,
            )

    if ncx_path is None:
        for item in manifest.values():
            if item.get("media_type") == "application/x-dtbncx+xml":
                ncx_href = item.get("href")

                if ncx_href:
                    ncx_path = _resolve_resource_path(
                        opf_path,
                        ncx_href,
                    )
                    break

    # Fixture/EPUB yang hanya menggunakan spine@toc="ncx"
    # tanpa manifest item.
    if ncx_path is None:
        opf_dir = _opf_directory(opf_path)

        candidate_names = [
            "toc.ncx",
            f"{toc_id}.ncx" if toc_id else "",
        ]

        source_names = set()

        try:
            with ZipFile(source_path, "r") as archive:
                source_names = set(archive.namelist())
        except Exception:
            return None, None

        for candidate in candidate_names:
            if not candidate:
                continue

            candidate_path = _normalize_zip_path(
                f"{opf_dir}/{candidate}"
            )

            if candidate_path in source_names:
                ncx_path = candidate_path
                break

    if ncx_path is None:
        return None, None

    try:
        with ZipFile(source_path, "r") as archive:
            original_xml = archive.read(
                ncx_path
            ).decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        return None, None

    href_to_title = _build_navigation_titles(
        document,
        structure,
    )

    if not href_to_title:
        return ncx_path, original_xml

    return (
        ncx_path,
        update_ncx(
            original_xml,
            href_to_title,
        ),
    )



def reconstruct_epub(
    document: Document,
    output_path,
    source_path=None,
):
    output_path = Path(output_path)

    structure = deepcopy(
        document.metadata.get(
            "epub",
            _build_default_structure(document),
        )
    )

    if not structure.get("manifest"):
        structure = _build_default_structure(
            document
        )

    grouped = _group_paragraphs_by_spine(
        document,
        structure,
    )

    if not grouped:
        structure = _build_default_structure(
            document
        )

        grouped = {
            "content": list(
                document.paragraphs
            )
        }

    opf_path = structure.get(
        "opf_path",
        "OEBPS/content.opf",
    )

    generated_paths = {
        "mimetype",
        "META-INF/container.xml",
        opf_path,
    }

    manifest = structure.get(
        "manifest",
        {},
    )

    generated_xhtml = {}
    generated_resources = {}

    for idref in structure.get(
        "spine",
        [],
    ):
        item = manifest.get(idref)

        if not item:
            continue

        href = item.get("href")

        if not href:
            continue

        xhtml_path = _resolve_resource_path(
            opf_path,
            href,
        )

        paragraphs = grouped.get(
            idref,
            [],
        )

        if _can_use_xhtml_source(
            document,
            structure,
            idref,
            paragraphs,
        ):
            html = _inject_translated_xhtml(
                document,
                structure,
                idref,
                paragraphs,
            )

            if html is not None:
                generated_xhtml[
                    xhtml_path
                ] = html

        if xhtml_path not in generated_xhtml:
            stylesheet_info = structure.get(
                "spine_stylesheets",
                {},
            ).get(idref, {})

            stylesheet_paths = stylesheet_info.get(
                "links",
                [],
            )

            generated_xhtml[
                xhtml_path
            ] = _build_xhtml(
                paragraphs,
                stylesheet_paths,
            )

        generated_paths.add(
            xhtml_path
        )

    # Update nav.xhtml jika tersedia.
    navigation_path, navigation_html = (
        _update_navigation_source(
            structure,
            document,
        )
    )

    if navigation_path and navigation_html:
        generated_xhtml[
            navigation_path
        ] = navigation_html

        generated_paths.add(
            navigation_path
        )

    # Update EPUB 2 toc.ncx jika tersedia.
    ncx_path, ncx_xml = _update_ncx_source(
        structure,
        document,
        source_path,
    )

    if ncx_path and ncx_xml:
        generated_resources[
            ncx_path
        ] = ncx_xml

        generated_paths.add(
            ncx_path
        )

    content_opf = _build_content_opf(
        document,
        structure,
    )

    container_xml = _build_container_xml(
        opf_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with ZipFile(
        output_path,
        "w",
    ) as output:
        output.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=0,
        )

        output.writestr(
            "META-INF/container.xml",
            container_xml,
            compress_type=ZIP_DEFLATED,
        )

        output.writestr(
            opf_path,
            content_opf,
            compress_type=ZIP_DEFLATED,
        )

        for path, html in generated_xhtml.items():
            output.writestr(
                path,
                html.encode("utf-8"),
                compress_type=ZIP_DEFLATED,
            )

        for path, data in generated_resources.items():
            if isinstance(data, str):
                data = data.encode("utf-8")

            output.writestr(
                path,
                data,
                compress_type=ZIP_DEFLATED,
            )

        if source_path is not None:
            source_path = Path(source_path)

            if source_path.exists():
                with ZipFile(
                    source_path,
                    "r",
                ) as source_zip:
                    for info in source_zip.infolist():
                        name = info.filename

                        if _is_generated_entry(
                            name,
                            generated_paths,
                        ):
                            continue

                        data = source_zip.read(
                            name
                        )

                        output.writestr(
                            info,
                            data,
                            compress_type=info.compress_type,
                        )

    return output_path
