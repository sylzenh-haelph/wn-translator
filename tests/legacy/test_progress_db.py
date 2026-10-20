import shutil
from pathlib import Path

from storage.progress_db import ProgressDB


TEST_DIR = Path("progress_test")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)


db = ProgressDB(TEST_DIR)


print("=== START CHAPTER ===")

data = db.start_chapter("chapter_001")

print(data)

assert data["chapter_id"] == "chapter_001"
assert data["status"] == "in_progress"


print("\n=== SAVE CHUNK 1 ===")

data = db.save_chunk(
    chapter_id="chapter_001",
    chunk_id="chunk_0000",
    translation="Alice memasuki istana.",
    context_state={
        "scene": "Alice memasuki istana.",
        "active_characters": ["Alice"],
        "current_situation": "Alice sedang mencari Marcus.",
        "references": [],
        "style_state": {},
    },
    attempts=1,
    qa_passed=True,
)

print(data)

assert "chunk_0000" in data["chunks"]
assert "chunk_0000" in data["completed_chunks"]
assert data["chunks"]["chunk_0000"]["attempts"] == 1


print("\n=== SAVE FLAGGED CHUNK ===")

data = db.save_chunk(
    chapter_id="chapter_001",
    chunk_id="chunk_0001",
    translation="Marcus masuk.",
    context_state={
        "scene": "Marcus enters.",
        "active_characters": ["Marcus"],
        "current_situation": "Marcus enters the room.",
        "references": [],
        "style_state": {},
    },
    attempts=3,
    qa_passed=False,
    flagged=True,
    qa_issues=[
        "paragraph_count",
        "preserved_entity",
    ],
)

print(data)

assert "chunk_0001" in data["chunks"]
assert "chunk_0001" in data["flagged_chunks"]
assert "chunk_0001" not in data["completed_chunks"]
assert data["chunks"]["chunk_0001"]["attempts"] == 3


print("\n=== COMPLETED CHECK ===")

assert db.is_chunk_completed(
    "chapter_001",
    "chunk_0000",
) is True

assert db.is_chunk_completed(
    "chapter_001",
    "chunk_0001",
) is False


print("chunk_0000:", db.is_chunk_completed(
    "chapter_001",
    "chunk_0000",
))

print("chunk_0001:", db.is_chunk_completed(
    "chapter_001",
    "chunk_0001",
))


print("\n=== GET CHUNK ===")

chunk = db.get_chunk(
    "chapter_001",
    "chunk_0000",
)

print(chunk)

assert chunk["translation"] == "Alice memasuki istana."
assert chunk["qa_passed"] is True


print("\n=== NEXT CHUNK ===")

next_chunk = db.get_next_chunk_id(
    "chapter_001",
    [
        "chunk_0000",
        "chunk_0001",
        "chunk_0002",
    ],
)

print("Next:", next_chunk)

assert next_chunk == "chunk_0001"


print("\n=== PERSISTENCE / RELOAD ===")

db2 = ProgressDB(TEST_DIR)

reloaded = db2.load("chapter_001")

print(reloaded)

assert reloaded["status"] == "in_progress"
assert "chunk_0000" in reloaded["completed_chunks"]
assert "chunk_0001" in reloaded["flagged_chunks"]
assert (
    reloaded["chunks"]["chunk_0000"]["translation"]
    == "Alice memasuki istana."
)


print("\n=== MARK COMPLETED ===")

data = db2.mark_completed("chapter_001")

print(data)

assert data["status"] == "completed"


print("\nPASS")

shutil.rmtree(TEST_DIR)
