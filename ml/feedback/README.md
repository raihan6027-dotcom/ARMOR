# ml/feedback/

Ekspor feedback loop pembelajaran (`python -m app.cli feedback export` dari `backend/`). Isinya prompt pengguna yang memberi izin, jadi `feedback.csv` tidak di-commit. Periksa setiap baris, perbaiki label bila perlu, isi `diperiksa_oleh`, lalu jalankan `python ml/retrain.py intent`.
