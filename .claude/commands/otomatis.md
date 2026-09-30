---
description: Jalankan semua fase pengembangan ARMOR berurutan secara otomatis sampai Fase 12
disable-model-invocation: true
---

Kerjakan pengembangan ARMOR secara otomatis, dari fase pertama yang belum selesai sampai Fase 12, mengikuti docs/PROMPTS.md dan CLAUDE.md.

Cara kerja:

1. Baca docs/PROGRESS.md (buat jika belum ada). File ini mencatat fase yang sudah selesai, commit-nya, dan hal yang menunggu tim. Lanjutkan dari fase pertama yang belum selesai. Urutan fase: 0, 1, 2, 3, 4, 5, 6, 6b, 7, 8, 9, 10a, 10b, 10c, 10d, 10e, 10f, 11, 12.
2. Untuk setiap fase: tulis rencana singkat, kerjakan SEMUA tugas fase itu sampai "Kriteria selesai" terpenuhi, jalankan semua tes (lama dan baru), tambahkan entri ke docs/AI_USAGE.md, commit sesuai pesan di prompt fase, perbarui docs/PROGRESS.md, lalu LANJUT ke fase berikutnya tanpa menunggu saya.
3. Jangan menyederhanakan, melewatkan, atau menandai selesai tugas yang belum benar-benar selesai. Jika tes gagal, perbaiki kodenya, bukan tesnya.
4. Data yang harus dibuat manusia (foto dan rekaman relawan, pemeriksaan dataset prompt, anotasi risiko oleh dua orang, hasil survei): jangan dikarang dan jangan dilewati diam-diam. Bangun semua skrip, format, dan instruksinya. Boleh menjalankan pipeline dengan data contoh yang diberi tanda jelas SINTETIS hanya untuk memastikan kode berjalan. Catat kebutuhan datanya di docs/PROGRESS.md bagian "Menunggu tim", lalu lanjut ke fase berikutnya. Angka dari data sintetis TIDAK BOLEH masuk docs/eval/RINGKASAN.md sebagai hasil evaluasi.
5. Jika hasil Claude Design belum ada di docs/design/, turunkan layar dari sistem desain di CLAUDE.md bagian 10 dan docs/design/intro-reference.dc.html, lalu catat layar yang kamu turunkan sendiri.
6. Hal yang butuh akun atau tindakan saya (login GitHub, Vercel, Hugging Face, SMTP, persetujuan lisensi model): siapkan sampai tinggal satu langkah, catat di "Menunggu tim" beserta langkah persisnya, lalu lanjut.
7. Berhenti dan tanya saya HANYA jika: sebuah keputusan bertentangan dengan CLAUDE.md; ada tindakan yang tidak bisa dibatalkan di luar folder repo (menghapus file di luar repo, push --force, membuat repo publik); atau semua fase tersisa terblokir oleh data dari tim.
8. Push ke remote hanya jika origin sudah disambungkan, dan hanya ke branch main atau branch yang sedang dipakai. Jangan pernah push --force. Jangan pernah mengubah visibilitas repo.
9. Di akhir setiap fase, tulis di docs/PROGRESS.md: nama fase, hash commit, ringkasan satu paragraf, hasil tes, dan hal yang perlu diperiksa manusia.
10. Jika konteks mulai penuh atau sesi terputus, semua status penting sudah ada di docs/PROGRESS.md, sehingga sesi baru cukup menjalankan /otomatis lagi untuk melanjutkan.

Setelah Fase 12 selesai: tulis ringkasan akhir di docs/PROGRESS.md berisi daftar lengkap "Menunggu tim" yang diurutkan dari yang paling penting, lalu berhenti.
