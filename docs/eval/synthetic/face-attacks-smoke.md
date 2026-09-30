# Uji serangan enrollment wajah (SINTETIS, BUKAN HASIL)

Dijalankan dengan data SINTETIS hanya untuk memastikan kode berjalan. Angka di bawah TIDAK BOLEH dipakai di proposal atau RINGKASAN.md.

- Tanggal: 2026-09-30
- Cara mereproduksi: `python ml/face_eval/attacks.py --synthetic`

| Serangan | Percobaan | Tertolak | Persentase tertolak | Alasan penolakan |
| --- | --- | --- | --- | --- |
| Foto dari layar | 20 | 20 | 100.0% | POSE_SPREAD_TOO_SMALL: 20 |
| Foto cetak | 20 | 20 | 100.0% | FACE_QUALITY_LOW: 20 |
| Wajah yang sudah terdaftar | 20 | 20 | 100.0% | FACE_ALREADY_REGISTERED: 20 |
