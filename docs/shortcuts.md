# Shortcut yang perlu diingat

Keputusan sementara di kode. Tiap entri menyebut file, nomor baris, dan batasannya.
Daftar ini dibuat ulang lewat command yang sama setiap ada perubahan besar.

- `main.py:532`: shortcut: cocokkan nama file saja, aset dengan nama sama di tempat lain ikut tersimpan
- `main.py:1239`: shortcut: sebelum run pertama, jumlah chapter bisa beda dari run (AI classifier); sama setelah run
- `main.py:1325`: shortcut: bagian sangat pendek (sampul, daftar isi, promo) dilewati supaya tidak memakai panggilan riset
- `main.py:1329`: shortcut: semua bagian ikut diriset, termasuk halaman non-cerita; penyaringan menyusul
- `qa/rule_based_qa.py:203`: shortcut: hanya pola panah "->" atau "→", echo tanpa panah belum tertangkap, naikkan jika muncul lagi
- `reconstruction/epub_reconstructor.py:622`: shortcut: lang="en" di halaman terjemahan diganti "id", span Inggris ikut berubah, naikkan jika muncul
- `reconstruction/epub_reconstructor.py:921`: shortcut: EPUB sumber tanpa nav (mis. EPUB 2 ber-NCX) diberi daftar isi baru agar EPUB 3 valid
- `reconstruction/epub_validator.py:356`: shortcut: hanya EPUB 3 yang diperiksa, NCX pada EPUB 2 belum
- `reconstruction/xhtml_text_injector.py:102`: shortcut: judul bertanda \u241e disisip utuh ke node pertama, teks lain dibagi proporsional
- `translation/chapter_title_translator.py:97`: shortcut: kunci cache hanya judul asli; dua novel dengan judul sama memakai terjemahan yang sama
- `translation/glossary.py:32`: shortcut: kata asal yang terpotong antar run formatting (miring/tebal) belum tergantikan
- `translation/glossary.py:59`: shortcut: pembandingan per kata; ejaan beda tanpa kata yang sama (mis. 'Manggod' vs 'Man-God') belum digabung
- `translation/model_client.py:17`: shortcut: hanya aktif kalau WN_USAGE_FILE diset (lewat UI), supaya tes dan CLI tidak menulis file
- `translation/model_client.py:109`: shortcut: deteksi kuota harian dari teks pesan Gemini; kalau formatnya berubah, cek lagi di sini
- `ui/glossary_page.py:87`: shortcut: catatan komentar yang memuat titik atau titik dua dianggap bukan entri; nama asal dengan titik perlu dicek
- `ui/server.py:354`: shortcut: dihitung per hari lokal; kuota Gemini reset mengikuti zona waktu Pasifik, jadi angkanya perkiraan
- `ui/server.py:442`: shortcut: mt_v15 memakai folder lama temp/mt_project, novel lain punya folder sendiri
- `ui/server.py:531`: shortcut: hanya proses dari UI ini yang terdeteksi, proses tmux lain di luar UI tidak
