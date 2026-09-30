"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/Providers";
import { useToast } from "@/components/Toast";
import {
  Banner,
  BottomSheet,
  Empty,
  Field,
  IconButton,
  List,
  OptionChips,
  PrimaryButton,
  Row,
  Screen,
  Section,
  Stack,
  StatusChip,
} from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate, INTENT_LABEL } from "@/lib/messages";
import type { CircleMember, Profile } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

const SCOPE_INTENTS = ["PERSONAL_CREATION", "PERSONAL_EDITING", "SATIRE_PARODY", "COMMERCIAL_USE", "POLITICAL_USE"];

export default function CirclePage() {
  return (
    <RequireAuth>
      <Circle />
    </RequireAuth>
  );
}

function Circle() {
  const toast = useToast();
  const { data, error, reload } = useLoad(async () => {
    const profile = await raw<Profile>("/identity/profile");
    const res = await raw<{ items: CircleMember[] }>(`/circle?identity_id=${profile.identity_id}`);
    return { identityId: profile.identity_id, items: res.items };
  });
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [intents, setIntents] = useState<string[]>(["PERSONAL_CREATION"]);
  const [media, setMedia] = useState<"FACE" | "VOICE" | "BOTH">("FACE");
  const [until, setUntil] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function add() {
    if (!data) return;
    setFormError(null);
    try {
      await raw("/circle", {
        method: "POST",
        body: JSON.stringify({
          identity_id: data.identityId,
          email,
          intents,
          media: media === "BOTH" ? null : media,
          expires_at: until ? `${until}T23:59:59` : null,
        }),
      });
      setOpen(false);
      setEmail("");
      toast("Ditambahkan ke lingkaran tepercaya");
      void reload();
    } catch (err) {
      setFormError(errorText(err));
    }
  }

  async function remove(ref: string) {
    try {
      await raw(`/circle/${ref}`, { method: "DELETE" });
      toast("Dihapus dari lingkaran");
      void reload();
    } catch (err) {
      toast(errorText(err));
    }
  }

  return (
    <Screen title="Lingkaran tepercaya" back="/identitas/" action={<IconButton icon="plus" label="Tambah orang" onClick={() => setOpen(true)} />}>
      <Stack gap={20}>
        <p style={{ color: "var(--muted)" }}>
          Orang di sini boleh memakai identitasmu untuk tujuan yang kamu pilih tanpa bertanya dulu. Tujuan yang
          merugikan dan Lock tetap berlaku untuk mereka.
        </p>
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {data && data.items.length === 0 ? (
          <Empty title="Belum ada orang">
            <PrimaryButton onClick={() => setOpen(true)}>Tambah orang</PrimaryButton>
          </Empty>
        ) : null}
        {data && data.items.length > 0 ? (
          <List label="Anggota lingkaran">
            {data.items.map((m) => (
              <Row
                key={m.member_ref}
                icon="user"
                title={m.email ?? "Akun"}
                sub={`${(m.intents ?? ["Semua tujuan yang boleh"]).map((i) => INTENT_LABEL[i] ?? i).join(", ")} · ${
                  m.media === "VOICE" ? "suara" : m.media === "FACE" ? "wajah" : "wajah dan suara"
                }${m.expires_at ? ` · sampai ${formatDate(m.expires_at)}` : ""}`}
                end={
                  <>
                    {!m.active ? <StatusChip status="NEUTRAL" text="Berakhir" /> : null}
                    <IconButton icon="trash" label={`Hapus ${m.email}`} onClick={() => void remove(m.member_ref)} />
                  </>
                }
              />
            ))}
          </List>
        ) : null}

        <BottomSheet title="Tambah orang" open={open} onClose={() => setOpen(false)}>
          {formError ? <Banner error>{formError}</Banner> : null}
          <Field label="Email akun ARMOR" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Section title="Tujuan">
            <div role="group" aria-label="Tujuan yang diizinkan" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {SCOPE_INTENTS.map((i) => (
                <button
                  key={i}
                  type="button"
                  aria-pressed={intents.includes(i)}
                  className="chipToggle"
                  onClick={() => setIntents((cur) => (cur.includes(i) ? cur.filter((x) => x !== i) : [...cur, i]))}
                  style={{
                    minHeight: 44,
                    padding: "8px 14px",
                    borderRadius: 22,
                    border: `1px solid ${intents.includes(i) ? "var(--accent)" : "var(--line)"}`,
                    background: intents.includes(i) ? "color-mix(in srgb, var(--accent) 18%, transparent)" : "transparent",
                    cursor: "pointer",
                  }}
                >
                  {INTENT_LABEL[i]}
                </button>
              ))}
            </div>
          </Section>
          <Section title="Media">
            <OptionChips
              label="Media"
              value={media}
              onChange={setMedia}
              options={[
                { value: "FACE", label: "Wajah" },
                { value: "VOICE", label: "Suara" },
                { value: "BOTH", label: "Keduanya" },
              ]}
            />
          </Section>
          <Field label="Berlaku sampai (opsional)" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
          <PrimaryButton onClick={() => void add()} disabled={!email || intents.length === 0}>
            Tambahkan
          </PrimaryButton>
        </BottomSheet>
      </Stack>
    </Screen>
  );
}
