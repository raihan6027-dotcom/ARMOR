"use client";

import Link from "next/link";

import { Icon } from "@/components/Icon";
import { RequireAuth, useAuth } from "@/components/Providers";
import {
  Banner,
  Card,
  IconButton,
  List,
  PrimaryLink,
  Row,
  Screen,
  Section,
  Stack,
  StatusChip,
} from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate, INTENT_LABEL } from "@/lib/messages";
import { type Activity, type ConsentItem, LOCK_TEXT, type Profile } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

import s from "./beranda.module.css";

export default function HomePage() {
  return (
    <RequireAuth>
      <Home />
    </RequireAuth>
  );
}

async function loadProfile(): Promise<Profile | null> {
  try {
    return await raw<Profile>("/identity/profile");
  } catch (e) {
    if ((e as { status?: number }).status === 404) return null;
    throw e;
  }
}

function Home() {
  const { me } = useAuth();
  const profile = useLoad(loadProfile);
  const activity = useLoad(() => raw<Activity>("/dashboard/activity?weeks=1"));
  const inbox = useLoad(() => raw<{ items: ConsentItem[]; pending: number }>("/consent/inbox?status=pending"));
  const name = me?.display_name || me?.email.split("@")[0];
  const offline = [profile.error, activity.error, inbox.error].find((e) => e?.code === "OFFLINE");
  const week = activity.data?.this_week;
  const latest = inbox.data?.items[0];

  return (
    <Screen
      title="Beranda"
      tabs
      action={<IconButton icon="bell" label="Notifikasi" href="/notifikasi/" />}
    >
      <Stack gap={22}>
        <p style={{ color: "var(--muted)" }}>Halo, {name}.</p>
        {offline ? <Banner error>{errorText(offline)}</Banner> : null}

        <Section title="Status perlindungan">
          {profile.loading ? (
            <p role="status" style={{ color: "var(--dim)" }}>Memuat...</p>
          ) : profile.data ? (
            <div className={s.status}>
              <MediaStatus
                label="Wajah"
                enrolled={profile.data.face_enrolled}
                lock={LOCK_TEXT[profile.data.face_lock]}
                href="/enroll/"
              />
              <MediaStatus
                label="Suara"
                enrolled={profile.data.voice_enrolled}
                lock={LOCK_TEXT[profile.data.voice_lock]}
                href="/identitas/"
              />
            </div>
          ) : (
            <Card>
              <Stack gap={12}>
                <strong>Wajahmu belum terdaftar</strong>
                <p style={{ color: "var(--muted)" }}>
                  Kamu sudah terlindungi dari konten yang menghina, memfitnah, meniru, menipu, atau seksual. Daftarkan
                  wajah untuk menentukan sendiri siapa yang boleh memakainya.
                </p>
                <PrimaryLink href="/enroll/">Daftarkan wajah</PrimaryLink>
              </Stack>
            </Card>
          )}
        </Section>

        {profile.data ? (
          <Section title="Minggu ini">
            <Link href="/aktivitas/" className={s.activity} aria-label="Lihat dasbor aktivitas">
              <span className={s.metric}>
                <strong>{week?.attempts ?? 0}</strong> upaya penggunaan
              </span>
              <span className={s.metric} style={{ color: "var(--deny)" }}>
                <strong>{week?.blocked ?? 0}</strong> diblokir
              </span>
              <span className={s.metric} style={{ color: "var(--review)" }}>
                <strong>{inbox.data?.pending ?? 0}</strong> menunggu jawabanmu
              </span>
              <Icon name="chevron" />
            </Link>
          </Section>
        ) : null}

        {latest ? (
          <Section title="Permintaan persetujuan terbaru">
            <List>
              <Row
                icon="inbox"
                title={latest.requester_email ?? "Pengirim"}
                sub={`${INTENT_LABEL[latest.intent ?? ""] ?? latest.intent} · ${formatDate(latest.created_at)}`}
                end={<StatusChip status="REVIEW" text="Menunggu" />}
                href={`/consent/detail/?id=${latest.consent_id}`}
              />
            </List>
          </Section>
        ) : null}

        <Section title="Periksa permintaan">
          <List>
            <Row icon="scan" title="Periksa sebelum membuat konten AI" sub="Gambar, video, audio, atau teks." href="/periksa/" />
          </List>
        </Section>
      </Stack>
    </Screen>
  );
}

function MediaStatus({ label, enrolled, lock, href }: { label: string; enrolled: boolean; lock: string; href: string }) {
  return (
    <div className={s.media}>
      <span className={s.mediaHead}>
        <Icon name={enrolled ? "shieldCheck" : "shield"} />
        <strong>{label}</strong>
      </span>
      {enrolled ? (
        <>
          <StatusChip status="ALLOW" text="Terlindungi" />
          <span className={s.lock}>
            <Icon name={lock === LOCK_TEXT.NONE ? "unlock" : "lock"} size={16} /> {lock}
          </span>
        </>
      ) : (
        <Link href={href} className={s.enrollLink}>
          Daftarkan {label.toLowerCase()}
        </Link>
      )}
    </div>
  );
}
