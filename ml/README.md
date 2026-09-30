# ml/

Kode pelatihan dan evaluasi model ARMOR. Data relawan (foto, video, rekaman) **tidak pernah** di-commit; lihat `.gitignore`.

| Folder | Isi | Fase |
| --- | --- | --- |
| `intent/` | Dataset prompt, pelatihan TF-IDF + LR dan IndoBERT, evaluasi | 4 |
| `risk/` | Skenario risiko, anotasi dua anotator, pelatihan LR + RF | 5 |
| `face_eval/` | Evaluasi TAR/FAR/EER dan serangan enrollment dari data relawan | 3, 9 |
| `voice_eval/` | Evaluasi EER suara dan anti-spoof | 10b |
| `models/` | Artefak model terlatih (diabaikan git kecuali file kecil `.json`/`.md`) | 4, 5 |
