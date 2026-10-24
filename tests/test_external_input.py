from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import ui.server as server


def test_external_file_under_storage_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_STORAGE", tmp_path)
    novel = tmp_path / "Novel.epub"
    novel.write_bytes(b"x")
    assert server.safe_input(str(novel)) == novel.resolve()


def test_path_outside_allowed_roots_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_STORAGE", tmp_path)
    with pytest.raises(ValueError):
        server.safe_input("/etc/passwd.epub")


def test_traversal_out_of_storage_is_rejected(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()
    outside = tmp_path / "secret.epub"
    outside.write_bytes(b"x")
    monkeypatch.setattr(server, "ALLOWED_STORAGE", storage)
    with pytest.raises(ValueError):
        server.safe_input(str(storage / ".." / "secret.epub"))


def test_remember_and_recent_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "SOURCES_FILE", tmp_path / "sources.json")
    novel = tmp_path / "Novel.epub"
    novel.write_bytes(b"x")
    server.remember_source(novel)
    assert server.recent_sources() == [novel]


def test_browse_page_links_novel_files(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_STORAGE", tmp_path)
    (tmp_path / "Novel.epub").write_bytes(b"x")
    page = server.browse_page(str(tmp_path))
    assert "/?input=" in page
    assert "Novel.epub" in page


def test_build_command_reads_external_source_without_copy():
    cmd = server.build_command(Path("/storage/emulated/0/Download/Novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000")
    assert "WN_SRC=" in cmd
    assert '"$WN_SRC"' in cmd
    assert "rm -f" in cmd
