# Progres pengembangan ARMOR

Dokumen status untuk perintah `/otomatis` dan untuk tim. Urutan fase: 0, 1, 2, 3, 4, 5, 6, 6b, 7, 8, 9, 10a, 10b, 10c, 10d, 10e, 10f, 11, 12.

## Status fase

| Fase | Status | Commit |
| --- | --- | --- |
| Awal | Selesai | `2ec74d9` |
| 0 | Selesai | `3649ac6` |
| 1 | Selesai | `78287e1` |
| 2 | Selesai | `2f03f1c` |
| 3 | Selesai | `6c1cef7` |
| 4 | Selesai | `f8b16bb` |
| 5 | Selesai | `94052da` |
| 6 | Selesai | `8233412` |
| 6b | Selesai | `4e67ec2` |
| 7 | Selesai | (lihat log di bawah) |
| 8 | Belum | |
| 9 | Belum | |
| 10a | Belum | |
| 10b | Belum | |
| 10c | Belum | |
| 10d | Belum | |
| 10e | Belum | |
| 10f | Belum | |
| 11 | Belum | |
| 12 | Belum | |

## Menunggu tim

| Prioritas | Hal | Dibutuhkan untuk | Langkah persis |
| --- | --- | --- | --- |
| Tinggi | Isi data penanggung jawab di `docs/consent-form-relawan.md`, cetak, dan kumpulkan tanda tangan relawan | Fase 3, 9, 10b, 11 | Ganti `[nama ketua tim]` dan `[email kontak tim]`, lalu sebar formulir sebelum mengambil foto atau rekaman. |
| Tinggi | Kumpulkan foto wajah relawan dan percobaan serangan enrollment | Angka Face AI Bab 7 (TAR/FAR/EER, ambang, serangan) | Ikuti `ml/face_eval/README.md`: minimal 20 relawan (3 foto enrollment + 8 sampai 10 foto probe), 10 percobaan untuk tiap serangan (layar, cetak, sudah terdaftar). Simpan di `ml/face_eval/data/` (tidak di-commit), lalu jalankan `embed.py`, `evaluate.py`, `attacks.py`. |
| Tinggi | Unduh model InsightFace `buffalo_l` ke laptop demo | Face AI asli, demo offline | Ikuti `ml/models/README.md` (butuh internet sekali, dan Microsoft C++ Build Tools untuk memasang insightface di Windows). |
| Tinggi | Ganti ambang placeholder wajah dengan hasil evaluasi | Keputusan wajah yang terukur | Salin `FACE_MATCH_THRESHOLD` dan `FACE_GRAY_MARGIN` dari `docs/eval/face.md` ke `backend/.env`. |
| Tinggi | Periksa dataset Intent AI (3.500 prompt + 90 parafrase) | Angka Intent AI Bab 7 yang sah (saat ini EKSPERIMEN) | Ikuti `docs/intent-labeling-guide.md`: buka `ml/intent/dataset/intent_dataset.csv` dan `paraphrase.csv`, periksa label, perbaiki kalimat janggal, isi `diperiksa_oleh`. Lalu `python ml/intent/dataset/generate.py --check`, `python ml/intent/train_baseline.py`, `python ml/intent/select_model.py`. |
| Tinggi | Tambah prompt alami tulisan tim, terutama eufemisme kelas berbahaya | Tingkat lolos parafrase (saat ini 18,4%) | Tambahkan baris `sumber=manual`, `split=train`/`val`, id `MAN-xxxxx` ke `intent_dataset.csv` (lihat `ml/intent/README.md`). Jangan menyalin dari `paraphrase.csv` dan jangan menambah `split=test`. |
| Tinggi | Anotasi risiko oleh dua anotator terpisah | Model Risk AI asli dan angka Bab 7 (macro F1, kappa) | Ikuti `docs/risk-annotation-guide.md`: dua orang mengisi `ml/risk/annotations/anotator_A.csv` dan `anotator_B.csv` tanpa saling melihat (minimal 300 skenario), jalankan `python ml/risk/kappa.py`, bahas `ml/risk/data/disagreements.csv`, lalu `python ml/risk/train.py`. |
| Sedang | Latih IndoBERT di GPU | Perbandingan Intent AI Bab 7 | Buka Colab/Kaggle dengan GPU, jalankan langkah di docstring `ml/intent/train_indobert.py`, unduh `ml/models/intent/indobert/` dan `indobert_report.json` ke laptop, lalu `python ml/intent/select_model.py`. Cek dan catat lisensi checkpoint di `docs/TECH_LIST.md`. |
| Sedang | Tinjau teks persetujuan lapis 1 | Enrollment wajah dan suara | Baca `docs/consent-text/face-v1.md` dan `voice-v1.md`; jika diubah, buat versi baru (misalnya `face-v2.md`) dan naikkan `CONSENT_TEXT_FACE`. |
| Sedang | Tunjuk peninjau dan admin | Konsol peninjau, banding, sengketa | Setelah akun mereka mendaftar: `cd backend` lalu `python -m app.cli role grant --email <email> --role REVIEWER` (atau `ADMIN`). |
| Rendah | Aktifkan email (opsional, bukan untuk demo offline) | Notifikasi email | Isi `EMAIL_ENABLED=true`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` di `backend/.env` dengan akun SMTP tim. |
| Sedang | Ekspor desain Claude Design (jika tim memakainya) | Kesesuaian tampilan dengan desain tim | Semua layar Fase 7 diturunkan dari CLAUDE.md bagian 10 dan `docs/design/intro-reference.dc.html`. Jika ada ekspor Claude Design, simpan di `docs/design/` lalu jalankan `/fase 7` untuk menyelaraskan layar yang berbeda. |
| Sedang | Uji aplikasi di ponsel asli dengan pembaca layar | Aksesibilitas nyata, kamera depan, pemasangan PWA | Jalankan backend dan `npm run dev` di `app/`, buka dari ponsel di jaringan yang sama (atur `NEXT_PUBLIC_API_URL` ke IP laptop dan tambahkan origin ponsel ke `CORS_ORIGINS`), coba enrollment dengan kamera depan dan navigasi dengan TalkBack. |
| Sedang | Sambungkan repo ke GitHub (privat) agar CI jalan | CI, kerja paralel 4 anggota | Buat repo privat kosong di GitHub, lalu di `E:\armor`: `git remote add origin <url>` dan `git push -u origin main`. |



## Log per fase

### Fase 0: persiapan monorepo

- **Commit:** `3649ac6`
- **Ringkasan:** Struktur monorepo sesuai CLAUDE.md bagian 4 dibuat (`backend/`, `ml/`, `generator_mock/`, `app/`, `docs/`). `.gitignore` sekarang mengabaikan rahasia, venv, artefak model, dan semua folder media/dataset relawan; `.gitattributes` menyeragamkan akhir baris. `backend/.env.example` memuat semua kunci konfigurasi (termasuk `ARMOR_EMBEDDING_KEY` dan `FACE_GRAY_MARGIN`), dan `backend/scripts/gen_secrets.py` membuat `JWT_SECRET` serta kunci Fernet baru. Ruff dan pytest dikonfigurasi di `backend/pyproject.toml`; requirements dipisah menjadi core, ml, dan dev agar CI tidak memasang model berat. Workflow CI menjalankan ruff dan pytest. Riwayat git lama tidak berisi rahasia; repo baru belum pernah memuat `.env`, `.venv`, atau `.pkl`.
- **Hasil tes:** 46 lulus, 0 gagal. `ruff check` dan `ruff format --check` bersih.
- **Perlu diperiksa manusia:** formulir consent relawan; bahwa `requirements.txt` lengkap masih bisa dipasang di laptop demo (insightface butuh compiler C++ di Windows).

### Fase 1: menutup celah keamanan

- **Commit:** `78287e1`
- **Ringkasan:** Sepuluh celah yang terbukti (ditambah 9b: mengunci identitas orang lain) kini punya tes regresi di `backend/tests/security/test_fase1_security.py` yang gagal pada kode lama dan lulus sesudahnya. Perbaikan: kepemilikan dicek pada enroll, verify, profile, lock, dan permission; consent wajib login, requester diambil dari token, hanya pemilik yang menjawab; policy menerapkan Identity Lock; riwayat dan log hanya milik sendiri; semua ID memakai UUID; respons ke requester tidak lagi membocorkan identitas target, skor, izin, atau consent, dengan pesan seragam. Server juga menolak menyala di produksi dengan rahasia bawaan atau CORS `*`. Tabel sebelum vs sesudah ada di `docs/eval/security-fase1.md`.
- **Hasil tes:** 61 lulus, 0 gagal (46 lama, 12 keamanan, 3 config). Ruff bersih.
- **Perlu diperiksa manusia:** tabel Bab 7.2; tiga tes lama yang disesuaikan karena mengukuhkan celah (dicatat di `docs/AI_USAGE.md`).

### Fase 2: model domain dan policy engine multimodal

- **Commit:** `2f03f1c`
- **Ringkasan:** Enum kanonik CLAUDE.md bagian 6 berlaku di seluruh backend. Policy engine ditulis ulang: menerima daftar target (sumber, jenis target, identitas, skor, Lock, consent, izin, lingkaran tepercaya, wali) beserta intent, risiko, jenis media, dan realisme; menerapkan aturan mutlak, gagal aman, dan matriks per target; lalu mengambil keputusan paling ketat. Keluarannya: keputusan, reason code, alasan bahasa Indonesia, saran prompt, pesan requester yang seragam, dan detail per target untuk pemilik dan audit. Izin disimpan per intent x media (bawaan wajah sesuai CLAUDE.md, suara bawaan DENY, empat intent berbahaya terkunci DENY). Lock diatur per media dengan tiga tingkat. Consent punya cakupan intent dan media. Gateway `/requests` dan `/decision` memakai engine baru. Selama fase ini ditemukan bahwa `backend/app/models/` tidak pernah ter-commit karena pola `.gitignore` lama; sudah diperbaiki.
- **Hasil tes:** 185 lulus, 0 gagal. Cakupan `app/policy` 100% (baris dan cabang). Ruff bersih.
- **Perlu diperiksa manusia:** (1) tafsiran bahwa izin ALLOW = consent tetap; (2) teks alasan dan saran prompt di `backend/app/policy/explain.py`; (3) commit `awal`, `fase-0`, dan `fase-1` tidak memuat `backend/app/models/*.py`, jadi checkout commit lama itu tidak bisa dijalankan; mulai commit Fase 2 lengkap; (4) skema basis data berubah: hapus `backend/armor.db` lokal sebelum menjalankan server (belum ada migrasi).

### Fase 3: Face AI opt-in

- **Commit:** `6c1cef7`
- **Ringkasan:** Galeri wajah tokoh dan klien identifikasi lama dihapus; Gemini tidak lagi menerima gambar atau ditanya soal identitas. Face AI baru mendeteksi semua wajah dengan satu pipeline InsightFace untuk enrollment dan inferensi, lengkap dengan cek kualitas (ukuran, blur, pose). Enrollment memakai 3 tangkapan dengan sudut berbeda dan persetujuan lapis 1 yang tercatat beserta versi teksnya; menolak kualitas buruk, orang berbeda, sudut yang tidak berubah (foto layar/cetak), dan wajah yang sudah terdaftar (membuka kasus sengketa). Embedding rata-rata disimpan terenkripsi Fernet; foto tidak disimpan. Gateway mencocokkan setiap wajah ke seluruh enrollment dan menghasilkan SELF, OTHER_REGISTERED, OTHER_UNREGISTERED, atau UNCLEAR (zona abu-abu); klien tidak bisa lagi menyebut target, sehingga consent kini diajukan per `request_id` dan pemilik punya kotak consent dasar. Pemilik bisa mencabut persetujuan per media, menghapus identitas, dan mengunduh datanya. Skrip evaluasi `ml/face_eval` (TAR pada FAR 1% dan 0,1%, EER, ROC, rekomendasi ambang, uji serangan enrollment) siap dan sudah diuji jalan dengan data SINTETIS.
- **Hasil tes:** 248 lulus, 1 dilewati (tes model asli, InsightFace belum terpasang), 0 gagal. Tes `ml/face_eval`: 8 lulus. Ruff bersih.
- **Perlu diperiksa manusia:** teks persetujuan lapis 1; kebijakan bahwa skor di zona abu-abu saat enrollment dianggap duplikat (dikirim ke sengketa); estimasi yaw/pitch dari 5 landmark bersifat kasar dan perlu dicek dengan foto nyata; skema basis data berubah lagi (hapus `backend/armor.db` lokal).

### Fase 4: Intent AI

- **Commit:** `f8b16bb`
- **Ringkasan:** Dataset Intent AI dibuat dari template untuk 10 kelas, dua bahasa, dan tiga media (3.500 prompt, split beku 2.450/520/530 dengan hash set uji), ditambah 90 parafrase/eufemisme tulisan tangan sebagai set ketahanan. Panduan pelabelan ditulis, dan training final ditolak selama masih ada baris yang belum diperiksa. Baseline TF-IDF + LR dilatih sebagai eksperimen; ambang UNCERTAIN dipilih dari data validasi; laporan per kelas, recall kelas berbahaya, confusion matrix, dan hasil parafrase ada di `docs/eval/intent.md`. Skrip IndoBERT siap untuk GPU. Backend memuat model aktif (`ml/models/intent/active.json`) dengan fallback keyword, Gemini tidak lagi dipakai untuk intent, dan setiap log keputusan mencatat versi model.
- **Hasil tes:** backend 254 lulus, 1 dilewati, 0 gagal; `ml/` 15 lulus; ruff bersih.
- **Hasil eksperimen (bukan final):** set uji template macro F1 1,000 (menghafal template, tidak bermakna); set parafrase macro F1 0,485, recall berbahaya 0,358, tingkat lolos 0,184.
- **Perlu diperiksa manusia:** pemeriksaan dataset; kualitas kalimat template bahasa Inggris; keputusan bahwa pemilihan model memprioritaskan tingkat lolos di set parafrase. File model `.joblib` tidak di-commit: jalankan `python ml/intent/train_baseline.py --allow-unreviewed` (atau tanpa flag setelah diperiksa) di laptop demo agar backend memakai model, bukan fallback.

### Fase 5: Risk AI

- **Commit:** `94052da`
- **Ringkasan:** Risk AI menilai isi konten saja (intent, keyakinan, jenis target, media, realisme, manipulasi, konteks sensitif, suara sintetis); consent dan izin bukan fitur. Realisme, manipulasi, dan konteks sensitif diekstrak dari prompt dengan aturan kata kunci terdokumentasi dan teruji. Generator 600 skenario dan lembar anotasi dua anotator siap, beserta skrip Cohen's kappa dan penggabungan label. Training membandingkan Logistic Regression dan Random Forest dengan validasi silang dan memilih berdasarkan macro F1. Backend menghitung skor 0-100 dari probabilitas berbobot, level, dan tiga fitur paling berpengaruh; tanpa model hasil anotasi manusia dipakai tabel per intent. Realisme kini mengaktifkan aturan satire fotorealistik di policy. Gemini dihapus seluruhnya.
- **Hasil tes:** backend 292 lulus, 1 dilewati, 0 gagal; `ml/` 20 lulus; ruff bersih.
- **Perlu diperiksa manusia:** panduan anotasi dan kata kunci fitur. Backend memakai tabel fallback risiko sampai anotasi selesai.

### Fase 6: gateway lengkap dan fitur pemilik

- **Commit:** `8233412`
- **Ringkasan:** Gateway kini lewat Media Router dan mencatat waktu tiap tahap; video dan audio ditandai tidak tersedia (gagal aman) sampai Fase 9 dan 10b. Keputusan REVIEW ditahan (HELD) dan otomatis dinilai ulang begitu pemilik menjawab consent, lalu requester mendapat notifikasi. Consent punya cakupan dan masa berlaku (sekali pakai, 1/7/30 hari, tanggal), bisa dicabut, kedaluwarsa otomatis, dan pengirim bisa diblokir; batas 3 permintaan per hari per identitas. Lingkaran tepercaya, notifikasi (email opsional), audit log berantai hash dengan verifikasi, dasbor aktivitas, dan kasus banding/sengketa lengkap dengan peran peninjau, pembekuan, pindah kepemilikan, dan hapus pendaftaran palsu. CLI untuk peran, akun platform, pembersihan log 90 hari. Unggahan divalidasi dari isi berkas dan ukurannya dibatasi.
- **Hasil tes:** 330 lulus, 1 dilewati, 0 gagal; cakupan `app/` 94%, `app/policy` 100%; ruff bersih.
- **Perlu diperiksa manusia:** alur peninjau dan teks notifikasi. Skema basis data berubah lagi (hapus `backend/armor.db` lokal).

### Fase 6b: loop pembelajaran

- **Commit:** `4e67ec2`
- **Ringkasan:** Requester bisa mengizinkan prompt-nya dipakai untuk perbaikan model (bawaan mati; klausul di `docs/TERMS.md`). Hasil manusia (REVIEW yang selesai, jawaban consent, banding dan koreksi label peninjau) menjadi label di tabel `feedback`, tanpa media. Tim mengekspor dan memeriksa feedback, lalu `ml/retrain.py` melatih ulang Intent AI atau Risk AI dan hanya memakai model baru jika macro F1 dan recall kelas berbahaya di set uji beku tidak turun. Setiap percobaan tercatat di `versions.json` dan `docs/eval/retrain.md`; versi yang pernah dipakai bisa dikembalikan. `model_version` sudah tercatat di setiap log keputusan sejak Fase 4.
- **Hasil tes:** backend 335 lulus, 1 dilewati; `ml/` 25 lulus (termasuk tes model lebih buruk ditolak); ruff bersih.
- **Perlu diperiksa manusia:** klausul ketentuan layanan. Retrain nyata menunggu feedback dari pemakaian aplikasi.

### Fase 7: aplikasi

- **Commit:** (lihat tabel status). Bagian: 7a `2920578` (+ perbaikan `fd70a0e`), 7b `ccf8da2`, 7c `203ed1f`.
- **Ringkasan:** Aplikasi Next.js 16 mobile-first dan PWA di `app/`, tersambung ke semua endpoint backend lewat klien bertipe dari OpenAPI, diekspor statis agar bisa jalan offline. Semua layar 1 sampai 12 CLAUDE.md bagian 10 selesai: intro dan sambutan, cara kerja, daftar/masuk, enrollment wajah dengan persetujuan lapis 1 dan kamera tiga sudut (cadangan unggah berkas), beranda, periksa dan hasil beserta alasan dan saran, banding, kotak consent (cakupan, masa berlaku, cabut, blokir), identitas (Lock, izin intent x media, lingkaran tepercaya), aktivitas, data saya (unduh, hapus dua langkah), notifikasi, akun, kasus, ketentuan dan privasi (draf). Teks persetujuan dan legal diambil dari `docs/` saat build. Tidak ada ekspor Claude Design, sehingga semua layar diturunkan dari CLAUDE.md bagian 10 dan `intro-reference.dc.html`: intro/sambutan (langsung dari referensi), cara kerja, daftar, masuk, enroll, beranda, periksa, hasil, banding, consent, detail consent, identitas, izin, lingkaran, aktivitas, data saya, notifikasi, akun, kasus, ketentuan, privasi.
- **Hasil tes:** `tsc` dan ESLint bersih; build statis 24 rute; Playwright 4 lulus (alur intro, daftar, enroll kamera palsu, periksa, hasil; periksa teks; axe WCAG 2.1 AA tanpa pelanggaran di 5 layar publik dan 12 layar setelah masuk); Lighthouse aksesibilitas: intro 95, layar publik lain 100. Backend 337 lulus, 1 dilewati.
- **Catatan:** commit `2920578` masuk dengan 3 tes backend gagal (kode keluar pytest tertutup `| tail`, tes membaca `.env` pengembang); diperbaiki di `fd70a0e`. Server statis sederhana (misalnya `python -m http.server`) memberi 404 untuk berkas prefetch segmen Next (`__next.<rute>.__PAGE__.txt`, sedangkan berkasnya di `__next.<rute>/__PAGE__.txt`); navigasi tetap jalan karena Next jatuh ke pengambilan biasa. Penyajian dari backend di Fase 12 memetakan nama itu.
- **Perlu diperiksa manusia:** tampilan di ponsel asli dan dengan TalkBack; semua teks UI; kesesuaian dengan desain tim; draf `docs/PRIVACY.md` dan `docs/TERMS.md` (difinalkan di Fase 11).
