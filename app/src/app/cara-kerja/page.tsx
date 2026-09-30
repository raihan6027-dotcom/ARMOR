"use client";

import { Icon, type IconName } from "@/components/Icon";
import { Card, PrimaryLink, Screen, Section, Stack, StatusChip } from "@/components/ui";

import s from "./cara-kerja.module.css";

const CHECKS: { icon: IconName; title: string; text: string }[] = [
  { icon: "user", title: "Wajah", text: "Apakah ada wajah terdaftar di media? Tanpa menebak nama." },
  { icon: "mic", title: "Suara", text: "Apakah suara di rekaman milik orang terdaftar, atau buatan?" },
  { icon: "text", title: "Nama", text: "Apakah prompt menyebut nama atau alias yang dilindungi?" },
  { icon: "info", title: "Maksud", text: "Untuk apa konten dibuat: pribadi, iklan, politik, atau merugikan?" },
  { icon: "chart", title: "Risiko", text: "Seberapa besar kerugiannya jika konten tersebar?" },
];

export default function HowItWorks() {
  return (
    <Screen title="Cara kerja ARMOR" back="/">
      <Stack gap={20}>
        <p style={{ color: "var(--muted)" }}>
          Sebelum AI membuat gambar, video, atau audio, permintaanmu melewati alur ini.
        </p>

        <ol className={s.flow} aria-label="Alur pemeriksaan">
          <li className={s.node}>
            <span className={s.nodeIcon}>
              <Icon name="upload" />
            </span>
            <span>
              <strong>Media dan prompt masuk</strong>
              <br />
              <span className={s.muted}>Foto, video, audio, atau teks saja.</span>
            </span>
          </li>
          <li className={s.group}>
            <strong className={s.groupTitle}>Lima pemeriksaan AI</strong>
            <ul className={s.checks}>
              {CHECKS.map((c) => (
                <li key={c.title} className={s.check}>
                  <span className={s.nodeIcon}>
                    <Icon name={c.icon} />
                  </span>
                  <span>
                    <strong>{c.title}</strong>
                    <br />
                    <span className={s.muted}>{c.text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </li>
          <li className={s.node}>
            <span className={s.nodeIcon}>
              <Icon name="shield" />
            </span>
            <span>
              <strong>Aturan dan izin pemilik</strong>
              <br />
              <span className={s.muted}>
                AI hanya memberi informasi. Keputusan diambil oleh aturan yang sama untuk semua orang.
              </span>
            </span>
          </li>
          <li className={s.outcomes}>
            <span className={s.outcome}>
              <StatusChip status="ALLOW" text="ALLOW" />
              <span className={s.muted}>Konten dibuat dan diberi label AI.</span>
            </span>
            <span className={s.outcome}>
              <StatusChip status="REVIEW" text="REVIEW" />
              <span className={s.muted}>Ditahan sampai pemilik atau peninjau menjawab.</span>
            </span>
            <span className={s.outcome}>
              <StatusChip status="DENY" text="DENY" />
              <span className={s.muted}>Ditolak, dengan alasan dan saran prompt yang aman.</span>
            </span>
          </li>
        </ol>

        <Section title="Dua lapis perlindungan">
          <Card>
            <strong>Perlindungan umum.</strong>{" "}
            <span className={s.muted}>
              Semua orang terlindungi dari konten yang menghina, memfitnah, meniru, menipu, atau seksual,
              walaupun tidak mendaftar.
            </span>
          </Card>
          <Card>
            <strong>Perlindungan personal.</strong>{" "}
            <span className={s.muted}>
              Jika kamu mendaftarkan wajah atau suara, kamu yang menentukan siapa boleh memakainya dan untuk
              apa.
            </span>
          </Card>
        </Section>

        <Section title="Janji kami">
          <ul className={s.promises}>
            <li>ARMOR tidak pernah menebak nama orang dari wajah atau suaranya.</li>
            <li>Foto dan rekaman tidak disimpan. Yang disimpan hanya pola angka terenkripsi milik pendaftar.</li>
            <li>Hanya pemilik yang mengendalikan identitasnya.</li>
          </ul>
        </Section>

        <PrimaryLink href="/daftar/">Lindungi identitas saya</PrimaryLink>
      </Stack>
    </Screen>
  );
}
