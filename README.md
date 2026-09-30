# ARMOR

**AI-Aware Identity Protection.** AI Safety Gateway yang memeriksa setiap permintaan ke AI generatif (gambar, video, audio, atau teks) **sebelum** konten dibuat, lalu memutuskan ALLOW, REVIEW, atau DENY beserta alasannya.

Pertanyaan inti: *apakah AI berhak memakai wajah, suara, atau nama orang ini untuk tujuan ini?*

Karya lomba KOMPRES 16 Informatika, kategori AI Innovation. Spesifikasi lengkap dan aturan proyek ada di [CLAUDE.md](CLAUDE.md); status pengerjaan ada di [docs/PROGRESS.md](docs/PROGRESS.md).

## Struktur repo

```
armor/
  CLAUDE.md          spesifikasi dan aturan proyek (sumber kebenaran)
  backend/           API FastAPI: gateway, policy engine, identitas, consent
  ml/                pelatihan dan evaluasi model (intent, risk, face, voice)
  generator_mock/    layanan AI generatif tiruan untuk demo offline
  app/               aplikasi Next.js mobile-first
  docs/              PROMPTS, progres, penggunaan AI, teknologi, evaluasi, desain
  .claude/commands/  perintah /fase dan /otomatis untuk Claude Code
```

## Menjalankan backend

Butuh Python 3.11.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # macOS/Linux: cp .env.example .env
python scripts/gen_secrets.py --write
uvicorn app.main:app --reload
```

Buka http://localhost:8000/docs untuk dokumentasi API interaktif.

`requirements-dev.txt` cukup untuk API dan semua tes. Untuk model wajah asli (InsightFace), pasang juga `pip install -r requirements-ml.txt`; di Windows ini butuh Microsoft C++ Build Tools.

## Menjalankan tes

```bash
cd backend
pytest -q              # semua tes
ruff check .           # lint
ruff format --check .  # format
```

Tes berjalan sepenuhnya offline: tanpa model terunduh dan tanpa layanan pihak ketiga. CI GitHub Actions menjalankan ketiga perintah di atas pada setiap push ke `main` dan setiap pull request.

## Cara tim bekerja

Pengembangan dibagi per fase di [docs/PROMPTS.md](docs/PROMPTS.md). Di Claude Code, ketik `/fase N` untuk satu fase atau `/otomatis` untuk melanjutkan semua fase yang tersisa. Setiap fase diakhiri dengan tes lulus, entri di [docs/AI_USAGE.md](docs/AI_USAGE.md), dan commit `fase-N: ...`.

Data wajah dan suara relawan **tidak pernah** masuk repo. Formulir persetujuan relawan ada di [docs/consent-form-relawan.md](docs/consent-form-relawan.md).
