# ARMOR: panduan proyek untuk Claude Code

File ini adalah sumber kebenaran proyek. Baca seluruhnya sebelum mengerjakan tugas apa pun. Jika instruksi di prompt bertentangan dengan file ini, tanyakan dulu sebelum menyimpang.

## 1. Apa itu ARMOR

ARMOR (AI-Aware Identity Protection) adalah AI Safety Gateway multimodal yang berdiri di depan layanan AI generatif. Setiap permintaan (gambar, video, atau audio + prompt) diperiksa **sebelum** konten dibuat, lalu diputuskan menjadi ALLOW, REVIEW, atau DENY beserta alasannya.

Pertanyaan inti ARMOR: **apakah AI berhak memakai wajah, suara, atau nama orang ini untuk tujuan ini?**

Karya ini diikutkan KOMPRES 16 Informatika kategori AI Innovation. Bobot penilaian terbesar ada pada penerapan dan inovasi AI (30%), jadi komponen AI harus nyata, terukur, dan bisa dijelaskan.

## 2. Prinsip yang tidak boleh dilanggar

1. **Opt-in.** Database biometrik hanya berisi wajah/suara yang didaftarkan sendiri oleh pemiliknya, dengan consent tertulis. Media dari permintaan TIDAK PERNAH menambah database.
2. **Tanpa nama.** ARMOR tidak pernah mengidentifikasi nama seseorang dari wajah atau suaranya. Jawaban Identity AI hanya: SELF, OTHER_REGISTERED, OTHER_UNREGISTERED, UNCLEAR.
3. **Dilarang:** galeri wajah tokoh dari internet, dataset wajah tanpa consent di jalur produk, dan mengirim wajah/suara ke layanan AI pihak ketiga (termasuk Gemini) untuk ditebak identitasnya.
4. **AI memberi informasi, policy memutuskan.** Keputusan akhir selalu dari policy engine deterministik. Output model tidak pernah menjadi keputusan langsung.
5. **Gagal aman.** Model tidak tersedia, intent UNCERTAIN, atau skor wajah di zona abu-abu menghasilkan REVIEW. Tidak pernah ALLOW diam-diam.
6. **Minimisasi data.** Foto, video, dan rekaman hanya diproses di memori lalu dibuang. Yang disimpan: embedding terdaftar (terenkripsi), akun, consent, izin, kasus, dan log keputusan tanpa media.
7. **Kendali pemilik.** Hanya pemilik identitas yang boleh mengubah izin, Lock, lingkaran tepercaya, dan menjawab consent atas identitasnya.
8. **Bisa berjalan offline.** Demo final dilakukan luring di kampus. Seluruh jalur utama harus jalan di satu laptop tanpa internet (model diunduh sebelumnya).

## 3. Dua lapis perlindungan

- **Lapis 1, perlindungan umum (tanpa database).** Wajah/suara yang bukan milik requester dianggap OTHER. Intent IMPERSONATION, DEFAMATION, SEXUAL_EXPLICIT, DECEPTIVE terhadap OTHER selalu DENY.
- **Lapis 2, perlindungan personal (pengguna terdaftar).** Identity Lock, kotak consent, izin per tujuan dan per media, lingkaran tepercaya, mode wali, dasbor aktivitas, nama/alias.

## 3b. Daftar fitur lengkap (semua masuk prototipe lomba)

**Identitas dan enrollment**
- Enrollment wajah 3 pose dari kamera (cek kualitas, cek sudut berbeda, cek duplikat) dan enrollment suara 3 kalimat acak (cek transkrip, anti-spoofing, cek duplikat), masing-masing dengan consent lapis 1 terekam.
- Nama dan alias terdaftar untuk Text Identity Matcher.
- Mode wali: orang tua/wali mendaftarkan anak; semua penggunaan identitas anak DENY.
- Data saya: lihat data dan lama simpannya, unduh, cabut persetujuan per media, hapus identitas.

