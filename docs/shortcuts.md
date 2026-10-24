# Shortcut yang perlu diingat

Keputusan sementara di kode. Tiap entri menyebut file, nomor baris, dan batasannya.
Daftar ini dibuat ulang setiap ada perubahan besar.

- `main.py:532`: cocokkan nama file saja, aset dengan nama sama di tempat lain ikut tersimpan
- `main.py:1239`: sebelum run pertama, jumlah chapter bisa beda dari run (AI classifier); sama setelah run
- `main.py:1325`: bagian sangat pendek (sampul, daftar isi, promo) dilewati supaya tidak memakai panggilan riset
- `main.py:1329`: semua bagian ikut diriset, termasuk halaman non-cerita; penyaringan menyusul
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
