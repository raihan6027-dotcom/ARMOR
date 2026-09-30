# Daftar teknologi dan lisensi ARMOR

Setiap dependensi baru wajib dicatat di sini beserta lisensi dan kegunaannya (CLAUDE.md bagian 5). Kolom "Status" menandai apakah sudah dipakai di kode atau masih rencana fase berikutnya.

## Backend

| Teknologi | Versi | Lisensi | Kegunaan | Status |
| --- | --- | --- | --- | --- |
| Python | 3.11 | PSF | Bahasa backend dan ML | Dipakai |
| FastAPI | 0.115.14 | MIT | Framework API | Dipakai |
| Uvicorn | 0.52.4 | BSD-3 | Server ASGI | Dipakai |
| Pydantic / pydantic-settings | 2.13.4 / 2.15.0 | MIT | Validasi skema dan konfigurasi dari env | Dipakai |
| SQLAlchemy | 2.0.54 | MIT | ORM, SQLite (dev) dan MySQL/PostgreSQL (deploy) | Dipakai |
| PyMySQL | 1.2.3 | MIT | Driver MySQL | Dipakai (deploy) |
| cryptography | 50.0.1 | Apache-2.0 / BSD | Fernet untuk enkripsi embedding biometrik (`app/core/crypto.py`) | Dipakai |
| bcrypt | 5.0.0 | Apache-2.0 | Hash kata sandi | Dipakai |
| python-jose | 3.5.0 | MIT | Token JWT | Dipakai |
| NumPy | 2.2.6 | BSD-3 | Operasi vektor embedding | Dipakai |
| Pillow | 12.3.0 | MIT-CMU (HPND) | Baca gambar, metadata PNG untuk ARMOR Shield | Dipakai |
| python-multipart | 0.0.32 | Apache-2.0 | Unggahan berkas | Dipakai |
| email-validator | 2.3.0 | Unlicense | Validasi email akun | Dipakai |

## AI dan ML

| Teknologi | Lisensi | Kegunaan | Status |
| --- | --- | --- | --- |
| InsightFace (pustaka) | MIT | Deteksi semua wajah dan embedding via `FaceAnalysis.get` (satu pipeline untuk enrollment dan inferensi) | Dipakai (Fase 3, `backend/app/ai/face.py`) |
| Model InsightFace `buffalo_l` (SCRFD + ArcFace) | **Riset nonkomersial saja** | Deteksi wajah dan embedding 512-D | Aman untuk lomba; produksi butuh model berlisensi komersial |
| ONNX Runtime | MIT | Menjalankan model ONNX di CPU | Dipakai |
| OpenCV (headless) | Apache-2.0 | Pra-proses gambar, ambil frame video | Dipakai |
| pandas | BSD-3 | Olah data evaluasi | Rencana Fase 4-5 |
| matplotlib | Lisensi matplotlib (berbasis PSF, BSD-compatible) | Kurva ROC dan grafik evaluasi di `ml/` | Dipakai (Fase 3, `ml/face_eval`) |
| scikit-learn 1.7.2 | BSD-3 | Intent AI (TF-IDF kata + karakter + Logistic Regression), Risk AI (LR + RF) | Dipakai (Intent Fase 4, `backend/app/ai/intent.py`, `ml/intent/`) |
| joblib | BSD-3 | Menyimpan dan memuat model scikit-learn lokal | Dipakai (Fase 4) |
| SpeechBrain `spkrec-ecapa-voxceleb` | Apache-2.0 | Embedding suara | Rencana Fase 10b |
| Whisper (small/base) | MIT | Transkrip suara offline | Rencana Fase 10b |
| Model anti-spoof (AASIST atau setara) | Cek sebelum dipakai | Deteksi rekaman ulang dan suara sintetis | Rencana Fase 10b |
| IndoBERT `indobenchmark/indobert-base-p1` (IndoNLU) + Hugging Face transformers (Apache-2.0) + PyTorch (BSD-3) | Cek lisensi checkpoint sebelum pengumpulan | Pembanding Intent AI (`ml/intent/train_indobert.py`, GPU) | Skrip siap, belum dijalankan (butuh GPU) |
| rapidfuzz | MIT | Pencocokan nama/alias | Rencana Fase 10a |
| spaCy | MIT | NER sederhana | Rencana Fase 10a (atau regex) |
| imagehash | BSD-2 | Perceptual hash ARMOR Shield | Rencana Fase 8 |
| AudioSeal | MIT (kode), cek lisensi bobot | Watermark audio ARMOR Shield | Rencana Fase 10b |

## Warisan yang akan dihapus

| Teknologi | Alasan dihapus | Fase |
| --- | --- | --- |
| google-genai (Gemini) | CLAUDE.md bagian 12: tidak boleh ada panggilan API AI pihak ketiga di jalur utama | Fase 3: tidak lagi menerima gambar atau pertanyaan identitas (selesai). Fase 4-5: dihapus dari intent dan risk |
| `official_face_registry.pkl` (galeri 6.114 wajah tokoh) | Data biometrik tanpa persetujuan | Dihapus di Fase 3 |

## Frontend (rencana Fase 7)

| Teknologi | Lisensi | Kegunaan |
| --- | --- | --- |
| Next.js (App Router, TypeScript) | MIT | Aplikasi mobile-first dan PWA |
| Big Shoulders Display / Stencil Display | SIL OFL 1.1 | Judul, wordmark, slogan |
| Atkinson Hyperlegible | SIL OFL 1.1 | Teks isi |
| Playwright | Apache-2.0 | Tes alur end-to-end |

## Alat pengembangan

| Teknologi | Lisensi | Kegunaan |
| --- | --- | --- |
| pytest / pytest-cov | MIT | Tes dan cakupan tes |
| httpx | BSD-3 | Klien tes FastAPI |
| ruff | MIT | Linter dan formatter |
| GitHub Actions | Layanan GitHub | CI: ruff + pytest |
