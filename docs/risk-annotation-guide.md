# Panduan anotasi Risk AI

Dua anotator memberi label risiko pada setiap skenario di `ml/risk/annotations/anotator_A.csv` dan `anotator_B.csv`, **secara terpisah dan tanpa saling melihat**. Kesepakatan keduanya diukur dengan Cohen's kappa. Label final adalah label yang disepakati. Skenario yang tidak disepakati dibahas bersama, lalu hasilnya diisi di `ml/risk/data/disagreements.csv` (kolom `label_final`).

## Yang dinilai

Nilai **seberapa besar kerugian jika konten itu dibuat dan tersebar**, hanya dari isi kontennya: tujuan, siapa yang terlibat (diri sendiri, orang lain, tidak ada orang), jenis media, seberapa nyata hasilnya, seberapa besar orang atau ucapannya diubah, konteks sensitif, dan suara sintetis.

**Jangan** mempertimbangkan apakah pemilik sudah memberi izin atau persetujuan. Itu urusan policy engine, bukan Risk AI (CLAUDE.md bagian 8). Nilai seolah-olah belum ada izin apa pun.

## Tingkat

| Label | Skor | Arti | Contoh |
| --- | --- | --- | --- |
| LOW | di bawah 30 | Kerugian kecil, mudah dikenali sebagai buatan AI, atau hanya menyangkut diri sendiri | Avatar kartun diri sendiri; mencerahkan foto; karikatur yang jelas bercanda tentang orang tak dikenal |
| MEDIUM | 30 sampai 59 | Bisa merugikan kepentingan orang (uang, reputasi ringan, privasi) jika tanpa izin, tetapi tidak menipu publik | Iklan memakai wajah orang lain; poster dukungan politik yang jelas bertanda AI; tujuan tidak jelas |
| HIGH | 60 sampai 84 | Bisa menyesatkan orang banyak atau merugikan serius satu orang | Pengumuman palsu yang realistis; suara sintetis yang meminta uang; satire fotorealistik tentang pejabat |
| CRITICAL | 85 ke atas | Kerugian berat dan sulit dipulihkan | Konten seksual orang nyata; fitnah kriminal fotorealistik; peniruan pejabat dalam konteks pemilu atau bencana |

## Aturan bantu

1. Konten seksual yang melibatkan orang nyata selain diri sendiri minimal CRITICAL.
2. Realisme tinggi dan manipulasi tinggi bersama-sama umumnya menaikkan satu tingkat.
3. Konteks sensitif (anak, agama, pemilu, bencana, keuangan, hukum) umumnya menaikkan satu tingkat.
4. Suara sintetis pada permintaan yang menyangkut uang atau pernyataan resmi minimal HIGH.
5. Jika ragu antara dua tingkat, pilih yang lebih tinggi dan tulis alasannya di kolom `catatan`.
6. Target "tanpa orang" atau "diri sendiri" umumnya lebih rendah daripada orang lain, kecuali kontennya menipu publik.

## Langkah

1. `python ml/risk/scenarios.py` sudah dijalankan. Jangan jalankan ulang setelah anotasi dimulai.
2. Anotator A mengisi `anotator_A.csv`, anotator B mengisi `anotator_B.csv`. Kolom `label` diisi `LOW`, `MEDIUM`, `HIGH`, atau `CRITICAL`.
3. Jalankan `python ml/risk/kappa.py` dan catat kappa. Kappa di bawah 0,6 berarti panduan ini perlu diperjelas sebelum lanjut.
4. Bahas baris di `ml/risk/data/disagreements.csv`, isi `label_final`, lalu jalankan `kappa.py` lagi.
5. Jalankan `python ml/risk/train.py`.

Target minimum: 300 skenario berlabel oleh kedua anotator. Jika belum tercapai, laporkan jumlah sebenarnya.
