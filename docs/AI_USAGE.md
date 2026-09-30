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
