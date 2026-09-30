# Evaluasi Risk AI

**Status: belum dijalankan: data belum tersedia.**

Anotasi dua anotator belum ada. Langkahnya ada di [`docs/risk-annotation-guide.md`](../risk-annotation-guide.md). Setelah anotasi selesai, file ini ditimpa oleh `python ml/risk/train.py` dengan macro F1 per level, Cohen's kappa, dan grafik importance fitur.

Sampai saat itu backend memakai tabel risiko per intent (`backend/app/ai/risk.py`, versi `risk-fallback-table-v1`).

Hasil uji jalan dengan anotator SINTETIS ada di [`synthetic/risk-smoke.md`](synthetic/risk-smoke.md) dan bukan hasil evaluasi.
