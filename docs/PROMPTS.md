# Prompt pengembangan ARMOR dengan Claude Code

## Cara pakai

1. Buat folder repo baru `armor/`, taruh `CLAUDE.md` di root-nya, dan salin `intro-reference.dc.html` ke `docs/design/`. Setelah prototipe Claude Design selesai, ekspor hasilnya (file layar dan tangkapan layar tiap layar) ke `docs/design/` juga, sebelum Fase 7.
2. Salin folder `armor-backend` lama ke `armor/backend/`, tanpa `.venv`, `.env`, dan folder `.git` di dalamnya. Notebook eksperimen lama TIDAK dimasukkan ke repo; simpan sebagai arsip pribadi tim.
3. Buka Claude Code di folder `armor/`. Kirim **Prompt Pembuka**, lalu prompt fase sesuai jadwal di bawah. Fase 0, 1, dan 2 harus selesai lebih dulu karena fase lain bergantung pada enum dan policy baru.
4. Setelah tiap fase: baca ringkasannya, jalankan aplikasinya sendiri, dan cek hasilnya. Juri bisa bertanya detail kode, jadi setiap anggota harus paham bagian yang ia pegang.
5. Logo: salin `armor-mark.png` ke `app/public/` (file referensi desain merujuk ke nama itu).
6. Cara tercepat menjalankan fase: salin file `fase.md` ke `armor/.claude/commands/fase.md`. Setelah itu, di Claude Code cukup ketik `/fase 0`, `/fase 1`, `/fase 6b`, `/fase 10a`, dan seterusnya. Setelah selesai dan diperiksa, ketik `/clear` sebelum fase berikutnya.

### Cakupan

**Semua fase (0 sampai 12) masuk prototipe lomba.** Tidak ada fitur rancangan yang dipotong. Yang tidak dikerjakan hanya hal yang memang mustahil dalam lomba dan tetap ditulis sebagai rencana produksi di proposal: lisensi model wajah komersial (harus dibeli), audit independen (harus pihak luar), dan uji bias skala besar (butuh ribuan relawan).

### Jadwal 5 hari untuk 4 anggota

Setiap anggota menjalankan sesi Claude Code sendiri di branch masing-masing, lalu digabung (merge) ke `main` setiap malam setelah tes lulus.

| Hari | Anggota 1: backend, keamanan, policy | Anggota 2: Face AI dan Voice AI | Anggota 3: Intent, Risk, Text Matcher | Anggota 4: aplikasi dan desain |
| --- | --- | --- | --- | --- |
| 0 (hari ini) | Fase 0 | Sebar formulir consent, mulai kumpulkan foto dan rekaman relawan | Mulai buat dan periksa dataset prompt | Siapkan proyek Next.js dan token desain |
| 1 | Fase 1, lalu Fase 2 (selesaikan pagi, yang lain menunggu enum final) | Fase 3 | Fase 4 (dataset, baseline) | Fase 7a: intro, sambutan, autentikasi |
| 2 | Fase 6 | Fase 9, evaluasi wajah dengan data relawan | Fase 4 (IndoBERT), mulai anotasi Fase 5 | Fase 7b: enrollment wajah, analisis request |
| 3 | Fase 8 | Fase 10b (Voice AI) | Fase 5, Fase 10a | Fase 7c: consent, identitas saya, dasbor, data saya |
| 4 | Fase 10c, 10d, 10e | Evaluasi suara, Output Guard audio | Fase 6b (loop pembelajaran) | Fase 10f: layar untuk fitur Fase 8 sampai 10 |
| 5 | Fase 11 dan 12 bersama: angka untuk Bab 7, deploy, video demo, kirim | | | |

Hambatan terbesar bukan kode, melainkan data yang harus dibuat manusia: foto dan rekaman relawan, pemeriksaan dataset prompt, dan anotasi risiko oleh dua orang. Mulai hari ini. Jika pada hari ke-5 jumlah data belum mencapai target, laporkan jumlah sebenarnya di proposal, jangan dibulatkan.

---

## Prompt Pembuka

```
Baca CLAUDE.md sampai selesai. Itu spesifikasi lengkap proyek ARMOR dan aturan yang wajib kamu ikuti.

Setelah itu:
1. Jelajahi isi repo (backend/, docs/design/) dan jelaskan singkat kondisi kode yang ada.
2. Sebutkan bagian kode lama yang bertentangan dengan CLAUDE.md (misalnya galeri wajah tokoh, pemanggilan Gemini untuk identifikasi, celah kepemilikan).
3. Jangan ubah kode dulu. Tunggu prompt fase berikutnya.
```

---

## Fase 0: Persiapan repo