**Kendali pemilik**
- Identity Lock 3 tingkat per media (wajah, suara).
- Izin per tujuan (10 intent) x media.
- Kotak consent: setujui dengan cakupan dan masa berlaku (termasuk sekali pakai), tolak, blokir pengirim, cabut consent yang sudah diberikan, kedaluwarsa otomatis.
- Lingkaran tepercaya.
- Dasbor aktivitas: upaya penggunaan, diblokir, disetujui.
- Notifikasi dalam aplikasi (permintaan consent, upaya diblokir, Output Guard, status kasus) dan email opsional.

**Pemeriksaan permintaan**
- Masukan: gambar, video, audio, atau teks saja.
- Media Router, Face AI (termasuk video), Voice AI, Text Identity Matcher, Intent AI, Risk AI, policy engine, ARMOR Explain dengan saran prompt.
- Hasil ALLOW, REVIEW (pesan seragam), DENY, keadaan UNCLEAR dan gagal aman.

**Setelah keputusan**
- Generator lewat GeneratorAdapter (mock bawaan, model lokal opsional), untuk gambar, video, dan audio.
- Output Guard untuk gambar, video, dan audio.
- ARMOR Shield: label terlihat, metadata, hash dan perceptual hash, watermark audio; verifikasi publik tanpa login.
- Asisten laporan dan takedown.
- Banding atas DENY, sengketa pendaftaran palsu dengan verifikasi ulang, konsol peninjau dengan koreksi label.

**Platform dan tata kelola**
- API untuk platform: akun platform, API key, rate limit, contoh klien Python dan JavaScript, portal pemakaian.
- Loop pembelajaran dengan persetujuan requester dan gerbang evaluasi; `model_version` di setiap log.
- Audit log berantai hash; retensi log keputusan 90 hari lalu dihapus otomatis.
- Ketentuan layanan dan kebijakan privasi (docs/TERMS.md, docs/PRIVACY.md) yang tampil di aplikasi.
- Dokumen: DPIA singkat, model card per model, model ancaman teruji, daftar teknologi dan lisensi, catatan penggunaan AI.

**Aplikasi**
- Intro animasi, sambutan, cara kerja, daftar/masuk, beranda dengan tab bar, semua layar fitur di atas, akun, keadaan kosong dan error; PWA yang bisa berjalan offline dengan backend lokal, dibungkus juga sebagai APK.

## 4. Arsitektur

```
Request (media + prompt) -> Media Router
  -> Face AI (gambar + frame video)      -> target per wajah
  -> Voice AI (speaker + anti-spoof + ASR) -> target per suara + transkrip
  -> Text Identity Matcher (prompt + transkrip) -> target per nama/alias
  -> Intent AI (prompt + transkrip)      -> kelas + confidence
-> Risk AI (fitur konten) -> skor 0-100 + level
-> Policy Engine (per target, ambil paling ketat) + ARMOR Explain
-> ALLOW: generator (mock) -> Output Guard -> ARMOR Shield
   REVIEW: kotak consent pemilik / minta konteks
   DENY: alasan + saran prompt + banding
-> Audit log berantai hash, dasbor pemilik, loop pembelajaran
```

### Struktur repo (monorepo)

```
armor/
  CLAUDE.md
  backend/            FastAPI (turunan armor-backend yang sudah ada)
    app/
      ai/             face.py, voice.py, text_matcher.py, intent.py, risk.py, router.py
      policy/         engine.py, matrix.py, explain.py
      services/       identity, consent, permission, lock, circle, guardian, cases, shield, audit, notify
      routers/        satu file per domain
      models/         SQLAlchemy
      schema/         Pydantic + enums kanonik (common.py)
      core/           config, security, crypto, logging, ratelimit
    tests/            unit, api, integration, scenarios (20 skenario E2E)
  ml/
    intent/           dataset, training, evaluation
    risk/             dataset, anotasi, training, evaluation
    face_eval/        evaluasi TAR/FAR/EER dari data relawan
    voice_eval/       evaluasi EER + anti-spoof
    models/           artefak terlatih (gitignored kecuali file kecil)
  generator_mock/     layanan AI generatif tiruan untuk demo
  app/                frontend Next.js (mobile-first)
  docs/               AI_USAGE.md, consent-form-relawan.md, eval reports, DPIA singkat
  docker-compose.yml
```

## 5. Stack dan lisensi

