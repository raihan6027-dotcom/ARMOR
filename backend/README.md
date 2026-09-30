# ARMOR backend: AI Safety Gateway

API FastAPI untuk ARMOR (AI-Aware Identity Protection). Setiap permintaan ke AI generatif (media + prompt) diperiksa **sebelum** konten dibuat dan diputuskan ALLOW, REVIEW, atau DENY oleh policy engine deterministik. Spesifikasi lengkap: [../CLAUDE.md](../CLAUDE.md).

```
media -> Face AI (semua wajah) -> target SELF / OTHER_REGISTERED / OTHER_UNREGISTERED / UNCLEAR
prompt -> Intent AI -> Risk AI
target + pengaturan pemilik (Lock, izin, consent) -> policy engine -> keputusan + ARMOR Explain
```

Prinsip yang dijaga kode ini:

- **Opt-in:** hanya wajah yang didaftarkan pemiliknya (3 pose, dengan persetujuan lapis 1 tercatat) yang ada di database. Tidak ada galeri wajah tokoh.
- **Tanpa nama:** Face AI tidak pernah menebak siapa seseorang. Klien juga tidak bisa menyebut target; target hanya dari pencocokan media.
- **Minimisasi data:** foto hanya diproses di memori. Yang disimpan hanya embedding rata-rata terenkripsi Fernet (`ARMOR_EMBEDDING_KEY`).
- **Gagal aman:** model tidak tersedia, zona abu-abu, atau intent UNCERTAIN menghasilkan REVIEW.
- **Pesan seragam:** jawaban ke requester sama untuk orang terdaftar dan tidak terdaftar.

## Menjalankan

```bash
python -m venv .venv
.venv\Scripts\activate                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt    # API + tes
pip install -r requirements-ml.txt     # model wajah asli (opsional untuk tes)
copy .env.example .env                 # macOS/Linux: cp .env.example .env
python scripts/gen_secrets.py --write
uvicorn app.main:app --reload
```

Dokumentasi interaktif: http://localhost:8000/docs. Skema basis data belum memakai migrasi: setelah menarik perubahan model, hapus `armor.db` lokal.

## Tes

```bash
pytest -q
ruff check . && ruff format --check .
```

Tes berjalan offline tanpa model: wajah diganti "kamera sintetis" (`tests/synthetic.py`) yang memakai embedding acak ternormalisasi. Satu tes model asli (`tests/unit/test_face_model_optional.py`) otomatis dilewati jika InsightFace atau model `buffalo_l` belum ada.

## Endpoint utama

| Endpoint | Metode | Siapa | Kegunaan |
| --- | --- | --- | --- |
| `/auth/register`, `/auth/login`, `/auth/me` | POST/POST/GET | semua | Akun dan JWT |
| `/identity/enroll` | POST | pemilik | Daftarkan wajah sendiri (3 pose + persetujuan lapis 1) |
| `/identity/verify` | POST | pemilik | Cek foto terhadap wajah sendiri |
| `/identity/profile` | GET | pemilik | Status identitas, Lock, media terdaftar |
| `/identity/lock` | POST | pemilik | Lock per media: NONE, COMMERCIAL_POLITICAL, ALL |
| `/identity/me/revoke?media=FACE\|VOICE` | POST | pemilik | Cabut persetujuan satu media, embedding dihapus |
| `/identity/me` | DELETE | pemilik | Hapus semua data identitas |
| `/me/data` | GET | pengguna | Unduh semua data milik sendiri (tanpa embedding mentah) |
| `/permissions` | GET/POST | pemilik | Izin per intent x media |
| `/requests` | POST/GET | pengguna | Gateway: periksa permintaan; riwayat milik sendiri |
| `/consent/request` | POST | requester | Minta persetujuan untuk permintaan REVIEW milik sendiri |
| `/consent/request/{request_id}` | GET | requester | Status persetujuan (gabungan) |
| `/consent/inbox`, `/consent/respond` | GET/POST | pemilik | Kotak consent dan jawabannya |
| `/decision` | POST | semua | Evaluasi policy tanpa status (untuk demo dan uji) |

Semua error memakai amplop `{"error": {"code", "message", "details?"}}`.