```
Fase 0: siapkan monorepo ARMOR sesuai struktur di CLAUDE.md bagian 4.

Tugas:
1. Rapikan struktur folder: backend/, ml/, generator_mock/, app/, docs/. Pindahkan kode backend lama ke backend/ tanpa mengubah perilakunya.
2. Buat .gitignore sesuai CLAUDE.md bagian 9. Pastikan tidak ada .env, .venv, *.pkl, atau media yang ter-commit. Jika ada di riwayat git, laporkan ke saya.
3. Buat backend/.env.example lengkap (DATABASE_URL, JWT_SECRET, ARMOR_EMBEDDING_KEY, MODEL_DIR, FACE_MATCH_THRESHOLD, FACE_GRAY_MARGIN, dll.) dengan nilai contoh yang aman. Buat skrip kecil untuk menghasilkan JWT_SECRET dan ARMOR_EMBEDDING_KEY baru.
4. Tambahkan ruff dan konfigurasi pytest. Pastikan 46 tes lama tetap lulus.
5. Buat docs/AI_USAGE.md, docs/TECH_LIST.md (isi dari CLAUDE.md bagian 5), dan docs/consent-form-relawan.md (formulir persetujuan pengambilan foto wajah dan rekaman suara untuk relawan: data apa, tujuan, lama simpan, cara mencabut, tanda tangan).
6. Tambahkan workflow CI sederhana (GitHub Actions) yang menjalankan ruff dan pytest backend.
7. Tulis README.md root: cara menjalankan backend, tes, dan struktur repo.

Kriteria selesai: pytest lulus, ruff bersih, tidak ada rahasia di repo, commit "fase-0: persiapan monorepo".
```

---

## Fase 1: Menutup celah keamanan

```
Fase 1: tutup celah keamanan backend. Setiap celah harus punya tes regresi yang sebelumnya gagal dan sekarang lulus.

Celah yang sudah terbukti:
1. Akun lain bisa me-enroll ulang identity_id milik orang lain dan menjadi pemiliknya, lalu request-nya dianggap SELF dan ALLOW.
2. Siapa pun yang login bisa mengubah permission identitas orang lain.
3. /consent/request dan /consent/respond tidak butuh login, sehingga siapa pun bisa menyetujui consent atas nama pemilik.
4. Status Identity Lock disimpan tetapi tidak pernah dicek policy.
5. GET /requests dan /logs menampilkan riwayat semua pengguna.
6. request_id dan consent_id dibuat dari hitungan baris (race condition).
7. /identity/verify bisa dipakai siapa saja untuk mencocokkan wajah ke identity_id mana pun (menjadi alat pengecek identitas orang lain).
8. /identity/profile bisa membaca identitas milik orang lain.
9. /identity/lock bisa "mengklaim" identity_id yang belum terdaftar.
10. Respons /requests membocorkan match_score dan identity_id target ke requester (melanggar aturan pesan seragam).

Tugas:
- Tulis dulu tes untuk skenario serangan di atas (tests/security/), jalankan, dan tunjukkan bahwa tes itu gagal.
- Perbaiki: /identity/verify hanya untuk memverifikasi wajah terhadap identitas milik sendiri; /identity/profile hanya milik sendiri; /identity/lock hanya untuk identitas yang sudah terdaftar dan dimiliki pemanggil; respons /requests ke requester tidak memuat match_score, identity_id target, atau detail per target (detail hanya untuk pemilik dan audit log); cek kepemilikan di enroll, permission, lock; consent/respond hanya oleh pemilik identitas (401 tanpa login, 403 bukan pemilik); consent/request butuh login dan requester_id diambil dari token, bukan body; Lock dipakai policy (sementara: target OTHER pada identitas Locked = DENY); riwayat hanya milik sendiri; semua ID pakai UUID.
- Semua error memakai envelope yang sudah ada.

Kriteria selesai: semua tes lama dan tes keamanan lulus, commit "fase-1: tutup celah keamanan", entri baru di docs/AI_USAGE.md. Laporkan tabel "sebelum vs sesudah" per skenario untuk Bab 7.2 proposal.
```

---

## Fase 2: Model domain dan policy engine baru

