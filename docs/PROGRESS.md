# Progres pengembangan ARMOR

Dokumen status untuk perintah `/otomatis` dan untuk tim. Urutan fase: 0, 1, 2, 3, 4, 5, 6, 6b, 7, 8, 9, 10a, 10b, 10c, 10d, 10e, 10f, 11, 12.

## Status fase

| Fase | Status | Commit |
| --- | --- | --- |
| Awal | Selesai | `2ec74d9` |
| 0 | Selesai | `3649ac6` |
| 1 | Selesai | `78287e1` |
| 2 | Selesai | (lihat log di bawah) |
| 3 | Belum | |
| 4 | Belum | |
| 5 | Belum | |
| 6 | Belum | |
| 6b | Belum | |
| 7 | Belum | |
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

- **Commit:** (lihat tabel status)
- **Ringkasan:** Enum kanonik CLAUDE.md bagian 6 berlaku di seluruh backend. Policy engine ditulis ulang: menerima daftar target (sumber, jenis target, identitas, skor, Lock, consent, izin, lingkaran tepercaya, wali) beserta intent, risiko, jenis media, dan realisme; menerapkan aturan mutlak, gagal aman, dan matriks per target; lalu mengambil keputusan paling ketat. Keluarannya: keputusan, reason code, alasan bahasa Indonesia, saran prompt, pesan requester yang seragam, dan detail per target untuk pemilik dan audit. Izin disimpan per intent x media (bawaan wajah sesuai CLAUDE.md, suara bawaan DENY, empat intent berbahaya terkunci DENY). Lock diatur per media dengan tiga tingkat. Consent punya cakupan intent dan media. Gateway `/requests` dan `/decision` memakai engine baru. Selama fase ini ditemukan bahwa `backend/app/models/` tidak pernah ter-commit karena pola `.gitignore` lama; sudah diperbaiki.
- **Hasil tes:** 185 lulus, 0 gagal. Cakupan `app/policy` 100% (baris dan cabang). Ruff bersih.
- **Perlu diperiksa manusia:** (1) tafsiran bahwa izin ALLOW = consent tetap; (2) teks alasan dan saran prompt di `backend/app/policy/explain.py`; (3) commit `awal`, `fase-0`, dan `fase-1` tidak memuat `backend/app/models/*.py`, jadi checkout commit lama itu tidak bisa dijalankan; mulai commit Fase 2 lengkap; (4) skema basis data berubah: hapus `backend/armor.db` lokal sebelum menjalankan server (belum ada migrasi).
