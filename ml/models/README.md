# ml/models/

Artefak model untuk demo offline. File biner (`*.joblib`, `*.onnx`, `*.pt`, `*.bin`) tidak di-commit.

## InsightFace `buffalo_l` (Face AI)

Lisensi model: **riset nonkomersial saja** (aman untuk lomba, wajib dicantumkan; produksi butuh model berlisensi komersial).

Unduh sekali selagi ada internet, lalu backend berjalan offline:

```bash
pip install -r backend/requirements-ml.txt
python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_l', root='ml/models').prepare(ctx_id=-1)"
```

Model tersimpan di `ml/models/models/buffalo_l/`. Backend mencarinya di `MODEL_DIR` (kosong = folder ini). Fase 12 menambahkan skrip yang mengunduh semua model sekaligus.
