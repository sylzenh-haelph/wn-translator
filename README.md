# Converise EN»ID

Terjemahan novel Inggris ke Indonesia dengan AI (Gemini dan Gemma), dengan antarmuka lokal yang bisa dibuka dari HP. Berjalan di Termux.

## Alur

EPUB/DOCX -> parser -> pemisah chapter (Heading 1 atau AI untuk bagian ambigu) -> glosarium -> chunking -> terjemahan (JSON per paragraf) -> refinement jika QA gagal -> QA aturan -> retry -> progres per chunk -> rakit ulang -> EPUB/DOCX

Riset entitas (Tavily) hanya dipakai di mode Radar, bukan saat menerjemahkan.

## Cara menjalankan

    pip install -r requirements.txt
    export GEMINI_API_KEY="..."
    export TAVILY_API_KEY="..."   # opsional; tanpa ini matikan riset dengan WN_RESEARCH_ENABLED=0
    python ui/server.py

Buka http://127.0.0.1:8765 di browser. Server hanya bisa diakses dari perangkat itu sendiri. Jalankan server di sesi tmux supaya tidak mati saat Termux berpindah layar.

Notifikasi memakai termux-notification (perlu aplikasi Termux:API). Tanpa itu, job tetap berjalan dan notifikasi dilewati.

## Mode di UI

- Forge: menerjemahkan chapter yang dicentang, lalu membuat hasil penuh dalam format yang dipilih (EPUB atau DOCX).
- Radar: memindai entitas novel ke glosarium baru. Tidak menerjemahkan.

Pilihan Paralel chapter (default mati) menerjemahkan dua chapter bersamaan. Lebih cepat, tapi kuota Gemini bisa habis lebih cepat.

Centang "Terjemahkan ulang chapter yang dipilih" untuk mengulang chapter tertentu. Progres lama langsung dihapus, tanpa cadangan.

## Fitur di UI

- Dapur: pengaturan job (novel, mode, format, glosarium, paralel, terjemahkan ulang) dan tombol Mulai/Berhenti.
- Pustaka: file hasil yang bisa diunduh. File diunduh sekali lalu dihapus dari folder hasil.
- Jelajah: cari novel di folder Download.
- Perlu diulang: chapter yang gagal, dengan jumlah chunk yang selesai, jumlah peringatan, dan tiga alasan terakhir dari log.
- Log terbaru: log per job, termasuk tiap agent saat paralel.
- Editor glosarium: cari, filter, urutan, dan tanda entri baru dari scan.
- Ikon dan manifest untuk shortcut di layar utama.
- Saat job berjalan, centang chapter mengikuti pilihan job itu, bukan default.

## CLI

    python main.py input/novel.epub -o temp/novel.epub --project-dir temp/novel_project --chapter 2-5
    python main.py input/novel.epub --status --project-dir temp/novel_project
    python main.py input/novel.epub -o temp/novel.epub --export-chapters --workers 2
    python main.py input/novel.epub --scan-glossary glossary/novel.txt --project-dir temp/novel_project

Flag utama: --chapter (N, START-END, atau daftar dengan koma), --workers (default 1), --glossary, --export-chapters, --chapter-output-dir, --status, --scan-glossary.

## Glosarium

- Format: `Asal = Indonesia`. Baris yang diawali `#` dinonaktifkan dan diabaikan.
- Alias dengan awalan `~`, misalnya `~Rudy = Rudeus Greyrat`.
- Pencocokan peka huruf besar-kecil dan memakai batas kata. `Lady` diganti, `lady` sebagai kata biasa tidak.
- Gelar dan panggilan (Lady, Lord, Sir, Mr., Mrs., Miss, Master) diterjemahkan lewat entri sendiri. Nama di belakangnya tidak diterjemahkan.
- Radar menulis nama inti tanpa gelar atau sapaan. Variasi seperti `Subaru-kun` dan `Mr. Subaru` digabung menjadi `Subaru`.
- Entri yang tidak muncul di teks sumber selama 20 chapter dihapus dari file, tanpa konfirmasi. Entri dengan `#` tidak disentuh. Penghitungan dimulai dari entri yang ada sekarang, dan setiap chapter dihitung sekali.

## Aturan terjemahan dan QA

- Separator yang hanya berisi simbol (misalnya `△ ▼ △ ▼`) dan baris yang hanya berisi URL dibiarkan seperti aslinya.
- Judul berkutip pendek tanpa tanda baca (sampai delapan kata) tidak dianggap bahasa Inggris yang tertinggal. Dialog tetap diperiksa.
- URL diabaikan saat pemeriksaan bahasa Inggris.
- Judul chapter yang gagal diterjemahkan dipakai apa adanya, dan chapter tetap diproses.

## Output dan nama file

- Hasil penuh: `(ID in Converïse) <judul>_<tanggal>.<ext>` untuk EPUB ke EPUB atau DOCX ke DOCX. `(ID by Converïse)` untuk DOCX ke EPUB.
- Chapter export: `chapter-NN.xhtml` di dalam EPUB, satu file per chapter.
- DOCX dengan minimal dua Heading 1 dipisah per chapter. Pada EPUB dari DOCX, setiap chapter menjadi halaman sendiri dan punya entri daftar isi. Batas chapter diambil dari hasil terjemahan, bukan dari deteksi heading.
- Output penuh tidak dibuat kalau ada chapter gagal atau chunk yang ditandai. Ulangi chapter yang gagal, lalu jalankan lagi.

## Struktur

- main.py: pipeline CLI untuk terjemahan, scan glosarium, dan ekspor chapter
- ui/: antarmuka lokal, editor glosarium, dan notifikasi (job_notify.py)
- parsers/: parser EPUB/DOCX dan perbaikan EPUB sumber
- research/: deteksi dan riset entitas (dipakai Radar)
- translation/: chunking, terjemahan, refinement, penerjemah judul, glosarium, dan aturan jangan-diterjemahkan (keep_rules.py)
- qa/: pemeriksaan aturan dan kontrol retry
- storage/: progres, cache, log, dan statistik
- reconstruction/: rakit ulang EPUB/DOCX dan validasi
- config/: pengaturan, batas retry, dan provider
- tests/: tes utama. Dijalankan dengan `pytest`
- tests/legacy/: tes lama, tetap dijalankan
- scripts/manual/: skrip manual yang memanggil API. Tidak dijalankan pytest
- docs/shortcuts.md: keputusan sementara di kode yang perlu diingat

## Data lokal (tidak di Git)

- input/: novel asli. Hanya fixture tes yang ikut di Git.
- glossary/: glosarium per novel, `glossary/.entities/` untuk hasil riset per seri, dan `glossary/.usage/` untuk penghitungan pemakaian.
- temp/: progres (`progress/`), cache, log, statistik (`stats/`), daftar chapter (`chapters.json`), dan hasil build.

## Tes

    python -m pytest -q

## Keamanan

API key diambil dari environment variable dan tidak boleh di-commit. File .env sudah diabaikan oleh Git. Jangan menulis kunci di log atau chat.

## Status

Dalam pengembangan aktif.
