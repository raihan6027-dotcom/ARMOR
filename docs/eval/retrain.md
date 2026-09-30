# Loop pembelajaran: riwayat retrain

**Status: belum dijalankan: belum ada feedback yang diperiksa.** Baris tabel di bawah ditambahkan otomatis oleh `python ml/retrain.py intent` (atau `risk`) setiap kali retrain dicoba.

Setiap baris adalah satu percobaan retrain dengan feedback yang sudah diperiksa. Model baru hanya dipakai jika macro F1 dan recall kelas berbahaya pada set uji beku tidak turun. Percobaan yang ditolak tetap dicatat. Versi yang pernah dipakai bisa dikembalikan dengan `python ml/retrain.py rollback --component intent --to <versi>`.

Cara mereproduksi: dari `backend/` jalankan `python -m app.cli feedback export`, periksa `ml/feedback/feedback.csv` (isi `diperiksa_oleh`), lalu `python ml/retrain.py intent`.

| Waktu | Komponen | Versi kandidat | Feedback dipakai | Macro F1 (aktif -> kandidat) | Recall berbahaya (aktif -> kandidat) | Hasil |
| --- | --- | --- | --- | --- | --- | --- |
