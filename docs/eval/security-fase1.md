# Fase 1: celah keamanan, sebelum vs sesudah (Bab 7.2)

Setiap baris punya tes regresi di `backend/tests/security/test_fase1_security.py`. Kolom "Sebelum" adalah hasil nyata menjalankan tes itu terhadap kode lama (commit `8459c21`, sebelum perbaikan): 12 dari 12 tes gagal. Kolom "Sesudah" adalah hasil setelah perbaikan Fase 1: 12 dari 12 lulus.

Cara mereproduksi:

```bash
cd backend
git stash              # atau checkout 8459c21 untuk melihat kolom "Sebelum"
pytest tests/security -q
```

| No | Serangan | Sebelum (kode lama) | Sesudah (Fase 1) | Tes |
| --- | --- | --- | --- | --- |
| 1 | Akun lain me-enroll ulang `identity_id` milik orang lain lalu dianggap SELF | Enroll diterima (HTTP 200), kepemilikan pindah ke penyerang | Ditolak HTTP 403 `FORBIDDEN`; penyerang tetap dianggap OTHER dan tidak pernah ALLOW | `test_1_cannot_reenroll_someone_elses_identity` |
| 2 | Mengubah atau membaca permission identitas orang lain | Diterima (HTTP 200) | Ditolak HTTP 403; permission pemilik tidak berubah | `test_2_cannot_change_or_read_someone_elses_permissions` |
| 3a | `/consent/request` tanpa login, dan `requester_id` dipalsukan lewat body | Diterima tanpa login (HTTP 200); `requester_id` dari body dipercaya | Tanpa login HTTP 401; `requester_id` selalu dari token | `test_3a_consent_request_requires_login_and_takes_requester_from_token` |
| 3b | Menyetujui consent atas nama pemilik | Siapa pun, bahkan tanpa login, bisa menyetujui (HTTP 200) | Tanpa login HTTP 401; bukan pemilik HTTP 403; hanya pemilik identitas yang bisa menjawab | `test_3b_only_owner_can_respond_to_consent` |
| 4 | Identity Lock tidak pernah dicek policy | Identitas Locked tetap diproses, keputusan REVIEW | Target OTHER pada identitas Locked selalu DENY (`IDENTITY_LOCKED`, hanya tercatat di log pemilik/audit) | `test_4_identity_lock_is_enforced_by_policy` |
| 5 | `GET /requests` dan `/logs` menampilkan riwayat semua pengguna | Penyerang melihat 1 permintaan milik orang lain | Hanya riwayat milik sendiri (0 untuk penyerang) | `test_5_history_and_logs_only_show_own_requests` |
| 6 | ID dari hitungan baris (race condition, bentrok setelah penghapusan) | Setelah satu baris dihapus, ID berikutnya bentrok: HTTP 500 `UNIQUE constraint failed` | Semua ID (pengguna, request, consent) UUID v4; tidak bentrok | `test_6_ids_are_uuids_and_do_not_collide_after_deletion` |
| 7 | `/identity/verify` sebagai alat pengecek wajah terhadap identitas siapa pun | HTTP 200 berisi skor kecocokan wajah | HTTP 404 untuk identitas yang bukan milik pemanggil; tidak ada skor | `test_7_verify_is_not_an_identity_checking_oracle` |
| 8 | `/identity/profile` membaca identitas orang lain | HTTP 200 berisi profil | HTTP 404 (tidak membedakan "tidak ada" dan "bukan milikmu") | `test_8_profile_of_another_user_is_not_readable` |
| 9 | `/identity/lock` "mengklaim" `identity_id` yang belum terdaftar | HTTP 200, identitas baru tercipta tanpa pemilik | HTTP 404, tidak ada yang tercipta; pemilik asli tetap bisa mendaftar | `test_9_lock_cannot_claim_an_unregistered_identity_id` |
| 9b | Mengunci identitas milik orang lain | HTTP 200, identitas orang lain terkunci | HTTP 403 | `test_9b_lock_of_someone_elses_identity_is_forbidden` |
| 10 | Respons `/requests` membocorkan `match_score`, `identity_id` target, status verifikasi | Respons memuat `identity_id`, `verified`, `match_score`; riwayat memuat `identity_id` | Respons ke requester hanya memuat `target` (SELF/OTHER) dan keputusan dengan pesan seragam; respons untuk orang terdaftar dan tidak terdaftar identik | `test_10_requester_response_does_not_leak_target_details` |

## Pengetatan tambahan

| Hal | Perubahan | Tes |
| --- | --- | --- |
| Rahasia bawaan di produksi | Server menolak menyala jika `APP_ENV=production` dan `JWT_SECRET` masih bawaan atau kurang dari 32 karakter, atau `CORS_ORIGINS=*` | `tests/unit/test_config_security.py` |
| Status consent | `GET /consent/status/{id}` wajib login dan hanya untuk requester atau pemilik identitas | `tests/api/test_consent.py` |