| Bagian | Pilihan | Lisensi / catatan |
| --- | --- | --- |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Pydantic 2, pytest | MIT/BSD |
| Database | SQLite (dev), MySQL atau PostgreSQL (deploy) lewat `DATABASE_URL` | |
| Face | InsightFace `buffalo_l` (SCRFD + ArcFace) via `FaceAnalysis.get` | Model: riset nonkomersial saja |
| Voice | SpeechBrain `spkrec-ecapa-voxceleb`, Whisper (small/base), anti-spoof (AASIST atau setara) | Apache 2.0 / MIT / cek lisensi anti-spoof |
| Text | spaCy atau regex NER sederhana + rapidfuzz | MIT |
| Intent | scikit-learn (TF-IDF + LR) baseline; IndoBERT fine-tune pembanding | BSD / cek lisensi checkpoint |
| Risk | scikit-learn LR + Random Forest | BSD |
| Shield | Pillow (metadata PNG), imagehash, AudioSeal untuk audio | MIT/BSD |
| Kripto | `cryptography` Fernet untuk embedding | Apache/BSD |
| Frontend | Next.js (App Router, TypeScript), CSS Modules atau Tailwind dengan token di bawah | MIT |

Setiap dependensi baru: tambahkan ke `docs/TECH_LIST.md` beserta lisensi dan kegunaannya (wajib untuk proposal lomba).

## 6. Enum kanonik (backend/app/schema/common.py)

- `IdentityTarget`: SELF, OTHER_REGISTERED, OTHER_UNREGISTERED, UNCLEAR
- `MediaType`: IMAGE, VIDEO, AUDIO, TEXT_ONLY
- `TargetSource`: FACE, VOICE, TEXT
- `Intent` (10): PERSONAL_CREATION, PERSONAL_EDITING, SATIRE_PARODY, COMMERCIAL_USE, POLITICAL_USE, IMPERSONATION, DEFAMATION, SEXUAL_EXPLICIT, DECEPTIVE, UNCERTAIN
- `RiskLevel`: LOW (<30), MEDIUM (30-59), HIGH (60-84), CRITICAL (>=85)
- `Decision`: ALLOW, REVIEW, DENY
- `ConsentStatus`: GRANTED, DENIED, PENDING, NONE
- `LockLevel`: NONE, COMMERCIAL_POLITICAL, ALL (diatur terpisah untuk FACE dan VOICE)
- `PermissionDecision`: ALLOW, REVIEW, DENY (per intent x media)

Izin bawaan pemilik (bisa diubah pemilik): PERSONAL_CREATION ALLOW, PERSONAL_EDITING ALLOW, SATIRE_PARODY REVIEW, COMMERCIAL_USE REVIEW, POLITICAL_USE REVIEW, IMPERSONATION DENY, DEFAMATION DENY, SEXUAL_EXPLICIT DENY, DECEPTIVE DENY. Kloning suara (VOICE, intent apa pun selain PERSONAL_* milik sendiri) bawaan DENY.

## 7. Policy engine (backend/app/policy)

Dinilai **per target**, lalu keputusan akhir = yang paling ketat (DENY > REVIEW > ALLOW).

### Aturan mutlak (dicek pertama, selalu DENY)

1. Target OTHER_* dengan intent IMPERSONATION, DEFAMATION, SEXUAL_EXPLICIT, atau DECEPTIVE.
2. Kloning suara OTHER_* tanpa consent GRANTED untuk media VOICE.
3. Target yang terdaftar lewat mode wali (anak).
4. Izin pemilik untuk intent x media tersebut = DENY, atau consent DENIED.

### Matriks

| Target \ Risiko | LOW | MEDIUM | HIGH | CRITICAL |
| --- | --- | --- | --- | --- |
| SELF | ALLOW | ALLOW | REVIEW | DENY |
| OTHER_REGISTERED, consent atau lingkaran tepercaya sesuai cakupan | ALLOW | ALLOW | REVIEW | DENY |
| OTHER_REGISTERED, belum ada consent | REVIEW | REVIEW | DENY | DENY |
| OTHER_REGISTERED, Locked untuk media/tujuan itu | DENY | DENY | DENY | DENY |
| OTHER_UNREGISTERED | ALLOW + label AI | REVIEW | DENY | DENY |
| UNCLEAR | REVIEW | REVIEW | DENY | DENY |

