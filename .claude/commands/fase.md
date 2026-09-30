---
description: Kerjakan satu fase pengembangan ARMOR dari docs/PROMPTS.md
disable-model-invocation: true
---

Kerjakan Fase $ARGUMENTS dari docs/PROMPTS.md.

Aturan:
1. Baca docs/PROMPTS.md dan ambil HANYA bagian "Fase $ARGUMENTS" (termasuk sub-bagiannya jika ada, misalnya 6b atau 10a). Jika fase itu tidak ditemukan, berhenti dan tanyakan ke saya.
2. Patuhi CLAUDE.md sepenuhnya.
3. Sebelum mengubah file, tulis rencana singkat dan daftar tugas fase ini.
4. Kerjakan semua tugas fase ini sampai "Kriteria selesai" terpenuhi. Jangan menyederhanakan atau melewatkan tugas tanpa bertanya.
5. Jalankan tes. Jangan menyatakan selesai jika ada tes yang gagal.
6. Tambahkan entri ke docs/AI_USAGE.md, lalu commit dengan pesan sesuai prompt fase.
7. Tutup dengan ringkasan: apa yang dikerjakan, hasil tes, hal yang perlu diperiksa manusia, dan data yang harus disiapkan tim (jika ada).
8. BERHENTI setelah fase ini. Jangan lanjut ke fase berikutnya.
