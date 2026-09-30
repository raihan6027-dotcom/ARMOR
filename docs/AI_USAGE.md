# Catatan penggunaan AI dalam pengembangan ARMOR

Dokumen ini wajib diungkapkan di proposal lomba (CLAUDE.md bagian 11). Setiap fase menambahkan satu entri: apa yang dikerjakan dengan bantuan Claude Code, file yang dihasilkan, dan apa yang diverifikasi manusia.

Alat: **Claude Code** (model Claude Opus 5.5, Anthropic), dijalankan oleh anggota tim di laptop masing-masing. Semua kode hasil bantuan AI ditinjau, dijalankan, dan diuji oleh tim sebelum digabung ke `main`.

---

## Awal: bahan proyek (commit `2ec74d9`)

- **Dikerjakan dengan Claude Code:** menyusun repo dari bahan tim (CLAUDE.md, PROMPTS.md, desain intro, logo, backend lama tanpa `.venv`, `.env`, `.git`), memeriksa riwayat git backend lama untuk rahasia yang ter-commit (tidak ditemukan), menjalankan 46 tes lama (lulus), dan mendaftar bagian kode lama yang bertentangan dengan CLAUDE.md.
- **File:** struktur awal repo, `.claude/commands/fase.md`.
- **Perlu diverifikasi manusia:** bahwa berkas bahan yang dipakai adalah versi final (v3).

## Fase 0: persiapan monorepo

- **Dikerjakan dengan Claude Code:** struktur monorepo (`backend/`, `ml/`, `generator_mock/`, `app/`, `docs/`), `.gitignore` sesuai CLAUDE.md bagian 9 (termasuk folder data relawan), `.gitattributes` untuk akhir baris seragam, `backend/.env.example` lengkap, skrip `backend/scripts/gen_secrets.py`, konfigurasi ruff dan pytest di `backend/pyproject.toml`, pemisahan requirements (core, ml, dev), perbaikan temuan ruff tanpa mengubah perilaku, workflow CI, dokumen `TECH_LIST.md`, `consent-form-relawan.md`, README root, dan `PROGRESS.md`.
- **Perubahan kode lama:** hanya gaya (format ruff) dan perbaikan lint tanpa perubahan perilaku: `raise ... from exc` pada dekode base64, penghapusan variabel tak terpakai di `decision_service.py`, dua field config baru (`face_gray_margin`, `armor_embedding_key`, `app_env`) yang belum dipakai kode.
- **Verifikasi otomatis:** `ruff check` dan `ruff format --check` bersih, 46 tes lama lulus.
- **Perlu diverifikasi manusia:** isi formulir consent relawan (nama penanggung jawab, email kontak, batas waktu simpan), dan menjalankan `python scripts/gen_secrets.py --write` di laptop masing-masing.

## Fase 1: menutup celah keamanan