### Aturan tambahan

- **Satire:** SATIRE_PARODY bergaya karikatur boleh (ikut matriks, selalu diberi label AI). Satire fotorealistik atau suara tiruan yang realistis diperlakukan sebagai DEFAMATION/DECEPTIVE (fitur `realism` dari Risk AI).
- **Gagal aman:** model error, intent UNCERTAIN, atau skor wajah/suara di zona abu-abu (ambang +/- margin di config) = REVIEW.
- **Pesan seragam:** pesan ke requester tidak boleh membedakan OTHER_REGISTERED dan OTHER_UNREGISTERED. Reason code detail hanya terlihat oleh pemilik identitas dan audit log.
- **ARMOR Explain:** setiap keputusan membawa `reason_code`, alasan bahasa Indonesia yang manusiawi, dan `suggestion` (prompt aman dari intent terdekat yang diizinkan). Template ada di `policy/explain.py`.
- Setiap aturan punya tes unit. Matriks diuji dengan tes table-driven yang mencakup semua sel.

## 8. Komponen AI

- **Face AI:** semua wajah diperiksa, cek kualitas (ukuran, blur Laplacian, pose) sebelum dicocokkan. Cosine similarity ke embedding terdaftar. Ambang dan margin abu-abu dibaca dari config hasil evaluasi `ml/face_eval`. Video: 2 frame/detik, gabungkan per jejak wajah.
- **Voice AI:** ECAPA embedding + anti-spoof + Whisper transkrip. Enrollment suara dengan 3 kalimat acak (challenge-response, dicek lewat transkrip).
- **Text Identity Matcher:** normalisasi, NER, fuzzy match (rapidfuzz) ke nama/alias terdaftar. Nama umum wajib punya alias unik.
- **Intent AI:** baseline TF-IDF + LR, pembanding IndoBERT. Confidence < ambang = UNCERTAIN. Dilaporkan macro F1 dan recall kelas berbahaya.
- **Risk AI:** LR/RF atas fitur konten (intent, confidence, jenis target, jenis media, realisme, tingkat manipulasi, konteks sensitif, penanda suara sintetis). **Consent dan izin BUKAN fitur Risk AI.** Label dari anotasi manual dua anotator, laporkan Cohen's kappa.
- Semua model di-load malas (lazy) dan punya fallback aman jika tidak tersedia.
- **Loop pembelajaran:** hasil REVIEW, banding, dan consent menjadi label untuk melatih ulang Intent dan Risk AI, hanya dari prompt yang requester-nya setuju dipakai untuk perbaikan model, tanpa media. Model baru hanya dipakai jika lolos gerbang evaluasi pada set uji beku (macro F1 dan recall kelas berbahaya tidak turun). Setiap log keputusan mencatat `model_version`.
- **Generator:** lewat antarmuka `GeneratorAdapter`. Mock adalah bawaan (demo offline); adapter model generatif lokal sungguhan bersifat opsional jika ada GPU.

## 9. Keamanan dan data

