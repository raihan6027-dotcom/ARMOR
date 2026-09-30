# ml/risk: Risk AI

Memberi skor risiko 0 sampai 100 dan level LOW/MEDIUM/HIGH/CRITICAL dari fitur konten (`backend/app/ai/risk_features.py`). Consent dan izin bukan fitur. Panduan anotasi: [`docs/risk-annotation-guide.md`](../../docs/risk-annotation-guide.md). Hasil: [`docs/eval/risk.md`](../../docs/eval/risk.md).

| File | Isi |
| --- | --- |
| `scenarios.py` | 600 skenario realistis dan lembar anotasi kosong untuk dua anotator |
| `annotations/anotator_A.csv`, `anotator_B.csv` | Diisi anotator secara terpisah |
| `kappa.py` | Cohen's kappa (biasa dan berbobot kuadratik), label sepakat, daftar yang perlu dibahas |
| `train.py` | Logistic Regression vs Random Forest (validasi silang, dipilih dari macro F1) |

```bash
python ml/risk/kappa.py
python ml/risk/train.py               # menulis ml/models/risk/active.json, dipakai backend
python ml/risk/train.py --synthetic   # uji jalan dengan anotator SINTETIS, tidak pernah dipakai backend
```

Tanpa model hasil anotasi manusia, backend memakai tabel risiko per intent (`backend/app/ai/risk.py`).
