# Shortcut yang perlu diingat

Keputusan sementara di kode. Tiap entri menyebut file, lalu nama fungsi bila ada. Nomor baris di bagian pertama berasal dari versi sebelumnya dan bisa sudah bergeser, jadi cari dengan nama fungsi.

## Entri lama (nomor baris bisa bergeser)

- `main.py:532`: cocokkan nama file saja, aset dengan nama sama di tempat lain ikut tersimpan (`_slim_chapter_epub`)
- `main.py:1239`: sebelum run pertama, jumlah chapter bisa beda dari run (AI classifier); sama setelah run (`show_status`)
- `main.py:1325`: bagian sangat pendek (sampul, daftar isi, promo) dilewati supaya tidak memakai panggilan riset (`scan_glossary_file`)
- `main.py:1329`: semua bagian ikut diriset, termasuk halaman non-cerita; penyaringan menyusul (`scan_glossary_file`)
- `qa/rule_based_qa.py:203`: hanya pola panah "->" atau "→", echo tanpa panah belum tertangkap, naikkan jika muncul lagi
- `reconstruction/epub_reconstructor.py:642`: lang="en" di halaman terjemahan diganti "id", span Inggris ikut berubah, naikkan jika muncul
- `reconstruction/epub_reconstructor.py:951`: EPUB sumber tanpa nav (mis. EPUB 2 ber-NCX) diberi daftar isi baru agar EPUB 3 valid
- `reconstruction/epub_validator.py:356`: hanya EPUB 3 yang diperiksa, NCX pada EPUB 2 belum
- `reconstruction/xhtml_text_injector.py:102`: judul bertanda \u241e disisip utuh ke node pertama, teks lain dibagi proporsional
- `translation/chapter_processor.py:79`: chunk kosong (pemisah adegan atau gambar) tidak dikirim ke model
- `translation/chapter_processor.py:144`: model kadang menggabung atau melewatkan paragraf di chunk besar; chunk dibelah dua lalu diulang
- `translation/chapter_title_translator.py:97`: kunci cache hanya judul asli; dua novel dengan judul sama memakai terjemahan yang sama
- `translation/glossary.py:45`: kata asal yang terpotong antar run formatting (miring/tebal) belum tergantikan
- `translation/glossary.py:83`: pembandingan per kata; ejaan beda tanpa kata yang sama (mis. 'Manggod' vs 'Man-God') belum digabung
- `translation/model_client.py:17`: hanya aktif kalau WN_USAGE_FILE diset (lewat UI), supaya tes dan CLI tidak menulis file
- `translation/model_client.py:109`: deteksi kuota harian dari teks pesan Gemini; kalau formatnya berubah, cek lagi di sini
- `translation/refinement_engine.py:124`: refinement yang jumlah paragrafnya salah dibuang; chunk tidak digagalkan
- `ui/glossary_page.py:106`: catatan komentar yang memuat titik atau titik dua dianggap bukan entri; nama asal dengan titik perlu dicek
- `ui/server.py:487`: dihitung per hari lokal; kuota Gemini reset mengikuti zona waktu Pasifik, jadi angkanya perkiraan
- `ui/server.py:505`: cache hasil yang sudah lolos QA tetap dipakai, jadi terjemahan ulang bisa langsung dari cache
- `ui/server.py:773`: mt_v15 memakai folder lama temp/mt_project, novel lain punya folder sendiri
- `ui/server.py:876`: hanya proses dari UI ini yang terdeteksi, proses tmux lain di luar UI tidak
- `ui/server.py:894`: novel baru memakai chunk lebih besar; novel yang sudah berjalan tidak diubah karena progresnya bergantung pada batas chunk lama

## Keputusan terbaru (belum ada nomor baris)

- `translation/glossary.py` (`prune_unused_entries`): entri yang tidak muncul di 20 chapter dihapus dari file tanpa konfirmasi. Entri manual yang aktif ikut terhapus; beri `#` untuk melindungi.
- `translation/keep_rules.py` (`keep_source`): paragraf tanpa huruf dan baris hanya-URL tidak dikirim ke terjemahan. Teks asli dipakai apa adanya.
- `qa/rule_based_qa.py`: URL diabaikan saat pemeriksaan bahasa Inggris. Judul berkutip sampai delapan kata tanpa tanda baca tidak ditandai. Dialog dengan tanda baca tetap diperiksa.
- `main.py` (`process_chapters`): judul yang gagal diterjemahkan dipakai apa adanya dan chapter tetap diproses.
- `main.py` (`process_chapters`, `--workers`): mode paralel hanya menerjemahkan chapter di thread lain. Judul, QA, perakitan, dan ekspor tetap berurutan di thread utama.
- `reconstruction/epub_reconstructor.py` (`_build_default_structure`): sumber DOCX dipisah per chapter memakai `chapter_starts` dari hasil terjemahan. Heading 1 hanya dipakai kalau metadata itu tidak ada.
- `ui/job_notify.py`: notifikasi memakai nama mode Forge dan Radar. Notifikasi selesai memuat nama novel, jumlah chapter, waktu, dan chapter yang perlu diulang.
- `ui/server.py` (`save_selection`, `load_selection`): pilihan chapter job disimpan di `last_selection.json` dan dipakai untuk centang saat job berjalan.
- `ui/server.py` (`retire_progress`): progres chapter yang dipilih dihapus langsung, tanpa folder retired dan tanpa cadangan.