- Semua endpoint yang mengubah data identitas memeriksa kepemilikan (`identity.user_id == current_user`). Tanpa pengecualian.
- `/consent/respond`, `/permissions`, `/identity/lock`, lingkaran tepercaya: pemilik saja.
- Riwayat dan log: hanya milik pengguna sendiri. Peninjau hanya melihat kasus yang ditugaskan.
- Embedding dienkripsi Fernet dengan `ARMOR_EMBEDDING_KEY` dari env. Kunci tidak pernah di repo.
- Audit log berantai hash: `hash = sha256(prev_hash + json_kanonik_baris)`.
- Rate limit: permintaan consent maksimal 3 per requester per identitas per hari; request gateway per API key.
- ID pakai UUID, bukan hitungan baris.
- `.gitignore` wajib memuat: `.env`, `.venv/`, `*.pkl`, `*.onnx`, `ml/models/**/*.bin`, folder media/dataset wajah dan suara.
- Log tidak boleh memuat media, embedding, password, atau token.
- **Consent lapis 1 terekam:** setiap persetujuan pemrosesan biometrik disimpan sebagai catatan (jenis data FACE/VOICE, versi teks persetujuan, waktu setuju, waktu cabut). Teks persetujuan diberi versi di `docs/consent-text/`.
- **Pencabutan per media:** pemilik bisa mencabut persetujuan wajah saja atau suara saja; embedding media itu langsung dihapus. Hapus identitas = hapus semuanya.
- **Consent lapis 2:** cakupan (intent, media), masa berlaku (sekali pakai, 1 hari, 7 hari, 30 hari, atau tanggal), kedaluwarsa otomatis, dan pemilik bisa mencabut consent yang sudah diberikan kapan saja. Consent kedaluwarsa atau dicabut dianggap NONE.
- **Unggahan:** batasi ukuran dan durasi (di config), validasi tipe dari isi berkas (bukan dari ekstensi), tolak dengan pesan jelas.
- **CORS:** di produksi hanya origin frontend yang diizinkan, bukan `*`.
- **Peran:** USER, REVIEWER, PLATFORM, ADMIN. Peran REVIEWER dan ADMIN hanya diberikan lewat perintah CLI.

## 10. Desain frontend

Aplikasi mobile-first (lebar desain 390 px, maksimal 480 px di desktop, terpusat). Bahasa antarmuka **Indonesia**; tiga slogan tetap bahasa Inggris: "Protect Identity. Preserve Consent. Build Trust."

### Token

| Token | Nilai |
| --- | --- |
| bg | #06142A |
| surface | #0C2340 |
| line | #1C3A5E |
| text | #EAF4FF |
| muted | #9DB4CF |
| dim | #6F89A8 |
| accent | #4FB8F5 |
| accent-soft | #9BE3FB |
| success (ALLOW) | #5FE3B1 |
| warning (REVIEW) | #F3C35E |
| danger (DENY) | #F79090 |

- Font: **Big Shoulders Display** (judul, wordmark, kapital), **Big Shoulders Stencil Display** (slogan intro), **Atkinson Hyperlegible** (teks isi). Muat lewat `next/font/google`.
- Motif dari logo: sudut terpotong (chamfer 14 px) pada tombol utama dan bingkai penting; bentuk perisai/berlian dan lubang kunci.
- **Sumber desain utama:** hasil Claude Design yang diekspor tim ke `docs/design/` (layar, komponen, alur). Jika ada perbedaan antara file ini dan desain itu dalam hal tampilan, ikuti desain itu; dalam hal aturan dan data, ikuti file ini.
- Intro: logo 3D berputar masuk + kilatan cahaya, tiga slogan zoom masuk dengan kilatan layar, animasi scan wajah (garis tergambar, titik landmark, sinar sapu, centang bertahap, stempel "IDENTITAS TERLINDUNGI"), lalu layar sambutan dengan logo 3D melayang. Referensi: `docs/design/intro-reference.dc.html`.
- Hormati `prefers-reduced-motion`. Ada tombol Lewati.

### Aturan anti "AI slop" (wajib)

- Tidak ada tanda pisah panjang (em dash) di teks antarmuka.
- Tidak ada label pengisi: penghitung "01 / 03", tag "Beta", "Powered by AI", kutipan motivasi, subjudul mono yang tidak menjelaskan apa pun.
- Tidak ada gradien latar, glassmorphism, emoji sebagai ikon, ikon sparkles.
- Tidak ada kartu dengan garis warna di sisi kiri, tidak ada kotak yang separuh isinya kosong, tidak ada tombol garis kosong full-width sebagai aksi sekunder (pakai tautan teks).
- Tidak ada angka atau testimoni karangan.
- Setiap elemen harus bisa menjawab "kenapa ini ada di sini?".
- Aksesibilitas: target sentuh >= 44 px, kontras teks >= 4.5:1, elemen interaktif pakai `<button>`/`<a>` asli, `aria-label` pada tombol ikon.

## 11. Cara bekerja

