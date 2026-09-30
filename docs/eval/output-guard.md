# Evaluasi Output Guard

Status: **belum dijalankan: data belum tersedia.**

Metrik (CLAUDE.md Lampiran C): persentase hasil terlarang yang tertahan, beserta persentase alarm palsu pada hasil yang diizinkan.

Cara menjalankan setelah foto relawan terkumpul (`ml/face_eval/data/relawan/`, lihat `ml/face_eval/README.md`) dan model InsightFace `buffalo_l` terpasang:

```bash
python ml/output_guard_eval/guard_eval.py
```

Skrip mendaftarkan tiap relawan dengan pemeriksaan enrollment backend, lalu untuk pasangan (requester, relawan lain) membuat hasil terlarang (generator tiruan mode `inject_face` menempelkan wajah relawan lain) dan hasil yang diizinkan (tanpa tempelan). Setiap hasil dinilai oleh `app.services.output_guard.judge`, aturan yang sama dengan backend. File ini akan ditimpa oleh laporan hasilnya.