```
Fase 2: perbarui enum dan policy engine sesuai CLAUDE.md bagian 6 dan 7.

Tugas:
1. Ganti enum di schema/common.py dengan enum kanonik (IdentityTarget 4 nilai, Intent 10 kelas, MediaType, TargetSource, LockLevel, ConsentStatus). Perbarui normalizer dan keyword fallback untuk kelas baru SATIRE_PARODY dan SEXUAL_EXPLICIT.
2. Tulis ulang policy/engine.py:
   - input: daftar target (masing-masing: source, target type, identity_id opsional, skor, status lock, consent, izin, anggota lingkaran tepercaya, wali) + intent + confidence + risk level + media type + realism;
   - urutan: aturan mutlak, aturan gagal aman, matriks per target, ambil keputusan paling ketat;
   - output: decision, reason_code, reason (bahasa Indonesia), suggestion, requester_message (seragam, tidak membocorkan status terdaftar), per_target_detail (untuk pemilik dan audit).
3. Buat policy/explain.py berisi template alasan dan saran prompt per reason_code. Bahasa Indonesia yang wajar, tanpa em dash.
4. Tes table-driven yang mencakup SETIAP sel matriks, setiap aturan mutlak, multi-target (paling ketat menang), satire kartun vs fotorealistik, dan pesan seragam.
5. Perbarui izin bawaan per intent x media sesuai CLAUDE.md bagian 6. Model Permission menyimpan media.
6. LockLevel per media (FACE, VOICE) pada identitas; endpoint /identity/lock menerima level dan media.

Kriteria selesai: semua tes lulus, cakupan tes policy 100%, commit "fase-2: policy engine multimodal".
```

---

## Fase 3: Face AI opt-in

```
Fase 3: bangun ulang Face AI sesuai CLAUDE.md bagian 2 dan 8.

Tugas:
1. Hapus registry galeri tokoh (app/ai/registry.py dan semua pemakaiannya). Hapus semua pemanggilan Gemini untuk identifikasi. Catat penghapusan di docs/AI_USAGE.md.
2. app/ai/face.py:
   - deteksi SEMUA wajah dengan InsightFace FaceAnalysis.get (pipeline yang sama untuk enrollment dan inferensi);
   - cek kualitas: ukuran wajah minimum, blur (varian Laplacian), pose (yaw/pitch dari landmark) dengan ambang di config;
   - kembalikan daftar wajah: bbox, embedding, skor kualitas.
3. Enrollment wajah: POST /identity/enroll menerima 3 foto pose berbeda (base64). Tolak jika kualitas buruk, jika 3 pose tidak saling cocok (orang berbeda), atau jika sudut pose (yaw) tidak cukup berbeda antar-tangkapan (mencegah foto dari layar/foto cetak yang diam). Cek duplikat ke seluruh embedding terdaftar; jika cocok dengan identitas lain, tolak dan buat kasus sengketa. Simpan rata-rata embedding terenkripsi Fernet. Foto tidak disimpan.
   Enrollment wajib menyertakan persetujuan lapis 1: simpan catatan consent (FACE, versi teks dari docs/consent-text/, waktu). Tanpa catatan ini enrollment ditolak.
4. Penentuan target di gateway: setiap wajah dicocokkan ke embedding requester dan ke semua embedding terdaftar. Hasil: SELF, OTHER_REGISTERED (dengan identity_id), OTHER_UNREGISTERED (embedding langsung dibuang), UNCLEAR (kualitas rendah atau skor di zona abu-abu). identity_id dari klien tidak lagi dipercaya.
5. DELETE /identity/me (hapus semua), POST /identity/me/revoke?media=FACE|VOICE (cabut persetujuan satu media: catatan consent diberi waktu cabut dan embedding media itu dihapus), dan GET /me/data (unduh data milik sendiri dalam JSON, tanpa embedding mentah, termasuk riwayat consent lapis 1).
6. ml/face_eval/: skrip evaluasi dari folder foto relawan (struktur folder per orang). Hitung pasangan sama dan berbeda, TAR pada FAR 1% dan 0,1%, EER, kurva ROC (PNG), dan rekomendasi ambang + margin abu-abu. Tambahkan uji serangan enrollment: foto dari layar, foto cetak, dan wajah yang sudah terdaftar, lalu laporkan persentase yang tertolak. Simpan hasil ke docs/eval/face.md. Jangan mengarang angka; jika folder data belum ada, buat instruksi pengumpulan data di README folder itu.
7. Buat docs/consent-text/face-v1.md dan voice-v1.md: teks persetujuan lapis 1 yang jelas (data apa, tujuan, lama simpan, cara mencabut). Teks ini juga dipakai di aplikasi.
8. Tes: gunakan embedding sintetis (vektor acak ternormalisasi) agar tes tidak butuh model. Tambahkan satu tes opsional yang dilewati jika model tidak tersedia.

Kriteria selesai: tidak ada lagi kode yang mengenali nama dari wajah, tes lulus, commit "fase-3: face ai opt-in".
```

---

## Fase 4: Intent AI

