# ml/face_eval: evaluasi Face AI

Mengukur seberapa baik Face AI mengenali wajah yang **didaftarkan sendiri** oleh pemiliknya, lalu menurunkan ambang `FACE_MATCH_THRESHOLD` dan `FACE_GRAY_MARGIN` dari data (CLAUDE.md bagian 12: ambang 0,40 lama tidak berasal dari data). Kode evaluasi memakai pipeline yang sama dengan backend (`backend/app/ai/face.py`), jadi hasilnya berlaku untuk aplikasi.

## 1. Sebelum mengambil data

1. Setiap relawan membaca dan menandatangani `docs/consent-form-relawan.md`. Tanpa formulir, tidak ada foto.
2. Relawan harus berusia 18 tahun ke atas.
3. Beri tiap relawan kode acak (`R01`, `R02`, ...). Nama hanya ada di formulir kertas, bukan di nama berkas.

## 2. Target jumlah data

| Data | Per relawan | Target minimum | Catatan |
| --- | --- | --- | --- |
| Foto enrollment | 3 (lurus, kepala sedikit ke kiri sekitar 15 derajat, sedikit ke kanan) | 20 relawan | Diambil dengan kamera laptop/HP, jarak sekitar 50 cm |
| Foto probe | 8 sampai 10 (cahaya berbeda, jarak berbeda, dengan dan tanpa kacamata, hari berbeda jika bisa) | 20 relawan | Dipakai untuk menghitung TAR dan FAR |
| Serangan: foto dari layar | 1 percobaan = 3 jepretan layar HP/laptop yang menampilkan foto relawan | 10 percobaan | Layar dipegang diam di depan kamera |
| Serangan: foto cetak | 1 percobaan = 3 jepretan foto cetak | 10 percobaan | Cetak ukuran postcard atau A5 |
| Serangan: wajah sudah terdaftar | 1 percobaan = 3 foto enrollment relawan yang sudah terdaftar, dikirim dari akun lain | 10 percobaan | Boleh memakai foto enrollment relawan lain |

Jika sampai hari ke-5 jumlahnya belum tercapai, jalankan dengan data yang ada dan laporkan jumlah sebenarnya. Jangan dibulatkan.

## 3. Struktur folder (TIDAK PERNAH di-commit)

Folder `ml/face_eval/data/` sudah diabaikan git. Simpan di laptop tim dengan enkripsi disk (BitLocker/FileVault), jangan di cloud publik.

```
ml/face_eval/data/
  relawan/
    R01/
      enroll/  1.jpg 2.jpg 3.jpg
      probe/   01.jpg ... 10.jpg
    R02/ ...
  serangan/
    layar/      P01/ 1.jpg 2.jpg 3.jpg   P02/ ...
    cetak/      P01/ ...
    terdaftar/  P01/ ...
```

## 4. Menjalankan

Butuh model InsightFace `buffalo_l` di `ml/models/` (lihat `ml/models/README.md`) dan `pip install -r backend/requirements-ml.txt -r ml/requirements.txt`.

```bash
python ml/face_eval/embed.py       # -> ml/face_eval/data/embeddings.npz (data biometrik, tidak di-commit)
python ml/face_eval/evaluate.py    # -> docs/eval/face.md + docs/eval/face_roc.png
python ml/face_eval/attacks.py     # -> docs/eval/face-attacks.md
```

Lalu salin rekomendasi dari `docs/eval/face.md` ke `backend/.env`:

```
FACE_MATCH_THRESHOLD=...
FACE_GRAY_MARGIN=...
```

## 5. Uji jalan tanpa data (SINTETIS)

```bash
python ml/face_eval/evaluate.py --synthetic
python ml/face_eval/attacks.py --synthetic
```

Hasilnya masuk `docs/eval/synthetic/` dan diberi tanda SINTETIS. Angka itu hanya bukti bahwa kodenya berjalan, bukan hasil evaluasi, dan tidak boleh masuk proposal atau `docs/eval/RINGKASAN.md`.

## 6. Setelah selesai

Hapus foto dan `embeddings.npz` paling lambat pada tanggal yang tertulis di formulir persetujuan.
