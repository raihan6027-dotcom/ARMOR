"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { CaseTimeline } from "@/components/CaseTimeline";
import { RequireAuth } from "@/components/Providers";
import { Banner, Field, PrimaryButton, Screen, Stack, TextLink } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText } from "@/lib/messages";
import type { CaseDetail } from "@/lib/types";

export default function AppealPage() {
  return (
    <RequireAuth>
      <Suspense>
        <Appeal />
      </Suspense>
    </RequireAuth>
  );
}

function Appeal() {
  const requestId = useSearchParams().get("request") ?? "";
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<CaseDetail | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (note.trim().length < 3) return setError("Jelaskan konteksnya dulu.");
    setBusy(true);
    setError(null);
    try {
      setCreated(
        await raw<CaseDetail>("/cases", {
          method: "POST",
          body: JSON.stringify({ kind: "APPEAL", request_id: requestId, note }),
        }),
      );
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (created) {
    return (
      <Screen title="Banding diajukan" back="/periksa/">
        <Stack>
          <p style={{ color: "var(--muted)" }}>
            Peninjau ARMOR akan membaca konteksmu. Jika label tujuan atau risikonya keliru, keputusan dinilai ulang
            dengan label yang benar.
          </p>
          <CaseTimeline detail={created} />
          <TextLink href="/kasus/">Lihat semua kasus</TextLink>
        </Stack>
      </Screen>
    );
  }

  return (
    <Screen title="Ajukan banding" back="/periksa/">
      <form onSubmit={submit}>
        <Stack>
          <p style={{ color: "var(--muted)" }}>
            Ceritakan konteks yang belum terbaca dari prompt, misalnya untuk apa konten ini dibuat dan siapa yang
            akan melihatnya.
          </p>
          {!requestId ? <Banner error>Permintaan yang dibanding tidak ditemukan.</Banner> : null}
          <Field
            label="Konteks tambahan"
            multiline
            value={note}
            maxLength={2000}
            onChange={(e) => setNote(e.target.value)}
            error={error}
          />
          <PrimaryButton type="submit" disabled={busy || !requestId}>
            {busy ? "Mengirim..." : "Kirim banding"}
          </PrimaryButton>
        </Stack>
      </form>
    </Screen>
  );
}