```
Fase 4: bangun Intent AI sesuai CLAUDE.md bagian 8.

Tugas:
1. ml/intent/dataset/: skema CSV (id, prompt, bahasa, media, intent, sumber, diperiksa_oleh). Buat generator template + variasi untuk 10 kelas, bahasa Indonesia dan Inggris, untuk gambar, video, dan audio. Target 3.500 prompt, split 70/15/15 berstrata, split dibekukan dengan seed. Buat juga set terpisah berisi parafrase dan eufemisme untuk uji ketahanan.
2. Buat docs/intent-labeling-guide.md: definisi tiap kelas, contoh batas antar-kelas (satire vs fitnah, komersial vs politik), dan aturan untuk kasus ragu.
3. Tandai kolom diperiksa_oleh kosong; tim memeriksa manual sebelum training final. Skrip harus menolak training final jika ada baris yang belum diperiksa (bisa di-override dengan flag untuk eksperimen).
4. ml/intent/train_baseline.py: TF-IDF (word + char n-gram) + Logistic Regression. Simpan model dan laporan: macro F1, F1 per kelas, recall kelas berbahaya, confusion matrix (PNG), hasil di set parafrase.
5. ml/intent/train_indobert.py: fine-tune IndoBERT, siap dijalankan di Colab/Kaggle (GPU), dengan laporan format yang sama.
6. Pilih ambang confidence untuk UNCERTAIN dari data validasi.
7. backend/app/ai/intent.py: memuat model terbaik, fallback ke keyword jika model tidak ada, output kelas + confidence.
8. Simpan laporan perbandingan ke docs/eval/intent.md.

Kriteria selesai: skrip jalan end-to-end dengan dataset yang ada, backend memakai model, tes lulus, commit "fase-4: intent ai".
```

---

## Fase 5: Risk AI

```
Fase 5: bangun Risk AI sesuai CLAUDE.md bagian 8. Ingat: consent dan izin BUKAN fitur Risk AI.

Tugas:
1. ml/risk/: skema skenario (intent, confidence, target_type, media, realism, manipulation, sensitive_context, synthetic_voice) dan generator kombinasi skenario yang realistis.
2. docs/risk-annotation-guide.md: definisi LOW/MEDIUM/HIGH/CRITICAL dengan contoh.
3. Format anotasi untuk dua anotator terpisah dan skrip Cohen's kappa. Label final = kesepakatan, sisanya dibahas.
4. Training LR dan Random Forest, pilih berdasarkan macro F1. Laporan: F1 per level, kappa, bobot/importance fitur (PNG). Simpan ke docs/eval/risk.md.
5. backend/app/ai/risk.py: skor 0-100 (probabilitas berbobot) + level sesuai ambang CLAUDE.md, plus 3 fitur paling berpengaruh untuk ARMOR Explain. Fallback tabel risiko per intent jika model tidak ada.
6. Ekstraksi fitur realism, manipulation, sensitive_context dari prompt (aturan kata kunci yang terdokumentasi + tes).

Kriteria selesai: tes lulus, commit "fase-5: risk ai".
```

---

## Fase 6: Gateway lengkap dan fitur pemilik

```
Fase 6: satukan semua komponen di gateway dan lengkapi fitur pemilik identitas.

Tugas:
1. app/ai/router.py (Media Router): terima gambar, video, atau audio + prompt. Arahkan ke komponen yang tersedia; komponen yang belum ada (voice, video) mengembalikan status "tidak tersedia" dan policy memperlakukannya dengan aturan gagal aman.
2. POST /requests: router -> target -> intent -> risk -> policy -> explain -> simpan log -> respons. Satu panggilan per komponen per request. Catat waktu per tahap.
3. Kotak consent: GET /consent/inbox (pemilik, filter menunggu/dijawab), POST /consent/{id}/respond dengan cakupan (intent, media, masa berlaku: sekali pakai, 1 hari, 7 hari, 30 hari, atau tanggal), tolak, atau blokir requester. Request yang tertahan dilanjutkan atau ditolak otomatis setelah dijawab. Consent sekali pakai hangus setelah dipakai; consent berjangka kedaluwarsa otomatis. POST /consent/{id}/revoke agar pemilik bisa mencabut consent yang sudah diberikan kapan saja. Consent kedaluwarsa atau dicabut dianggap NONE oleh policy.
4. Identity Lock 3 tingkat per media, lingkaran tepercaya (tambah/hapus akun + cakupan), izin per intent x media.
5. Notifikasi dalam aplikasi (tabel notifications + endpoint baca/tandai dibaca), ditambah notifikasi email opsional lewat SMTP yang bisa dimatikan di config (mati saat demo offline).
6. Rate limit sesuai CLAUDE.md bagian 9.
7. Audit log berantai hash + endpoint verifikasi integritas rantai.
8. GET /dashboard/activity: jumlah upaya penggunaan identitas pemilik, yang diblokir, yang disetujui, per minggu. Identitas requester hanya tampil jika ia mengajukan consent.
9. Kasus: POST /cases (banding atas DENY, sengketa pendaftaran palsu), status diajukan -> ditinjau -> selesai. Peran REVIEWER melihat kasus yang ditugaskan saja. Sengketa: pelapor melakukan verifikasi ulang wajah/suara secara langsung; jika cocok dengan identitas yang disengketakan dan bukan pemiliknya, peninjau dapat membekukan identitas itu, lalu memindahkan kepemilikan ke pelapor atau menghapus pendaftaran palsu. Semua tindakan peninjau tercatat di audit log.
10. Perintah CLI: memberi dan mencabut peran REVIEWER/ADMIN, membuat akun platform.
11. Pembersihan log lebih dari 90 hari (perintah CLI atau tugas terjadwal).
12. Batas ukuran unggahan dan validasi tipe berkas dari isi (magic bytes) untuk gambar, video, dan audio; pesan error yang jelas.
13. CORS dibaca dari config: `*` hanya di dev, origin frontend di produksi.
14. Perbarui OpenAPI docs dengan contoh request/response dalam bahasa Indonesia.

Kriteria selesai: tes integrasi untuk alur consent lengkap, lock, lingkaran tepercaya, banding; commit "fase-6: gateway lengkap".
```

