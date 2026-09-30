"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/Providers";
import { useToast } from "@/components/Toast";
import {
  Banner,
  BottomSheet,
  Field,
  List,
  PrimaryButton,
  Row,
  Screen,
  Section,
  Stack,
  TextButton,
} from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate } from "@/lib/messages";
import { useLoad } from "@/lib/useLoad";

interface MyData {
  retention: Record<string, string>;
  account: { email: string; created_at: string };
  identities: {
    identity_id: string;
    face_embedding_stored: boolean;
    face_enrolled_at: string | null;
    voice_embedding_stored: boolean;
    voice_enrolled_at: string | null;
  }[];
  biometric_consents: { media: string; text_version: string; agreed_at: string; revoked_at: string | null }[];
  requests_made: unknown[];
  consent_requests_received: unknown[];
}

type Confirm = null | { kind: "revoke"; media: "FACE" | "VOICE" } | { kind: "delete"; step: 1 | 2 };

export default function MyDataPage() {
  return (
    <RequireAuth>
      <MyDataView />
    </RequireAuth>
  );
}

function MyDataView() {
  const toast = useToast();
  const { data, error, reload } = useLoad(() => raw<MyData>("/me/data"));
  const [confirm, setConfirm] = useState<Confirm>(null);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const identity = data?.identities[0];

  function download() {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `armor-data-saya-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function run(path: string, method: string, done: string) {
    setBusy(true);
    try {
      await raw(path, { method });
      toast(done);
      setConfirm(null);
      setTyped("");
      await reload();
    } catch (err) {
      toast(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title="Data saya" back="/identitas/">
      <Stack gap={22}>
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {data ? (
          <>
            <Section title="Yang disimpan ARMOR">
              <List>
                <Row icon="user" title="Akun" sub={`${data.account.email}. ${data.retention.account}`} />
                <Row
                  icon="shield"
                  title="Pola wajah (terenkripsi)"
                  sub={
                    identity?.face_embedding_stored
                      ? `Tersimpan sejak ${formatDate(identity.face_enrolled_at)}. ${data.retention.face_embedding}`
                      : "Tidak disimpan."
                  }
                />
                <Row
                  icon="mic"
                  title="Pola suara (terenkripsi)"
                  sub={
                    identity?.voice_embedding_stored
                      ? `Tersimpan sejak ${formatDate(identity.voice_enrolled_at)}. ${data.retention.voice_embedding}`
                      : "Tidak disimpan."
                  }
                />
                <Row icon="image" title="Foto dan rekaman" sub={data.retention.photos_and_recordings} />
                <Row
                  icon="scan"
                  title="Log keputusan"
                  sub={`${data.requests_made.length} permintaanmu. ${data.retention.decision_log}`}
                />
                <Row
                  icon="check"
                  title="Catatan persetujuan"
                  sub={`${data.biometric_consents.length} catatan. ${data.retention.consent_records}`}
                />
              </List>
            </Section>

            <PrimaryButton onClick={download}>Unduh data saya</PrimaryButton>

            {identity ? (
              <Section title="Cabut atau hapus">
                <Stack gap={4}>
                  {identity.face_embedding_stored ? (
                    <TextButton danger onClick={() => setConfirm({ kind: "revoke", media: "FACE" })}>
                      Cabut persetujuan wajah
                    </TextButton>
                  ) : null}
                  {identity.voice_embedding_stored ? (
                    <TextButton danger onClick={() => setConfirm({ kind: "revoke", media: "VOICE" })}>
                      Cabut persetujuan suara
                    </TextButton>
                  ) : null}
                  <TextButton danger onClick={() => setConfirm({ kind: "delete", step: 1 })}>
                    Hapus identitas
                  </TextButton>
                </Stack>
              </Section>
            ) : null}
          </>
        ) : null}

        <BottomSheet
          title={confirm?.kind === "revoke" ? `Cabut persetujuan ${confirm.media === "FACE" ? "wajah" : "suara"}?` : "Hapus identitas?"}
          open={confirm !== null}
          onClose={() => {
            setConfirm(null);
            setTyped("");
          }}
        >
          {confirm?.kind === "revoke" ? (
            <>
              <p>
                Pola {confirm.media === "FACE" ? "wajah" : "suara"}mu langsung dihapus. ARMOR tidak lagi mengenali{" "}
                {confirm.media === "FACE" ? "wajah" : "suara"}mu sebagai terdaftar, jadi Lock dan izinmu tidak berlaku
                lagi untuk media ini. Perlindungan umum tetap berlaku.
              </p>
              <PrimaryButton danger disabled={busy} onClick={() => void run(`/identity/me/revoke?media=${confirm.media}`, "POST", "Persetujuan dicabut")}>
                Cabut dan hapus
              </PrimaryButton>
            </>
          ) : confirm?.kind === "delete" && confirm.step === 1 ? (
            <>
              <p>Yang akan dihapus permanen:</p>
              <ul style={{ margin: 0, paddingLeft: 20, color: "var(--muted)" }}>
                <li>pola wajah dan suara,</li>
                <li>Lock, izin per tujuan, dan lingkaran tepercaya,</li>
                <li>persetujuan yang pernah kamu berikan atau terima.</li>
              </ul>
              <p>Akunmu tetap ada. Kamu bisa mendaftar lagi kapan saja.</p>
              <PrimaryButton danger onClick={() => setConfirm({ kind: "delete", step: 2 })}>
                Lanjutkan
              </PrimaryButton>
            </>
          ) : (
            <>
              <Field label='Ketik "HAPUS" untuk memastikan' value={typed} onChange={(e) => setTyped(e.target.value)} />
              <PrimaryButton danger disabled={busy || typed !== "HAPUS"} onClick={() => void run("/identity/me", "DELETE", "Identitas dihapus")}>
                Hapus permanen
              </PrimaryButton>
            </>
          )}
        </BottomSheet>
      </Stack>
    </Screen>
  );
}
