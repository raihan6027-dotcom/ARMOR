"use client";

import { RequireAuth } from "@/components/Providers";
import { useToast } from "@/components/Toast";
import { Banner, Card, Empty, List, PrimaryLink, Row, Screen, Section, Segmented, Stack } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText } from "@/lib/messages";
import type { LockLevel, Profile } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

const LOCK_OPTIONS: { value: LockLevel; label: string }[] = [
  { value: "NONE", label: "Terbuka untuk pribadi" },
  { value: "COMMERCIAL_POLITICAL", label: "Kunci komersial dan politik" },
  { value: "ALL", label: "Kunci semua" },
];

function lockSentence(level: LockLevel, what: string): string {
  if (level === "ALL") return `Semua penggunaan ${what}mu oleh orang lain ditolak, termasuk edit ringan.`;
  if (level === "COMMERCIAL_POLITICAL")
    return `Iklan dan materi politik dengan ${what}mu selalu ditolak tanpa ditanyakan. Tujuan lain mengikuti izinmu.`;
  return `Orang lain mengikuti izin per tujuan yang kamu atur. Tujuan yang merugikan tetap selalu ditolak.`;
}

async function loadProfile(): Promise<Profile | null> {
  try {
    return await raw<Profile>("/identity/profile");
  } catch (e) {
    if ((e as { status?: number }).status === 404) return null;
    throw e;
  }
}

export default function IdentityPage() {
  return (
    <RequireAuth>
      <Identity />
    </RequireAuth>
  );
}

function Identity() {
  const toast = useToast();
  const { data: p, error, setData, loading } = useLoad(loadProfile);

  async function setLock(media: "FACE" | "VOICE", level: LockLevel) {
    if (!p) return;
    try {
      const res = await raw<{ face_lock: LockLevel; voice_lock: LockLevel; status: string }>("/identity/lock", {
        method: "POST",
        body: JSON.stringify({ identity_id: p.identity_id, level, media }),
      });
      setData({ ...p, ...res });
      toast("Lock diperbarui");
    } catch (err) {
      toast(errorText(err));
    }
  }

  return (
    <Screen title="Identitas" tabs>
      <Stack gap={22}>
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {loading && !p ? <p role="status" style={{ color: "var(--dim)" }}>Memuat...</p> : null}
        {!loading && !p && !error ? (
          <Empty title="Belum ada identitas terdaftar">
            <p style={{ color: "var(--muted)" }}>
              Daftarkan wajahmu untuk mengatur Lock, izin per tujuan, dan lingkaran tepercaya.
            </p>
            <PrimaryLink href="/enroll/">Daftarkan wajah</PrimaryLink>
          </Empty>
        ) : null}
        {p ? (
          <>
            <Section title="Lock wajah">
              {p.face_enrolled ? (
                <>
                  <Segmented label="Tingkat Lock wajah" value={p.face_lock} options={LOCK_OPTIONS} onChange={(v) => void setLock("FACE", v)} />
                  <p aria-live="polite" style={{ color: "var(--muted)" }}>{lockSentence(p.face_lock, "wajah")}</p>
                </>
              ) : (
                <Card>
                  <p style={{ color: "var(--muted)" }}>Wajah belum terdaftar.</p>
                </Card>
              )}
            </Section>
            <Section title="Lock suara">
              {p.voice_enrolled ? (
                <>
                  <Segmented label="Tingkat Lock suara" value={p.voice_lock} options={LOCK_OPTIONS} onChange={(v) => void setLock("VOICE", v)} />
                  <p aria-live="polite" style={{ color: "var(--muted)" }}>{lockSentence(p.voice_lock, "suara")}</p>
                </>
              ) : (
                <Card>
                  <p style={{ color: "var(--muted)" }}>
                    Suara belum terdaftar. Tanpa pendaftaran, suaramu tetap terlindungi dari peniruan: meniru suara orang
                    lain tanpa persetujuan selalu ditolak.
                  </p>
                </Card>
              )}
            </Section>
            <Section title="Atur">
              <List>
                <Row icon="settings" title="Izin per tujuan" sub="Izinkan, tinjau, atau tolak tiap tujuan." href="/identitas/izin/" />
                <Row icon="people" title="Lingkaran tepercaya" sub="Orang yang boleh tanpa bertanya dulu." href="/identitas/lingkaran/" />
                <Row icon="chart" title="Aktivitas" sub="Upaya penggunaan identitasmu." href="/aktivitas/" />
                <Row icon="key" title="Data saya" sub="Lihat, unduh, cabut, atau hapus." href="/data-saya/" />
                <Row icon="alert" title="Kasus" sub="Banding dan sengketa." href="/kasus/" />
              </List>
            </Section>
          </>
        ) : null}
      </Stack>
    </Screen>
  );
}