### Fase 6b: Loop pembelajaran

```
Fase 6b: bangun loop pembelajaran berkelanjutan untuk Intent AI dan Risk AI.

Tugas:
1. Tabel feedback: setiap keputusan REVIEW yang diselesaikan, hasil banding, dan keputusan consent menghasilkan label (prompt, intent final, risk final, sumber label). Simpan hanya jika requester menyetujui pemakaian promptnya untuk perbaikan model (tambahkan persetujuan ini di ketentuan layanan dan di layar request). Tanpa media.
2. Peninjau dapat mengoreksi label intent/risk saat menutup kasus.
3. ml/retrain.py: gabungkan dataset asli + feedback yang sudah diperiksa, latih ulang, evaluasi pada set uji BEKU yang tidak pernah bercampur dengan feedback. Model baru hanya menggantikan model lama jika macro F1 tidak turun dan recall kelas berbahaya tidak turun (gerbang evaluasi).
4. Versi model tercatat (model_version di setiap log keputusan) dan bisa dikembalikan ke versi sebelumnya.
5. Perintah CLI untuk menjalankan retrain dan laporan perbandingan versi di docs/eval/retrain.md.

Kriteria selesai: tes untuk gerbang evaluasi (model lebih buruk ditolak), commit "fase-6b: loop pembelajaran".
```

---

## Fase 7: Aplikasi frontend

