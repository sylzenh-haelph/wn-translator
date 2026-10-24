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

## Fitur di UI

- Mode Terjemahkan, Ekspor chapter selesai, dan Scan glosarium.
- Editor glosarium dengan pencarian, filter, urutan, dan penanda entri baru hasil scan.
- Alias glosarium dengan awalan `~`, misalnya `~Rudy = Rudeus Greyrat`.
- Cek nama dan cek kualitas dari hasil terjemahan yang sudah tersimpan, tanpa memanggil model.
- Kartu chapter gagal dengan alasan dari log dan tombol ulang per chapter.
- Pemeriksaan kuota harian sebelum proses dimulai.
- Riset entitas dipakai bersama untuk volume dari seri yang sama lewat nama glosarium.

## Struktur

- main.py: pipeline CLI untuk terjemahan, scan glosarium, dan ekspor chapter
- ui/: antarmuka lokal dan editor glosarium
- parsers/: parser EPUB/DOCX dan perbaikan EPUB sumber
- research/: deteksi dan riset entitas
- translation/: chunking, terjemahan, refinement, penerjemah judul, glosarium, cek nama, dan cek kualitas
- qa/: pemeriksaan aturan dan kontrol retry
- storage/: progres, cache, dan statistik
- reconstruction/: rakit ulang EPUB/DOCX
- config/: pengaturan dan batas retry
- tests/: tes utama
- tests/legacy/: tes lama yang dipindah dari root; tetap dijalankan
- scripts/manual/: skrip manual yang memanggil API; tidak dijalankan pytest
- docs/shortcuts.md: daftar keputusan sementara di kode

## Data lokal (tidak di Git)

- input/: novel asli. Hanya fixture tes yang ikut di Git.
- glossary/: glosarium per novel, termasuk hasil riset per seri di glossary/.entities/.
- temp/: progres, cache, log, dan hasil build.

## Tes

    pytest

## Keamanan

API key diambil dari environment variable dan tidak boleh di-commit. File .env sudah diabaikan oleh Git.

## Status

Dalam pengembangan aktif.
