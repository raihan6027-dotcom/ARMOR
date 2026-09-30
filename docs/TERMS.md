# Ketentuan layanan ARMOR

**DRAF, perlu ditinjau manusia.** Versi lengkap disusun di Fase 11. Bagian di bawah sudah berlaku di prototipe karena dipakai oleh fitur loop pembelajaran (Fase 6b).

## Pemakaian prompt untuk memperbaiki model (opsional)

Saat memeriksa permintaan, kamu boleh mencentang pilihan "Izinkan prompt ini dipakai untuk memperbaiki model ARMOR". Pilihan ini **tidak dicentang** secara bawaan.

Jika kamu mencentangnya:

- Yang dipakai hanya **teks prompt** dan label hasil keputusan (tujuan dan tingkat risiko). Foto, video, rekaman, wajah, dan suara **tidak pernah** dipakai atau disimpan.
- Prompt baru dipakai setelah diperiksa anggota tim ARMOR.
- Prompt dipakai untuk melatih ulang Intent AI dan Risk AI. Model baru hanya dipakai jika hasil pengujiannya tidak lebih buruk daripada model sebelumnya.
- Kamu bisa melihat permintaanmu, termasuk pilihan ini, lewat Data saya.

Jika kamu tidak mencentangnya, prompt tetap disimpan di log keputusan selama 90 hari untuk keperluan audit, tetapi tidak pernah dipakai untuk melatih model.
