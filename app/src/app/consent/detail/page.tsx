"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { FaceLines, ScanFrame } from "@/components/Logo3D";
import { RequireAuth, useAuth } from "@/components/Providers";
import { useToast } from "@/components/Toast";
import {
  Banner,
  BottomSheet,
  Field,
  List,
  OptionChips,
  PrimaryButton,
  Row,
  Screen,
  Section,
  Stack,
  StatusChip,
  TextButton,
} from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate, INTENT_LABEL, MEDIA_LABEL } from "@/lib/messages";
import { STATE_CHIP, type ConsentItem } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";


type Validity = "ONCE" | "DAYS_1" | "DAYS_7" | "DAYS_30" | "UNTIL";

export default function ConsentDetailPage() {
  return (
    <RequireAuth>
      <Suspense>
        <Detail />
      </Suspense>
    </RequireAuth>
  );
}

function Detail() {
  const id = useSearchParams().get("id") ?? "";
  const toast = useToast();
  const { refreshPending } = useAuth();
  const { data: c, error, setData } = useLoad(() => raw<ConsentItem>(`/consent/${id}`), id);
  const [sheet, setSheet] = useState(false);
  const [validity, setValidity] = useState<Validity>("ONCE");
  const [until, setUntil] = useState("");
  const [media, setMedia] = useState<"FACE" | "VOICE" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function act(path: string, body?: object, done?: string) {
    setBusy(true);
    setActionError(null);
    try {
      const updated = await raw<ConsentItem>(`/consent/${id}/${path}`, {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
      });
      setData(updated);
      setSheet(false);
      void refreshPending();
      if (done) toast(done);
    } catch (err) {
      setActionError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <Screen title="Permintaan" back="/consent/">
        <Banner error>{errorText(error)}</Banner>
      </Screen>
    );
  }
  if (!c) {
    return (
      <Screen title="Permintaan" back="/consent/">
        <p role="status" style={{ color: "var(--dim)" }}>Memuat...</p>
      </Screen>
    );
  }

  const chip = STATE_CHIP[c.state];
  return (
    <Screen title="Permintaan" back="/consent/">
      <Stack gap={20}>
        <StatusChip status={chip.status} text={chip.text} />
        <List label="Rincian permintaan">
          <Row icon="user" title="Dari" sub={c.requester_email ?? "Pengirim"} />
          <Row icon="info" title="Tujuan" sub={INTENT_LABEL[c.intent ?? ""] ?? "Semua tujuan"} />
          <Row icon={c.media === "VOICE" ? "mic" : "image"} title="Media" sub={`${MEDIA_LABEL[c.media ?? ""] ?? "Apa pun"}${c.media_type ? ` dalam ${MEDIA_LABEL[c.media_type]?.toLowerCase()}` : ""}`} />
          <Row icon="clock" title="Diminta" sub={formatDate(c.created_at)} />
          {c.expires_at ? <Row icon="clock" title="Berlaku sampai" sub={formatDate(c.expires_at)} /> : null}
        </List>

        {c.prompt ? (
          <Section title="Isi prompt">
            <blockquote style={{ margin: 0, padding: "12px 14px", borderLeft: "none", background: "var(--surface)", borderRadius: 10 }}>
              {c.prompt}
            </blockquote>
          </Section>
        ) : null}

        <Section title="Pratinjau">
          <div style={{ transform: "scale(0.6)", transformOrigin: "top center", height: 200 }} aria-hidden="true">
            <ScanFrame>
              <FaceLines scanning={false} />
            </ScanFrame>
          </div>
          <p style={{ color: "var(--dim)", fontSize: 14 }}>
            Ilustrasi. Media asli tidak disimpan ARMOR, jadi tidak bisa ditampilkan di sini.
          </p>
        </Section>

        {actionError ? <Banner error>{actionError}</Banner> : null}

        {c.state === "PENDING" ? (
          <Stack gap={8}>
            <PrimaryButton onClick={() => setSheet(true)} disabled={busy}>
              Setujui
            </PrimaryButton>
            <TextButton onClick={() => void act("respond", { action: "DENY" }, "Permintaan ditolak")} disabled={busy}>
              Tolak
            </TextButton>
            <TextButton danger onClick={() => void act("respond", { action: "BLOCK" }, "Pengirim diblokir")} disabled={busy}>
              Blokir pengirim
            </TextButton>
          </Stack>
        ) : null}

        {c.state === "GRANTED" ? (
          <Stack gap={8}>
            <p style={{ color: "var(--muted)" }}>
              Kamu bisa mencabut persetujuan ini kapan saja. Setelah dicabut, pengirim harus meminta lagi.
            </p>
            <TextButton danger onClick={() => void act("revoke", undefined, "Persetujuan dicabut")} disabled={busy}>
              Cabut persetujuan
            </TextButton>
          </Stack>
        ) : null}

        <BottomSheet title="Setujui dengan batasan" open={sheet} onClose={() => setSheet(false)}>
          <Section title="Tujuan">
            <p>{INTENT_LABEL[c.intent ?? ""] ?? "Semua tujuan"}</p>
          </Section>
          <Section title="Media">
            <OptionChips
              label="Media yang diizinkan"
              value={media ?? (c.media as "FACE" | "VOICE" | null)}
              onChange={setMedia}
              options={[
                { value: "FACE", label: "Wajah" },
                { value: "VOICE", label: "Suara" },
              ]}
            />
          </Section>
          <Section title="Masa berlaku">
            <OptionChips
              label="Masa berlaku"
              value={validity}
              onChange={setValidity}
              options={[
                { value: "ONCE", label: "Sekali pakai" },
                { value: "DAYS_1", label: "1 hari" },
                { value: "DAYS_7", label: "7 hari" },
                { value: "DAYS_30", label: "30 hari" },
                { value: "UNTIL", label: "Sampai tanggal" },
              ]}
            />
            {validity === "UNTIL" ? (
              <Field label="Berlaku sampai" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
            ) : null}
          </Section>
          <PrimaryButton
            disabled={busy || (validity === "UNTIL" && !until)}
            onClick={() =>
              void act(
                "respond",
                {
                  action: "APPROVE",
                  validity,
                  until: validity === "UNTIL" ? until : undefined,
                  media: media ?? undefined,
                },
                "Persetujuan diberikan",
              )
            }
          >
            Setujui
          </PrimaryButton>
        </BottomSheet>
      </Stack>
    </Screen>
  );
}