- Kerjakan per fase sesuai `PROMPTS.md`. Mulai setiap fase dengan rencana singkat dan daftar tugas; akhiri dengan tes lulus, ringkasan perubahan, dan commit.
- Jangan menandai tugas selesai jika tes gagal.
- Pesan commit: `fase-N: ringkasan`.
- Setiap akhir fase, tambahkan entri ke `docs/AI_USAGE.md`: apa yang dikerjakan dengan bantuan Claude Code, file yang dihasilkan, dan apa yang diverifikasi manusia. Ini wajib diungkapkan di proposal lomba.
- Jangan pernah mengarang angka evaluasi. Angka hanya berasal dari skrip evaluasi yang benar-benar dijalankan; simpan hasilnya di `docs/eval/`.
- Jika butuh data yang belum ada (foto relawan, rekaman suara, anotasi), buat skrip, format, dan instruksinya, lalu minta tim menyediakan datanya.
- Cakupan: semua fitur di file ini masuk prototipe lomba. Jangan menyederhanakan atau menunda fitur tanpa bertanya. Yang boleh tetap berupa rencana hanya: lisensi model komersial, audit independen, dan uji bias skala besar.

## 12. Riwayat keputusan desain (jangan dibalik tanpa bertanya)

Eksperimen awal tim ada di notebook yang sengaja TIDAK dimasukkan ke repo. Ringkasan pelajarannya:

| Keputusan | Alasan |
| --- | --- |
| Model ArcFace `buffalo_l` tetap dipakai | Model pretrained yang baik; notebook lama juga memakainya. Yang diganti adalah data dan preprocessing, bukan modelnya. |
| Galeri 6.114 wajah tokoh dari dataset internet dibuang | Data biometrik tanpa persetujuan (UU PDP: data pribadi spesifik). Diganti database opt-in. |
| Preprocessing RetinaFace + rotasi mata + CLAHE + `get_feat` dibuang; enrollment dan inferensi wajib memakai `FaceAnalysis.get` yang sama | Galeri dibuat dengan preprocessing berbeda dari jalur inferensi, sehingga embedding tidak sebanding: akurasi 93,38% di set uji tertutup, tetapi hanya 2 dari 10 foto nyata dikenali. Jangan menambahkan CLAHE atau alignment sendiri di satu sisi saja. |
| FAR tidak boleh dihitung sebagai 100% dikurangi TAR | Notebook lama melakukannya. FAR harus dari percobaan wajah asing terhadap ambang tertentu. |
| Ambang 0,40 tidak dipakai begitu saja | Tidak diturunkan dari data. Ambang dan margin abu-abu harus dari `ml/face_eval`. |
| Ide filter kualitas (blur, resolusi) dari notebook dipakai ulang | Menjadi cek kualitas Face AI. |
| Gemini tidak dipakai untuk identifikasi wajah | Identifikasi orang tanpa izin; melanggar kebijakan penggunaan Google dan ketentuan tier gratis (dilarang mengirim data pribadi). |
| Gemini atau LLM lain tidak dipakai untuk intent, risk, maupun keputusan | Intent dan Risk AI harus model sendiri yang bisa diukur, dijelaskan, dan berjalan offline. Keputusan akhir hanya dari policy engine. Tidak ada panggilan ke API AI pihak ketiga di jalur utama. |
| Model `buffalo_l` berlisensi riset nonkomersial | Aman untuk lomba dan wajib dicantumkan; produksi butuh model berlisensi komersial. |

## Lampiran A: 20 skenario uji end-to-end

Anggota tim A dan B terdaftar (wajah dan suara); C tidak terdaftar. Skenario ini menjadi tes otomatis di `tests/scenarios/` dan naskah demo.

