# Converise EN»ID

Terjemahan novel Inggris ke Indonesia dengan AI (Gemini dan Gemma), dengan antarmuka lokal yang bisa dibuka dari HP.

## Alur

EPUB/DOCX -> parser -> pemisah chapter -> riset entitas (opsional, Tavily) -> glosarium -> chunking -> terjemahan -> QA aturan -> retry -> progres per chunk -> rakit ulang -> EPUB/DOCX

## Cara menjalankan

    pip install -r requirements.txt
    export GEMINI_API_KEY="..."
    export TAVILY_API_KEY="..."   # opsional; tanpa ini matikan riset dengan WN_RESEARCH_ENABLED=0
    python ui/server.py

Buka http://127.0.0.1:8765 di browser. Server hanya bisa diakses dari perangkat itu sendiri.

Contoh lewat CLI:

    python main.py input/novel.epub -o temp/novel.epub --project-dir temp/novel_project --chapter 2-5
    python main.py input/novel.epub --scan-glossary glossary/novel.txt --project-dir temp/novel_project

## Struktur

- main.py: pipeline CLI untuk terjemahan, scan glosarium, dan ekspor chapter
- ui/: antarmuka lokal dan halaman editor glosarium
- parsers/: parser EPUB/DOCX dan perbaikan EPUB sumber
- research/: deteksi dan riset entitas
- translation/: chunking, terjemahan, refinement, penerjemah judul, dan pipeline project
- qa/: pemeriksaan aturan dan kontrol retry
- storage/: progres, cache, dan statistik
- reconstruction/: rakit ulang EPUB/DOCX
- config/: pengaturan dan batas retry
- tests/: tes utama
- tests/legacy/: tes lama yang dipindah dari root; tetap dijalankan
- docs/shortcuts.md: daftar keputusan sementara di kode

## Data lokal (tidak di Git)

- input/: novel asli. Hanya fixture tes yang ikut di Git.
- glossary/: glosarium per novel. Cadangan dibuat lewat tombol Backup data di UI.
- temp/: progres, cache, log, dan hasil build.

## Tes

    pytest

## Keamanan

API key diambil dari environment variable dan tidak boleh di-commit. File .env sudah diabaikan oleh Git.

## Status

Dalam pengembangan aktif.
