# ml/intent: Intent AI

Mengklasifikasikan tujuan prompt ke 10 kelas (CLAUDE.md bagian 6). Panduan label: [`docs/intent-labeling-guide.md`](../../docs/intent-labeling-guide.md). Hasil: [`docs/eval/intent.md`](../../docs/eval/intent.md).

| File | Isi |
| --- | --- |
| `dataset/templates.py` | Template kalimat per kelas, bahasa (id/en), dan media |
| `dataset/paraphrase.py` | Set ketahanan tulisan tangan (parafrase, eufemisme), tidak pernah dipakai training |
| `dataset/generate.py` | Membuat `intent_dataset.csv` (3.500 prompt), `paraphrase.csv`, dan `splits.json` (split beku) |
| `common.py` | Metrik bersama, pemilihan ambang UNCERTAIN, confusion matrix |
| `train_baseline.py` | TF-IDF (kata + karakter) + Logistic Regression, CPU |
| `train_indobert.py` | Fine-tune IndoBERT, GPU (Colab/Kaggle) |
| `select_model.py` | Memilih model untuk backend (`ml/models/intent/active.json`) dan menulis laporan |

## Alur

```bash
python ml/intent/dataset/generate.py            # sekali; jangan jalankan ulang setelah tim mulai memeriksa
# tim memeriksa CSV dan mengisi diperiksa_oleh (lihat panduan label)
python ml/intent/dataset/generate.py --check    # set uji tidak berubah
python ml/intent/train_baseline.py              # menolak jalan jika masih ada baris belum diperiksa
python ml/intent/train_indobert.py              # di Colab/Kaggle, lalu salin hasilnya ke ml/models/intent/
python ml/intent/select_model.py                # pilih model terbaik + tulis docs/eval/intent.md
```

Untuk eksperimen sebelum pemeriksaan selesai, tambahkan `--allow-unreviewed`. Hasilnya diberi status EKSPERIMEN dan tidak boleh masuk RINGKASAN.

## Menambah prompt alami

Dataset template mudah dihafal model (lihat catatan di `docs/eval/intent.md`). Tambahkan prompt tulisan tim ke `intent_dataset.csv` dengan `sumber=manual`, `split=train` (atau `val`), dan `id` baru `MAN-00001` dan seterusnya. **Jangan** menambah baris `split=test` dan jangan menyalin prompt dari `paraphrase.csv`.