- **Dikerjakan dengan Claude Code:** 12 tes serangan di `backend/tests/security/` ditulis lebih dulu dan terbukti gagal pada kode lama (12 gagal), lalu diperbaiki: cek kepemilikan pada enroll, verify, profile, lock, dan permission (`identity_service.get_owned`); consent wajib login, `requester_id` dari token, hanya pemilik yang menjawab, status consent hanya untuk requester/pemilik; policy mengecek Identity Lock (`IDENTITY_LOCKED`); riwayat dan log hanya milik sendiri; ID pengguna, request, dan consent memakai UUID; respons `/requests` dan riwayat ke requester tidak memuat `identity_id` target, `match_score`, status verifikasi, izin, atau consent, dengan pesan keputusan seragam untuk target OTHER; server menolak menyala di produksi dengan `JWT_SECRET` bawaan atau CORS `*`.
- **File:** `app/services/identity_service.py`, `consent_service.py`, `decision_service.py`, `app/identity/router.py`, `app/permission/router.py`, `app/consent/router.py`, `app/requests/router.py`, `app/logs/router.py`, `app/auth/router.py`, `app/policy/engine.py`, `app/schema/request.py`, `app/schema/consent.py`, `app/core/config.py`, `app/main.py`, tes baru di `tests/security/` dan `tests/unit/test_config_security.py`, `docs/eval/security-fase1.md`.
- **Tes lama yang disesuaikan (bukan dilemahkan):** `test_auth.py` (ID pengguna kini UUID, bukan `USER-001`), `test_consent.py` (consent kini butuh login dan dijawab pemilik), `test_permission.py` (permission kini hanya untuk identitas milik pemanggil, jadi tes lebih dulu mendaftarkan identitasnya). Ketiga tes lama itu sebelumnya mengukuhkan perilaku yang justru merupakan celah 2, 3, dan 6.
- **Verifikasi otomatis:** 61 tes lulus (46 lama, 12 keamanan, 3 config), ruff bersih.
- **Perlu diverifikasi manusia:** tabel sebelum/sesudah di `docs/eval/security-fase1.md` untuk Bab 7.2; pilihan desain bahwa endpoint baca (verify, profile) menjawab 404 untuk "bukan milikmu" agar tidak bisa dipakai menebak identitas yang ada.

## Fase 2: model domain dan policy engine multimodal

- **Dikerjakan dengan Claude Code:** enum kanonik di `schema/common.py` (IdentityTarget 4 nilai, Intent 10 kelas, MediaType, TargetSource, LockLevel, ConsentStatus dengan NONE), keyword fallback untuk SATIRE_PARODY dan SEXUAL_EXPLICIT; policy engine baru per target (`policy/engine.py`) dengan urutan aturan mutlak, gagal aman, matriks, lalu paling ketat; matriks sebagai data (`policy/matrix.py`); izin bawaan per intent x media (`policy/defaults.py`); ARMOR Explain (`policy/explain.py`) dengan alasan bahasa Indonesia, saran prompt, dan tampilan requester yang seragam; model Permission per intent x media; Lock per media (FACE, VOICE) dan endpoint `/identity/lock` dengan `level` dan `media`; cakupan consent (intent, media); gateway dan `/decision` memakai engine baru; risk fallback tidak lagi memakai consent (CLAUDE.md bagian 8).
- **Temuan dan perbaikan:** `backend/.gitignore` lama memuat pola `models/` tanpa jangkar yang ikut mengabaikan `backend/app/models/`. Akibatnya keenam file model SQLAlchemy tidak pernah ter-commit (juga di riwayat git backend lama). Pola dijangkarkan menjadi `/models/` dan `/data/`; file model ikut commit ini.
- **Tafsiran desain (perlu diperiksa manusia):** izin pemilik ALLOW untuk suatu intent x media diperlakukan sebagai consent tetap (baris matriks "consent atau lingkaran tepercaya sesuai cakupan"), karena tanpa itu opsi "Izinkan" tidak berbeda efeknya dari "Tinjau". Aturan mutlak 1 juga diterapkan pada target UNCLEAR.
- **Tes lama yang disesuaikan karena kontraknya berubah di fase ini:** `test_policy.py` diganti tes table-driven (API `evaluate_policy` lama dihapus); `test_decision.py` memakai skema `/decision` baru (skema lama kini ditolak 422); `test_permission.py` memakai bentuk intent x media; `test_schema.py` memakai `ConsentStatus.NONE`; risiko fallback COMMERCIAL_USE kini MEDIUM (bukan HIGH) di `test_intent_risk.py` dan `test_requests_e2e.py`, karena consent bukan fitur risiko dan skenario 4 Lampiran A mensyaratkan REVIEW lalu ALLOW; tes keamanan 1 memakai prompt iklan (avatar kini ALLOW karena izin bawaan PERSONAL_CREATION = ALLOW) dan memeriksa bahwa target tercatat OTHER_REGISTERED.
- **Verifikasi otomatis:** 185 tes lulus, cakupan tes `app/policy` 100% (baris dan cabang), ruff bersih.
