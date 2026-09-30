# Evaluasi Face AI

**Status: belum dijalankan: data belum tersedia.**

Foto relawan belum dikumpulkan. Langkah pengumpulan data, target jumlah, dan cara menjalankan ada di [`ml/face_eval/README.md`](../../ml/face_eval/README.md). Setelah data tersedia, file ini ditimpa oleh `python ml/face_eval/evaluate.py` dengan angka nyata: TAR pada FAR 1% dan 0,1%, EER, kurva ROC, serta rekomendasi `FACE_MATCH_THRESHOLD` dan `FACE_GRAY_MARGIN`.

Sampai saat itu backend memakai ambang placeholder `FACE_MATCH_THRESHOLD=0.40` dan `FACE_GRAY_MARGIN=0.05`, yang **tidak** berasal dari data.

Uji serangan enrollment (foto layar, foto cetak, wajah sudah terdaftar) ditulis ke [`face-attacks.md`](face-attacks.md) oleh `python ml/face_eval/attacks.py`, juga setelah data tersedia.

Hasil uji jalan dengan data SINTETIS ada di [`synthetic/`](synthetic/) dan bukan hasil evaluasi.
