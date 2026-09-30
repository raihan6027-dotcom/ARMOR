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
| `/auth/register`, `/auth/login`, `/auth/me` | POST/POST/GET/PATCH | semua | Akun, JWT, profil, sakelar notifikasi email |
| `/identity/enroll` | POST | pemilik | Daftarkan wajah sendiri (3 pose + persetujuan lapis 1) |
| `/identity/verify`, `/identity/profile` | POST/GET | pemilik | Cek foto terhadap wajah sendiri; status identitas |
| `/identity/lock` | POST | pemilik | Lock per media: NONE, COMMERCIAL_POLITICAL, ALL |
| `/identity/me/revoke?media=FACE\|VOICE`, `/identity/me` | POST/DELETE | pemilik | Cabut persetujuan satu media; hapus semua data identitas |
| `/me/data` | GET | pengguna | Unduh semua data milik sendiri (tanpa embedding mentah) |
| `/permissions` | GET/POST | pemilik | Izin per intent x media |
| `/circle`, `/circle/{member_ref}` | GET/POST/DELETE | pemilik | Lingkaran tepercaya dengan cakupan dan masa berlaku |
| `/requests`, `/requests/{id}` | POST/GET | pengguna | Gateway (gambar, video, audio, teks); riwayat dan status terbaru |
| `/consent/request`, `/consent/request/{request_id}` | POST/GET | requester | Minta persetujuan untuk permintaan REVIEW milik sendiri; status gabungan |
| `/consent/inbox`, `/consent/{id}` | GET | pemilik | Kotak consent (menunggu/dijawab), detail |
| `/consent/{id}/respond`, `/consent/{id}/revoke` | POST | pemilik | Setujui dengan cakupan dan masa berlaku, tolak, blokir; cabut |
| `/notifications`, `/notifications/read` | GET/POST | pengguna | Notifikasi dalam aplikasi |
| `/dashboard/activity` | GET | pemilik | Upaya penggunaan identitas per minggu |
| `/cases`, `/cases/dispute`, `/cases/{id}` | POST/POST/GET | pengguna | Banding atas DENY, sengketa pendaftaran palsu, status kasus |
| `/cases/{id}/review`, `/freeze`, `/resolve`, `/assign` | POST | peninjau/admin | Konsol peninjau |
| `/audit/verify` | GET | peninjau/admin | Periksa integritas rantai hash audit log |
| `/decision` | POST | semua | Evaluasi policy tanpa status (untuk demo dan uji) |

Semua error memakai amplop `{"error": {"code", "message", "details?"}}`.

## CLI admin

```bash
python -m app.cli role grant --email peninjau@example.com --role REVIEWER   # atau ADMIN
python -m app.cli role revoke --email peninjau@example.com
python -m app.cli platform create --email dev@platform.example --password <minimal 12 karakter>
python -m app.cli logs purge --days 90       # jalankan harian (Task Scheduler / cron)
python -m app.cli audit verify
```
