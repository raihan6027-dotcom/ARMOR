# generator_mock/: generator AI tiruan (SIMULASI)

Layanan FastAPI kecil yang **mensimulasikan** AI generatif untuk demo offline di laptop tanpa GPU. Ini bukan model generatif: gambar diolah dengan operasi Pillow sederhana yang dipilih dari kata kunci prompt (kartun, sketsa, hitam putih, cerah, atau gaya warna), dan permintaan teks saja menghasilkan komposisi abstrak. Setiap keluaran bertanda `SIMULASI` di metadata PNG, dan aplikasi menampilkan catatan bahwa generatornya simulasi.

ARMOR memanggil generator hanya setelah policy engine memutuskan ALLOW. Hasilnya lalu diperiksa Output Guard dan diberi ARMOR Shield oleh backend. Layanan ini tidak memutuskan apa pun dan tidak menyimpan apa pun.

## Menjalankan

```bash
cd generator_mock
pip install -r requirements.txt
uvicorn armor_generator_mock.service:app --port 8200
```

Backend memanggilnya lewat `GENERATOR=mock` dan `GENERATOR_URL=http://127.0.0.1:8200` (bawaan). Adapter lain (`GENERATOR=diffusers` atau `auto`) memakai model Stable Diffusion lokal jika ada GPU dan bobot model; lihat `ml/models/README.md`.

## Mode uji `inject_face` (demo Output Guard, skenario 15)

Mode ini menempelkan foto wajah ke setiap hasil, seolah generator "tanpa sengaja" memunculkan wajah orang terdaftar yang tidak pernah diminta.

1. Simpan satu foto wajah relawan B (yang sudah mendaftar di ARMOR dan menandatangani formulir consent) di `generator_mock/test_inject/`. Folder ini diabaikan git.
2. Jalankan dengan:
   ```bash
   GENERATOR_TEST_MODE=inject_face GENERATOR_INJECT_DIR=test_inject uvicorn armor_generator_mock.service:app --port 8200
   ```
3. Dari akun A, periksa permintaan aman (misalnya "Cerahkan foto saya ini") lalu tekan "Buat hasil". Output Guard menahan hasilnya dan B mendapat notifikasi.

Matikan mode uji setelah demo.

## Tes

```bash
pytest -q
```
