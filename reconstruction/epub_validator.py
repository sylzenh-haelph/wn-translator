from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from zipfile import ZIP_STORED, BadZipFile, ZipFile
from xml.etree import ElementTree as ET
from urllib.parse import unquote


@dataclass
class ValidationIssue:
    rule: str
    message: str
    severity: str = "error"


@dataclass
class EPUBValidationResult:
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
OPF_NS = "http://www.idpf.org/2007/opf"
DC_NS = "http://purl.org/dc/elements/1.1/"


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _normalize_path(path: str) -> str:
    parts = []

    for part in path.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue

        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)

    return "/".join(parts)


def _resolve_path(base_file: str, href: str) -> str:
    base_dir = Path(base_file).parent.as_posix()

    href = unquote(href.split("#", 1)[0])

    if base_dir == ".":
        return _normalize_path(href)

    return _normalize_path(f"{base_dir}/{href}")


def _add_error(issues, rule, message):
    issues.append(
        ValidationIssue(
            rule=rule,
            message=message,
            severity="error",
        )
    )


def _validate_zip_basics(archive, issues):
    names = archive.namelist()

    if not names:
        _add_error(
            issues,
            "ZIP_NOT_EMPTY",
            "EPUB ZIP tidak memiliki entry.",
        )
        return None

    if names[0] != "mimetype":
        _add_error(
            issues,
            "MIMETYPE_FIRST",
            "Entry pertama EPUB harus 'mimetype'.",
        )

    if names.count("mimetype") != 1:
        _add_error(
            issues,
            "MIMETYPE_UNIQUE",
            "Entry 'mimetype' harus muncul tepat satu kali.",
        )

    if "mimetype" not in names:
        _add_error(
            issues,
            "MIMETYPE_EXISTS",
            "EPUB tidak memiliki entry 'mimetype'.",
        )
        return None

    info = archive.getinfo("mimetype")

    if info.compress_type != ZIP_STORED:
        _add_error(
            issues,
            "MIMETYPE_UNCOMPRESSED",
            "Entry 'mimetype' harus tidak terkompresi.",
        )

    try:
        mimetype = archive.read("mimetype").decode("utf-8")
    except (UnicodeDecodeError, KeyError):
        _add_error(
            issues,
            "MIMETYPE_READABLE",
            "Entry 'mimetype' tidak dapat dibaca sebagai UTF-8.",
        )
        return None

    if mimetype != "application/epub+zip":
        _add_error(
            issues,
            "MIMETYPE_VALUE",
            f"Nilai mimetype tidak valid: {mimetype!r}",
        )

    return names


def _validate_container(archive, issues):
    container_path = "META-INF/container.xml"

    if container_path not in archive.namelist():
        _add_error(
            issues,
            "CONTAINER_EXISTS",
            "META-INF/container.xml tidak ditemukan.",
        )
        return None

    try:
        root = ET.fromstring(
            archive.read(container_path)
        )
    except (ET.ParseError, UnicodeDecodeError) as exc:
        _add_error(
            issues,
            "CONTAINER_XML",
            f"container.xml tidak valid: {exc}",
        )
        return None

    rootfiles = [
        element
        for element in root.iter()
        if _local_name(element.tag) == "rootfile"
    ]

    if not rootfiles:
        _add_error(
            issues,
            "CONTAINER_ROOTFILE",
            "container.xml tidak memiliki rootfile.",
        )
        return None

    opf_path = rootfiles[0].attrib.get("full-path")

    if not opf_path:
        _add_error(
            issues,
            "CONTAINER_OPF_PATH",
            "rootfile tidak memiliki full-path.",
        )
        return None

    opf_path = _normalize_path(unquote(opf_path))

    if opf_path not in archive.namelist():
        _add_error(
            issues,
            "OPF_EXISTS",
            f"OPF tidak ditemukan: {opf_path}",
        )
        return None

    return opf_path


