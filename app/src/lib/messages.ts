import type { ApiError } from "./api";

/** Indonesian UI text for backend error codes. The backend messages are English. */
const MESSAGES: Record<string, string> = {
  OFFLINE: "Tidak ada koneksi ke server ARMOR. Periksa jaringan lalu coba lagi.",
  UNAUTHORIZED: "Email atau kata sandi salah.",
  EMAIL_TAKEN: "Email ini sudah terdaftar. Masuk saja, atau pakai email lain.",
  VALIDATION_ERROR: "Isian belum lengkap atau formatnya salah.",
  FORBIDDEN: "Kamu tidak punya akses ke bagian ini.",
  NOT_FOUND: "Data tidak ditemukan.",
  RATE_LIMITED: "Terlalu banyak permintaan. Tunggu sebentar lalu coba lagi.",
  FILE_TOO_LARGE: "Berkas terlalu besar.",
  UNSUPPORTED_FILE_TYPE: "Jenis berkas tidak didukung. Pilih gambar, video, atau audio yang sesuai.",
  INVALID_FILE: "Berkas tidak bisa dibaca.",
  ONE_MEDIA_ONLY: "Lampirkan satu berkas saja.",
  CONSENT_REQUIRED: "Centang persetujuan dulu untuk melanjutkan.",
  CONSENT_TEXT_OUTDATED: "Teks persetujuan sudah diperbarui. Muat ulang halaman lalu baca lagi.",
  FACE_MODEL_UNAVAILABLE: "Pemeriksaan wajah sedang tidak tersedia. Coba lagi nanti.",
  FACE_NOT_FOUND: "Wajah tidak terlihat. Pastikan wajahmu berada di dalam bingkai.",
  MULTIPLE_FACES: "Ada lebih dari satu wajah. Pastikan hanya kamu di dalam bingkai.",
  FACE_QUALITY_LOW: "Foto kurang jelas.",
  POSES_DIFFERENT_PERSON: "Ketiga foto tidak terlihat seperti orang yang sama. Ulangi dari awal.",
  POSE_SPREAD_TOO_SMALL: "Sudut kepala terlalu mirip. Palingkan kepala sedikit ke kiri dan ke kanan.",
  FACE_ALREADY_REGISTERED: "Wajah ini sudah terdaftar atas akun lain.",
  EMBEDDING_KEY_MISSING: "Server belum siap menyimpan data biometrik. Hubungi admin.",
  CONSENT_BLOCKED: "Pemilik identitas tidak menerima permintaan darimu.",
  CONSENT_RATE_LIMITED: "Batas permintaan persetujuan hari ini sudah tercapai. Coba lagi besok.",
  CONSENT_NOT_APPLICABLE: "Persetujuan hanya bisa diminta untuk permintaan yang sedang ditinjau.",
  CONSENT_ALREADY_ANSWERED: "Permintaan ini sudah dijawab.",
  UNTIL_REQUIRED: "Pilih tanggal terakhir persetujuan berlaku.",
  UNTIL_IN_PAST: "Tanggal itu sudah lewat.",
  INTENT_LOCKED: "Tujuan ini selalu ditolak dan tidak bisa diubah.",
  IDENTITY_FROZEN: "Identitas ini sedang dibekukan selama sengketa ditinjau.",
  APPEAL_EXISTS: "Banding untuk permintaan ini sudah diajukan.",
  APPEAL_NOT_APPLICABLE: "Hanya keputusan ditolak yang bisa dibanding.",
  NO_MATCHING_ENROLLMENT: "Wajahmu tidak cocok dengan pendaftaran di akun lain.",
  CIRCLE_SELF: "Kamu tidak perlu menambahkan dirimu sendiri.",
};

const QUALITY: Record<string, string> = {
  FACE_TOO_SMALL: "Wajah terlalu kecil, dekatkan ke kamera.",
  FACE_BLURRY: "Terlalu buram atau gelap, cari cahaya yang lebih terang.",
  FACE_TURNED_AWAY: "Wajah terlalu miring, hadap ke kamera.",
};

export function errorText(err: unknown): string {
  const e = err as ApiError;
  if (e?.code === "FACE_QUALITY_LOW" && e.details && !Array.isArray(e.details)) {
    const issues = (e.details as { issues?: string[] }).issues ?? [];
    const text = issues.map((i) => QUALITY[i]).filter(Boolean).join(" ");
    if (text) return text;
  }
  return (e?.code && MESSAGES[e.code]) || "Terjadi kesalahan. Coba lagi.";
}

export const INTENT_LABEL: Record<string, string> = {
  PERSONAL_CREATION: "Kreasi pribadi",
  PERSONAL_EDITING: "Edit pribadi",
  SATIRE_PARODY: "Satire dan parodi",
  COMMERCIAL_USE: "Komersial",
  POLITICAL_USE: "Politik",
  IMPERSONATION: "Peniruan",
  DEFAMATION: "Pencemaran nama",
  SEXUAL_EXPLICIT: "Konten seksual",
  DECEPTIVE: "Penipuan",
  UNCERTAIN: "Tidak jelas",
};

export const MEDIA_LABEL: Record<string, string> = {
  FACE: "Wajah",
  VOICE: "Suara",
  IMAGE: "Gambar",
  VIDEO: "Video",
  AUDIO: "Audio",
  TEXT_ONLY: "Teks saja",
};

export const RISK_LABEL: Record<string, string> = {
  LOW: "rendah",
  MEDIUM: "sedang",
  HIGH: "tinggi",
  CRITICAL: "sangat tinggi",
};

export function formatDate(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