```
Fase 7: bangun aplikasi di app/ dengan Next.js (App Router, TypeScript), mobile-first, sesuai CLAUDE.md bagian 10. Patuhi aturan anti "AI slop" tanpa pengecualian.

Sumber desain: ikuti hasil Claude Design di docs/design/ (layar, komponen, keadaan, alur). Jika sebuah layar belum ada di sana, turunkan dari sistem desain yang sama. Laporkan layar yang kamu turunkan sendiri.

Kerjakan dalam tiga bagian dengan commit terpisah: 7a (layar 1, 2, 3), 7b (layar 4, 5, 6), 7c (layar 7 sampai 12). Layar untuk fitur Fase 8 sampai 10 dibuat di Fase 10f.

Layar dan urutan pengerjaan:
1. Intro + sambutan: port desain docs/design/intro-reference.dc.html ke komponen React. Logo 3D (lapisan bertumpuk + rotasi + kilatan cahaya bermask bentuk logo), tiga slogan zoom dengan font stensil dan kilatan layar, animasi scan wajah, layar sambutan dengan logo 3D melayang. Tombol Lewati, prefers-reduced-motion.
2. Cara kerja ARMOR: alur pemeriksaan dan dua lapis perlindungan dalam bentuk visual.
3. Autentikasi (daftar, masuk) dengan pesan error di dekat field.
4. Enrollment wajah: consent lapis 1 dari docs/consent-text/face-v1.md dengan centang eksplisit, ambil 3 pose dari kamera (getUserMedia) dengan panduan pose, umpan balik kualitas, penanganan wajah sudah terdaftar (arahkan ke sengketa), hasil.
5. Beranda dan tab bar (Beranda, Periksa, Consent dengan badge, Identitas, Akun): status perlindungan wajah dan suara, ringkasan aktivitas, permintaan consent terbaru.
6. Analisis request: pilih jenis masukan (gambar, video, audio, atau teks saja), unggah media + tulis prompt, persetujuan opsional pemakaian prompt untuk perbaikan model, animasi pemeriksaan yang menampilkan tahap nyata dari backend (termasuk hasil per wajah/suara/nama tanpa membocorkan status terdaftar orang lain), hasil ALLOW/REVIEW/DENY dengan alasan dan saran prompt (ARMOR Explain) yang bisa diketuk, tombol ajukan banding saat DENY, keadaan UNCLEAR dan gagal aman.
7. Kotak consent: daftar menunggu/dijawab, detail, setujui dengan cakupan dan masa berlaku (termasuk sekali pakai), tolak, blokir, cabut consent yang sudah diberikan, status kedaluwarsa.
8. Identitas saya: tingkat Lock per media, izin per tujuan x media, lingkaran tepercaya.
9. Dasbor aktivitas.
10. Data saya: data yang disimpan beserta lama simpannya, unduh, cabut persetujuan per media, hapus identitas (konfirmasi dua langkah).
11. Notifikasi: daftar semua notifikasi, tandai dibaca.
12. Akun: profil, sakelar notifikasi email, ketentuan layanan, kebijakan privasi, keluar. Plus keadaan kosong dan error di semua layar (tanpa koneksi, izin kamera/mikrofon ditolak, berkas terlalu besar, batas permintaan consent tercapai, pengirim diblokir).

Teknis:
- Klien API bertipe dari OpenAPI backend.
- Font via next/font/google: Big Shoulders Display, Big Shoulders Stencil Display, Atkinson Hyperlegible.
- Semua teks antarmuka bahasa Indonesia, tanpa em dash, tanpa label pengisi.
- Bisa diinstal sebagai PWA dan berjalan penuh dengan backend lokal (tanpa internet).
- Tes Playwright untuk alur: intro -> daftar -> enroll (mock kamera) -> request -> hasil.

Kriteria selesai: semua layar tersambung ke backend, Lighthouse aksesibilitas >= 90, commit "fase-7: aplikasi".
```

---

## Fase 8: Generator tiruan, Output Guard, ARMOR Shield

```
Fase 8: lengkapi jalur setelah ALLOW.

Tugas:
1. generator_mock/: layanan FastAPI kecil yang mensimulasikan AI generatif (misalnya transformasi gaya gambar dengan Pillow/OpenCV dan komposisi sederhana). Jelas ditandai sebagai simulasi. Sediakan mode uji yang sengaja menghasilkan gambar berisi wajah terdaftar untuk menguji Output Guard.
   Buat antarmuka generator yang bisa ditukar (GeneratorAdapter). Selain mock, sediakan adapter opsional untuk model generatif lokal sungguhan (misalnya Stable Diffusion img2img lewat diffusers) yang aktif hanya jika ada GPU dan bobot model sudah diunduh. Mock tetap bawaan agar demo offline di laptop tanpa GPU tetap berjalan. Catat lisensi model generatif di docs/TECH_LIST.md.
2. Output Guard: hasil generator diperiksa ulang oleh Face AI. Jika muncul identitas terdaftar yang tidak diizinkan, hasil ditahan, dicatat, dan pemilik mendapat notifikasi.
3. ARMOR Shield untuk gambar: label kecil terlihat "Dibuat dengan AI · ARMOR", metadata di PNG (id keputusan, waktu, status izin; ikuti pola C2PA semampunya), hash SHA-256 dan perceptual hash disimpan di registry.
4. POST /shield/verify dan halaman verifikasi publik di aplikasi: unggah gambar -> tampilkan apakah dibuat lewat ARMOR, kapan, dan status izinnya (cocokkan metadata, lalu hash, lalu perceptual hash).

Kriteria selesai: skenario 15 dan 16 di CLAUDE.md Lampiran A lulus sebagai tes otomatis, commit "fase-8: output guard dan shield".
```

---

## Fase 9: Video

```
Fase 9: dukungan video untuk Face AI.

Tugas:
1. Ambil frame 2 per detik (OpenCV), deteksi dan lacak wajah antar-frame (IoU + kemiripan embedding), gabungkan skor per jejak.
2. Batas durasi dan ukuran berkas di config; tolak dengan pesan jelas jika melebihi.
3. Fitur jenis media VIDEO masuk ke Risk AI.
4. Generator mock untuk video (misalnya filter gaya pada setiap frame) lewat GeneratorAdapter, Output Guard untuk video (sampel frame), dan Shield untuk video (metadata kontainer + hash) beserta verifikasi publiknya.
5. ml/face_eval: evaluasi akurasi target per klip dari video relawan.
6. Sambungkan ke Media Router dan POST /requests: video kini diproses Face AI (frame) dan trek audionya diteruskan ke Voice AI saat Fase 10b selesai. Hapus status "tidak tersedia" untuk video.

Kriteria selesai: skenario 14 lulus, waktu proses dilaporkan, commit "fase-9: video".
```