| No | Skenario | Keputusan yang diharapkan |
| --- | --- | --- |
| 1 | A mencerahkan fotonya sendiri | ALLOW |
| 2 | A membuat avatar kartun dirinya | ALLOW |
| 3 | A membuat karikatur superhero dari foto C | ALLOW + label AI |
| 4 | A membuat iklan memakai wajah B, B menyetujui lewat kotak consent | REVIEW lalu ALLOW |
| 5 | Sama dengan no. 4, B menolak | REVIEW lalu DENY |
| 6 | A membuat C memakai baju tahanan dan diborgol | DENY + saran prompt |
| 7 | A membuat C seolah membagikan bantuan dan meminta biaya admin | DENY |
| 8 | A mengedit ringan foto B yang sedang Locked | DENY |
| 9 | Foto B disamarkan (buram, kacamata hitam) untuk iklan | REVIEW |
| 10 | Satu foto berisi wajah A dan B, untuk iklan | REVIEW (paling ketat) |
| 11 | Fitnah terhadap C dengan kata-kata halus (eufemisme) | DENY |
| 12 | Akun lain mencoba mengubah izin milik B | Ditolak (bukan pemilik) |
| 13 | Prompt teks tanpa foto: "buat iklan dengan [nama/alias B]" | REVIEW |
| 14 | Video lip-sync C mengumumkan mundur dari jabatan | DENY |
| 15 | Prompt aman, tetapi hasil generator memuat wajah B | Ditahan Output Guard |
| 16 | Gambar hasil skenario 3 diunggah ke verifikasi publik | Terverifikasi dibuat lewat ARMOR |
| 17 | A memakai suaranya sendiri untuk narasi | ALLOW |
| 18 | A mengkloning suara B untuk pesan "minta transfer" | DENY |
| 19 | Rekaman ulang suara B dipakai untuk mendaftar sebagai B | Ditolak (anti-spoofing / duplikat) |
| 20 | Wajah anak yang didaftarkan lewat mode wali dipakai untuk konten apa pun | DENY |

## Lampiran B: model ancaman

Setiap baris diuji di Fase 11 dan hasilnya dicatat di `docs/threat-model.md`.

| Serangan | Tangkisan |
| --- | --- |
| Mendaftarkan wajah/suara orang lain sebagai milik sendiri | Multi-pose dari kamera dengan sudut berbeda; kalimat acak untuk suara; satu identitas per wajah/suara; jalur sengketa |
| Foto dari layar atau foto cetak saat enrollment | Cek perbedaan pose antar-tangkapan; evaluasi serangan di `ml/face_eval` |
| Menyamarkan wajah (buram, miring, kacamata hitam) | Cek kualitas; zona abu-abu menjadi REVIEW |
| Menyelipkan beberapa wajah atau suara | Semua target diperiksa; keputusan paling ketat berlaku |
| Rekaman ulang atau suara sintetis | Anti-spoofing; suara sintetis yang mirip suara terdaftar menaikkan risiko |
| Menyebut nama tanpa foto atau rekaman | Text Identity Matcher |
| Parafrase atau eufemisme prompt | Uji dengan set parafrase; confidence rendah menjadi UNCERTAIN |
| Prompt aman tetapi hasil memuat wajah/suara terdaftar | Output Guard |
| Menebak siapa yang terdaftar dari jawaban ARMOR | Pesan ke requester dibuat seragam |
| Membanjiri pemilik dengan permintaan consent | Rate limit per requester; pemilik dapat memblokir |
| Mengubah izin atau consent milik orang lain | Setiap perubahan hanya oleh pemilik identitas |
| Mengubah catatan keputusan | Audit log berantai hash |
| Mengunggah berkas raksasa atau berbahaya | Batas ukuran/durasi dan validasi tipe dari isi berkas |

## Lampiran C: metrik evaluasi yang harus dilaporkan

| Komponen | Metrik |
| --- | --- |
| Face AI gambar | TAR pada FAR 1% dan 0,1%, EER, ambang terpilih |
| Face AI video | Akurasi identifikasi target per klip |
| Face AI anti pendaftaran palsu | Persentase serangan tertolak (foto layar, foto cetak, wajah sudah terdaftar) |
| Voice AI | EER; persentase spoof terdeteksi |
| Text Identity Matcher | Precision dan recall |
| Intent AI | Macro F1, recall kelas berbahaya, untuk TF-IDF + LR dan IndoBERT, serta di set parafrase |
| Risk AI | Macro F1 per level, Cohen's kappa anotator |
| Output Guard | Persentase hasil terlarang yang tertahan |
| Sistem | Waktu keputusan per jenis media (rata-rata, p95); target gambar < 2 detik |
| Keamanan | Tabel sebelum vs sesudah untuk setiap celah Fase 1 |
