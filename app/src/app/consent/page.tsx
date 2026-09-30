"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/Providers";
import { Banner, Empty, List, Row, Screen, Segmented, Stack, StatusChip } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate, INTENT_LABEL, MEDIA_LABEL } from "@/lib/messages";
import { STATE_CHIP, type ConsentItem } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

export default function ConsentInboxPage() {
  return (
    <RequireAuth>
      <Inbox />
    </RequireAuth>
  );
}

function Inbox() {
  const [filter, setFilter] = useState<"pending" | "answered">("pending");
  const { data, error, loading } = useLoad(
    () => raw<{ items: ConsentItem[]; pending: number }>(`/consent/inbox?status=${filter}`),
    filter,
  );

  return (
    <Screen title="Consent" tabs>
      <Stack>
        <Segmented
          label="Saring permintaan"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "pending", label: `Menunggu${data && filter === "pending" ? ` (${data.pending})` : ""}` },
            { value: "answered", label: "Dijawab" },
          ]}
        />
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {loading && !data ? <p role="status" style={{ color: "var(--dim)" }}>Memuat...</p> : null}
        {data && data.items.length === 0 ? (
          filter === "pending" ? (
            <Empty title="Tidak ada yang menunggu">
              <p style={{ color: "var(--muted)" }}>
                Jika seseorang ingin memakai wajah atau suaramu untuk tujuan yang perlu izinmu, permintaannya muncul
                di sini. Tujuan yang sudah kamu izinkan atau tolak di Identitas tidak akan ditanyakan lagi.
              </p>
            </Empty>
          ) : (
            <Empty title="Belum ada yang dijawab" />
          )
        ) : null}
        {data && data.items.length > 0 ? (
          <List label="Permintaan persetujuan">
            {data.items.map((c) => (
              <Row
                key={c.consent_id}
                icon={c.media === "VOICE" ? "mic" : "user"}
                title={c.requester_email ?? "Pengirim"}
                sub={`${INTENT_LABEL[c.intent ?? ""] ?? c.intent ?? "Semua tujuan"} · ${MEDIA_LABEL[c.media ?? ""] ?? "Media apa pun"} · ${formatDate(c.created_at)}`}
                end={<StatusChip status={STATE_CHIP[c.state].status} text={STATE_CHIP[c.state].text} />}
                href={`/consent/detail/?id=${c.consent_id}`}
              />
            ))}
          </List>
        ) : null}
      </Stack>
    </Screen>
  );
}