def _validate_opf(archive, opf_path, issues):
    try:
        root = ET.fromstring(
            archive.read(opf_path)
        )
    except (ET.ParseError, UnicodeDecodeError, KeyError) as exc:
        _add_error(
            issues,
            "OPF_XML",
            f"content.opf tidak valid: {exc}",
        )
        return None

    if _local_name(root.tag) != "package":
        _add_error(
            issues,
            "OPF_ROOT",
            "Root OPF harus berupa <package>.",
        )

    manifest_items = {}
    spine_ids = []

    for element in root.iter():
        local = _local_name(element.tag)

        if local == "item":
            item_id = element.attrib.get("id")
            href = element.attrib.get("href")
            media_type = element.attrib.get("media-type")

            if not item_id:
                _add_error(
                    issues,
                    "OPF_MANIFEST_ID",
                    "Manifest item tidak memiliki id.",
                )
                continue

            if item_id in manifest_items:
                _add_error(
                    issues,
                    "OPF_DUPLICATE_MANIFEST_ID",
                    f"Manifest id duplikat: {item_id}",
                )

            manifest_items[item_id] = {
                "href": href,
                "media_type": media_type,
            }

        elif local == "itemref":
            idref = element.attrib.get("idref")
            if idref:
                spine_ids.append(idref)

    if not manifest_items:
        _add_error(
            issues,
            "OPF_MANIFEST",
            "OPF tidak memiliki manifest item.",
        )

    if not spine_ids:
        _add_error(
            issues,
            "OPF_SPINE",
            "OPF tidak memiliki spine itemref.",
        )

    names = set(archive.namelist())

    for item_id, item in manifest_items.items():
        href = item.get("href")

        if not href:
            _add_error(
                issues,
                "OPF_MANIFEST_HREF",
                f"Manifest item {item_id!r} tidak memiliki href.",
            )
            continue

        resource_path = _resolve_path(
            opf_path,
            href,
        )

        if resource_path not in names:
            _add_error(
                issues,
                "OPF_RESOURCE_EXISTS",
                f"Resource manifest tidak ditemukan: {resource_path}",
            )

    for idref in spine_ids:
        if idref not in manifest_items:
            _add_error(
                issues,
                "OPF_SPINE_REFERENCE",
                f"Spine mereferensikan manifest id yang tidak ada: {idref}",
            )

    return {
        "root": root,
        "manifest": manifest_items,
        "spine": spine_ids,
    }


def _validate_xhtml_documents(
    archive,
    opf_path,
    opf_info,
    issues,
):
    names = set(archive.namelist())

    for item_id, item in opf_info["manifest"].items():
        media_type = item.get("media_type")
        href = item.get("href")

        if media_type not in {
            "application/xhtml+xml",
            "text/html",
        }:
            continue

        if not href:
            continue

        path = _resolve_path(
            opf_path,
            href,
        )

        if path not in names:
            continue

        try:
            root = ET.fromstring(
                archive.read(path)
            )
        except (ET.ParseError, UnicodeDecodeError) as exc:
            _add_error(
                issues,
                "XHTML_XML",
                f"XHTML tidak valid ({path}): {exc}",
            )
            continue

        local = _local_name(root.tag)

        if local not in {"html", "HTML"}:
            _add_error(
                issues,
                "XHTML_ROOT",
                f"Root XHTML tidak valid ({path}): <{local}>",
            )


def validate_epub(path) -> EPUBValidationResult:
    path = Path(path)
    issues: list[ValidationIssue] = []

    if not path.exists():
        _add_error(
            issues,
            "OUTPUT_EXISTS",
            f"File output tidak ditemukan: {path}",
        )
        return EPUBValidationResult(False, issues)

    if not path.is_file():
        _add_error(
            issues,
            "OUTPUT_FILE",
            f"Output bukan file: {path}",
        )
        return EPUBValidationResult(False, issues)

    if path.stat().st_size == 0:
        _add_error(
            issues,
            "OUTPUT_NONEMPTY",
            "File output berukuran 0 byte.",
        )
        return EPUBValidationResult(False, issues)

    try:
        with ZipFile(path, "r") as archive:
            names = _validate_zip_basics(
                archive,
                issues,
            )

            if names is None:
                return EPUBValidationResult(
                    not any(i.severity == "error" for i in issues),
                    issues,
                )

            opf_path = _validate_container(
                archive,
                issues,
            )

            if opf_path is None:
                return EPUBValidationResult(
                    not any(i.severity == "error" for i in issues),
                    issues,
                )

            opf_info = _validate_opf(
                archive,
                opf_path,
                issues,
            )

            if opf_info is not None:
                _validate_xhtml_documents(
                    archive,
                    opf_path,
                    opf_info,
                    issues,
                )

    except BadZipFile as exc:
        _add_error(
            issues,
            "EPUB_ZIP",
            f"File bukan ZIP/EPUB yang valid: {exc}",
        )
    except OSError as exc:
        _add_error(
            issues,
            "OUTPUT_READ",
            f"Output tidak dapat dibaca: {exc}",
        )

    passed = not any(
        issue.severity == "error"
        for issue in issues
    )

    return EPUBValidationResult(
        passed=passed,
        issues=issues,
    )
