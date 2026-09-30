# ARMOR app

Aplikasi mobile-first (Next.js App Router, TypeScript, CSS Modules) untuk ARMOR. Diekspor statis (`output: "export"`) agar bisa dilayani dari server statis mana pun atau dari backend untuk demo offline, dan bisa dipasang sebagai PWA.

## Menjalankan

```bash
npm install
npm run dev          # http://localhost:3000, backend di http://localhost:8000
npm run build        # hasil statis di out/
```

Alamat backend diatur lewat `NEXT_PUBLIC_API_URL` (bawaan `http://localhost:8000`). Backend harus mengizinkan origin aplikasi di `CORS_ORIGINS`.

## Klien API bertipe

Tipe diturunkan dari OpenAPI backend:

```bash
cd ../backend && python scripts/export_openapi.py
cd ../app && npm run gen:api     # src/lib/api/schema.d.ts
```

## Desain

Token, font, dan aturan anti "AI slop" mengikuti `CLAUDE.md` bagian 10. Intro diturunkan dari `docs/design/intro-reference.dc.html`. Hasil Claude Design belum ada di `docs/design/`, jadi layar lain diturunkan dari sistem desain yang sama; daftarnya ada di `docs/PROGRESS.md` (Fase 7).