---

## Fase 10: Text Identity Matcher, Voice AI, mode wali, takedown, API platform, layar lanjutan

```
Fase 10: kerjakan bagian ini bertahap, commit per sub-bagian.

10a. Text Identity Matcher: endpoint untuk mengelola nama/alias milik sendiri (wajib alias unik untuk nama umum), normalisasi, NER, rapidfuzz. Sambungkan ke Media Router untuk prompt dan transkrip, sehingga menghasilkan target TEXT. Uji precision/recall dengan set prompt berisi nama, alias, salah ketik, dan nama lain; simpan ke docs/eval/text-matcher.md. Skenario 13 lulus.

10b. Voice AI:
- ECAPA embedding (SpeechBrain), Whisper untuk transkrip, model anti-spoof (cek dan catat lisensinya).
- Enrollment suara: wajib catatan consent lapis 1 VOICE (docs/consent-text/voice-v1.md), 3 kalimat acak ditampilkan, rekaman dicek transkripnya harus cocok, anti-spoof harus lolos, embedding rata-rata terenkripsi, rekaman dibuang, cek duplikat (jika cocok dengan identitas lain, buat kasus sengketa).
- Sambungkan ke Media Router: audio dan trek audio video diproses Voice AI. Hapus status "tidak tersedia" untuk suara.
- Target per suara + penanda sintetis; transkrip masuk ke Intent AI dan Text Identity Matcher.
- ml/voice_eval: EER dan persentase spoof terdeteksi dari rekaman relawan (termasuk rekaman ulang dan suara sintetis dengan izin relawan).
- Watermark AudioSeal untuk Shield audio, dan verifikasi publik untuk audio (deteksi watermark).
- Output Guard untuk audio: hasil generator audio diperiksa Voice AI; suara terdaftar yang tidak diizinkan ditahan.
- Generator mock untuk audio (misalnya perubahan pitch/kecepatan pada rekaman) agar alur audio bisa didemokan.
- Skenario 17, 18, 19 lulus.

10c. Mode wali: akun wali mendaftarkan anak; semua penggunaan identitas anak DENY. Skenario 20 lulus.

10d. Asisten laporan dan takedown: pemilik unggah konten mencurigakan -> cek wajah/suara dan Shield -> draf laporan (teks) berisi bukti.

10e. API untuk platform: akun platform, API key, rate limit per key, dokumentasi integrasi singkat, dan contoh klien kecil (Python dan JavaScript) yang memanggil ARMOR sebelum memanggil generator.

10f. Layar aplikasi untuk semua fitur Fase 8 sampai 10, dengan aturan desain yang sama seperti Fase 7:
- consent lapis 1 untuk suara dan enrollment suara (3 kalimat acak, rekam, umpan balik, keadaan rekaman ulang/sintetis terdeteksi, suara sudah terdaftar) serta pengaturan Lock/izin untuk suara;
- keadaan hasil khusus audio dan video di layar analisis (kloning suara ditolak, suara sintetis terdeteksi, progres frame video);
- nama dan alias;
- mode wali (tambah anak, status perlindungan);
- verifikasi publik ARMOR Shield (gambar, video, audio), bisa dibuka tanpa login;
- banding atas DENY dan sengketa pendaftaran palsu (dengan verifikasi ulang lewat kamera/mikrofon), beserta status kasus;
- konsol peninjau (peran reviewer): daftar kasus yang ditugaskan, detail, keputusan, koreksi label;
- asisten laporan dan takedown;
- halaman akun platform: buat dan cabut API key, lihat pemakaian;
- notifikasi Output Guard untuk pemilik.
Tes Playwright untuk alur banding dan verifikasi publik.

Kriteria selesai per sub-bagian: tes lulus, entri AI_USAGE, commit "fase-10x: ...".
```

---

## Fase 11: Evaluasi dan pengujian menyeluruh

