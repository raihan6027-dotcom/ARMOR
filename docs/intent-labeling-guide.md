# Panduan pelabelan Intent AI

Dipakai tim saat memeriksa `ml/intent/dataset/intent_dataset.csv` dan `paraphrase.csv`. Setiap baris yang sudah diperiksa diisi kolom `diperiksa_oleh` dengan inisial pemeriksa (misalnya `RA`). Skrip training final menolak jalan selama masih ada baris kosong.

Label intent menjawab satu pertanyaan: **apa tujuan requester terhadap orang di dalam media?** Bukan apakah permintaan itu boleh. Keputusan boleh atau tidak diambil policy engine.

## Definisi kelas

| Kelas | Definisi | Contoh |
| --- | --- | --- |
| PERSONAL_CREATION | Membuat karya baru untuk dipakai sendiri atau keluarga, tanpa tujuan komersial, politik, atau merugikan | Avatar kartun untuk foto profil; narasi dongeng dengan suara sendiri |
| PERSONAL_EDITING | Memperbaiki atau mengubah ringan media yang sudah ada, tanpa mengubah makna | Mencerahkan foto; menghapus bising di rekaman |
| SATIRE_PARODY | Lelucon atau kritik yang **jelas** bukan kejadian nyata (karikatur, kartun, meme) | Karikatur kepala besar; parodi superhero kikuk |
| COMMERCIAL_USE | Memakai orang untuk menjual, mempromosikan, atau mengiklankan | Iklan kopi; endorse skincare; jingle radio |
| POLITICAL_USE | Memakai orang untuk kampanye, dukungan calon atau partai, ajakan memilih | Poster pemilu; pidato partai |
| IMPERSONATION | Membuat orang seolah mengatakan atau melakukan sesuatu yang tidak ia lakukan, atau menyamar sebagai dia | Lip-sync pengumuman mundur; suara tiruan menyetujui kontrak |
| DEFAMATION | Membuat orang terlihat bersalah, hina, atau tercela (kriminal, narkoba, mabuk, dipermalukan) | Baju tahanan dan borgol; menerima suap |
| SEXUAL_EXPLICIT | Ketelanjangan, pose atau adegan seksual, konten dewasa | Tanpa busana; adegan 18+ |
| DECEPTIVE | Memakai orang untuk menipu atau menyesatkan publik (penipuan uang, hoaks) | Bantuan sosial dengan biaya admin; minta transfer darurat; kabar bencana palsu |
| UNCERTAIN | Tujuan tidak bisa ditentukan dari teks | "Olah foto ini jadi sesuatu" |

## Batas antar-kelas

- **Satire vs fitnah.** Satire harus jelas bercanda dan tidak menuduh perbuatan nyata. "Karikatur kepala besar" = SATIRE_PARODY. "Karikatur dia sedang menerima suap" = DEFAMATION, karena menuduh perbuatan tercela. Satire yang realistis (fotorealistik) tetap diberi label SATIRE_PARODY di dataset; policy engine yang mengubahnya menjadi DEFAMATION/DECEPTIVE berdasarkan fitur realisme dari Risk AI.
- **Peniruan vs penipuan.** Jika inti permintaannya adalah **ucapan palsu** (orang seolah mengatakan sesuatu), labelnya IMPERSONATION. Jika inti permintaannya **mengambil uang atau data korban**, labelnya DECEPTIVE, walaupun memakai suara tiruan ("minta transfer" = DECEPTIVE).
- **Komersial vs politik.** Menjual barang atau jasa = COMMERCIAL_USE. Mengajak memilih, mendukung calon, partai, atau kebijakan = POLITICAL_USE. Iklan layanan masyarakat netral tanpa calon atau partai = COMMERCIAL_USE jika ada merek, UNCERTAIN jika tidak jelas.
- **Kreasi vs edit.** Karya baru (avatar, ilustrasi, animasi) = PERSONAL_CREATION. Perbaikan media yang ada tanpa mengubah maknanya = PERSONAL_EDITING. Mengganti latar belakang tetap PERSONAL_EDITING selama tidak menempatkan orang di situasi yang menuduh atau menipu.
- **Seksual vs fitnah.** Jika ada ketelanjangan atau muatan seksual, pilih SEXUAL_EXPLICIT meskipun juga mempermalukan.

## Kasus ragu

1. Pilih kelas yang **paling berbahaya** yang masuk akal dari teks. Salah label ke arah aman lebih murah daripada meloloskan konten berbahaya.
2. Jika dua pemeriksa tidak sepakat, catat di kolom `sumber` dengan akhiran `|sengketa` dan diskusikan bersama sebelum training final.
3. Jika teks tidak memberi petunjuk tujuan sama sekali, pilih UNCERTAIN.
4. Perbaiki tata bahasa prompt yang janggal langsung di CSV (misalnya kalimat bahasa Inggris hasil template yang kurang wajar), tetapi jangan ubah maknanya.

## Cara memeriksa

1. Buka CSV di spreadsheet. Jangan ubah kolom `id` dan `split`.
2. Baca `prompt`, cocokkan dengan `intent`. Ubah `intent` jika salah.
3. Isi `diperiksa_oleh` dengan inisialmu.
4. Simpan sebagai CSV UTF-8, commit, lalu jalankan `python ml/intent/dataset/generate.py --check` untuk memastikan set uji beku tidak berubah.
