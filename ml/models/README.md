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

## Generator lokal opsional: Stable Diffusion 1.5 (Fase 8)

Tidak dibutuhkan untuk demo: bawaannya generator tiruan `generator_mock/`. Adapter ini hanya aktif jika laptop punya GPU CUDA (sekitar 6 GB VRAM atau lebih), `torch` dan `diffusers` terpasang, dan bobot model sudah diunduh.

Checkpoint yang disarankan: `stable-diffusion-v1-5/stable-diffusion-v1-5`, lisensi **CreativeML OpenRAIL-M** (boleh dipakai, termasuk komersial, dengan pembatasan penggunaan: misalnya dilarang untuk menyamar sebagai orang lain atau membuat konten yang merugikan; pembatasan itu harus diteruskan ke pengguna). Baca lisensinya sebelum mengunduh.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers accelerate
huggingface-cli download stable-diffusion-v1-5/stable-diffusion-v1-5 --local-dir ml/models/generator/sd \
  --include "*.json" "*.txt" "*fp16.safetensors"
```

Lalu isi `GENERATOR=auto` (atau `diffusers`) di `backend/.env`. Backend memuat model dengan `local_files_only`, jadi tidak pernah mengunduh saat berjalan. Jika GPU atau bobot tidak ada, `auto` kembali ke generator tiruan.