```
Fase 11: siapkan semua angka untuk Bab 7 proposal. Jangan mengarang angka apa pun.

Tugas:
1. tests/scenarios/: 20 skenario end-to-end dari CLAUDE.md Lampiran A sebagai tes otomatis (A dan B terdaftar, C tidak terdaftar). Semua fitur seharusnya sudah ada; jika ada skenario yang gagal, perbaiki kodenya, bukan tesnya.
2. Jalankan semua skrip evaluasi yang datanya tersedia (face, voice, intent, risk). Untuk yang datanya belum ada, tulis "belum dijalankan: data belum tersedia".
3. Benchmark waktu keputusan per jenis media (rata-rata dan p95) di laptop demo.
4. Uji bias sederhana Face AI per kelompok (jika atribut kelompok relawan dicatat dengan izin).
5. Buat docs/eval/RINGKASAN.md: tabel siap salin untuk Bab 7 proposal, mencakup semua metrik di CLAUDE.md Lampiran C, lengkap dengan cara mereproduksi setiap angka.
6. Model card untuk setiap model (Face, Voice, Text Matcher, Intent, Risk) di docs/model-cards/: tujuan, data, metrik, keterbatasan, lisensi, penggunaan yang tidak boleh.
7. docs/DPIA.md: penilaian dampak pelindungan data singkat (1-2 halaman) sesuai UU PDP: data yang diproses, dasar pemrosesan, risiko bagi subjek data, mitigasi, retensi, hak subjek data.
8. docs/threat-model.md: uji setiap baris model ancaman di CLAUDE.md Lampiran B dan catat hasilnya.
9. docs/TERMS.md dan docs/PRIVACY.md: ketentuan layanan dan kebijakan privasi ARMOR dalam bahasa Indonesia yang jelas (data yang diproses, tujuan, dasar pemrosesan, lama simpan, hak pengguna menurut UU PDP, pemakaian prompt untuk perbaikan model yang bersifat opsional, kontak). Tampilkan di layar Akun. Tandai sebagai draf yang perlu ditinjau manusia.

Kriteria selesai: RINGKASAN.md hanya berisi angka dari eksekusi nyata, commit "fase-11: evaluasi".
```

---

## Fase 12: Deploy dan pengumpulan

```
Fase 12: siapkan deploy, demo offline, dan berkas pengumpulan lomba.

Tugas:
1. Dockerfile backend dan generator_mock, docker-compose.yml untuk menjalankan seluruh sistem di satu laptop. Skrip untuk mengunduh semua model sebelumnya agar demo berjalan tanpa internet.
2. Deploy daring untuk tautan juri: frontend (misalnya Vercel) dan backend (misalnya Hugging Face Spaces Docker atau Railway). Tulis langkahnya di docs/DEPLOY.md. Pastikan tidak ada data wajah relawan di server publik; gunakan akun demo.
3. Seed data demo: akun A, B (terdaftar, dengan izin yang sesuai skenario), dan media C yang aman dipakai (misalnya foto anggota tim yang setuju, bukan orang lain).
4. docs/DEMO.md: naskah demo 15 menit mengikuti skenario CLAUDE.md Lampiran A dan lima jalur demo dari prototipe Claude Design, plus daftar pengecekan sebelum tampil.
5. Checklist rekam video demo cadangan (wajib karena demo butuh backend).
6. Perbarui README, docs/TECH_LIST.md (semua teknologi + lisensi), dan docs/AI_USAGE.md (ringkasan penggunaan Claude Code per fase dan kontribusi tim).
7. Berkas APK (opsional tapi disarankan, karena panitia menerima APK sebagai bentuk prototipe): bungkus PWA menjadi APK Android (Trusted Web Activity lewat Bubblewrap, atau Capacitor), arahkan ke backend daring, dan tulis cara membangunnya di docs/DEPLOY.md.
8. Pastikan CORS produksi hanya mengizinkan origin frontend, repositori publik tidak memuat rahasia atau data relawan, dan README menjelaskan cara menjalankan demo offline.

Kriteria selesai: `docker compose up` menjalankan seluruh demo offline, tautan daring bisa dibuka, commit "fase-12: siap kumpul".
```

---

## Prompt bantuan (pakai kapan saja)

**Review sebelum commit**
```
Review perubahan di fase ini terhadap CLAUDE.md: prinsip bagian 2, aturan keamanan bagian 9, dan aturan anti AI slop bagian 10. Daftar pelanggaran yang kamu temukan beserta perbaikannya, lalu perbaiki.
```

**Menjelaskan kode untuk persiapan tanya jawab juri**
```
Jelaskan cara kerja [nama modul] untuk mahasiswa yang akan ditanya juri: alur data, keputusan desain, keterbatasan, dan 5 pertanyaan juri yang paling mungkin beserta jawabannya.
```

**Saat ada bug**
```
Ada bug: [jelaskan gejala, langkah reproduksi, log]. Tulis dulu tes yang mereproduksi bug ini, pastikan gagal, baru perbaiki. Jangan ubah perilaku lain.
```
