"use client";

import { RequireAuth } from "@/components/Providers";
import type { IconName } from "@/components/Icon";
import { Banner, Empty, List, Row, Screen, Stack, TextButton } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate } from "@/lib/messages";
import type { Notification } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

const ICON: Record<string, IconName> = {
  CONSENT_REQUEST: "inbox",
  CONSENT_ANSWERED: "check",
  USE_BLOCKED: "shield",
  OUTPUT_GUARD: "shieldCheck",
  CASE_STATUS: "alert",
  REQUEST_UPDATED: "scan",
};

function link(n: Notification): string | undefined {
  if (n.kind === "CONSENT_REQUEST" && n.data.consent_id) return `/consent/detail/?id=${n.data.consent_id}`;
  if (n.kind === "USE_BLOCKED" || n.kind === "OUTPUT_GUARD") return "/aktivitas/";
  if (n.kind === "CASE_STATUS") return "/kasus/";
  return undefined;
}

export default function NotificationsPage() {
  return (
    <RequireAuth>
      <Notifications />
    </RequireAuth>
  );
}

function Notifications() {
  const { data, error, reload } = useLoad(() => raw<{ items: Notification[]; unread: number }>("/notifications"));

  async function markAll() {
    await raw("/notifications/read", { method: "POST", body: JSON.stringify({}) });
    await reload();
  }

  return (
    <Screen
      title="Notifikasi"
      back="/beranda/"
      action={data && data.unread > 0 ? <TextButton onClick={() => void markAll()}>Tandai dibaca</TextButton> : undefined}
    >
      <Stack>
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {data && data.items.length === 0 ? (
          <Empty title="Belum ada notifikasi">
            <p style={{ color: "var(--muted)" }}>
              Permintaan persetujuan, upaya yang diblokir, dan kabar kasusmu akan muncul di sini.
            </p>
          </Empty>
        ) : null}
        {data && data.items.length > 0 ? (
          <List label="Notifikasi">
            {data.items.map((n) => (
              <Row
                key={n.notification_id}
                icon={ICON[n.kind] ?? "bell"}
                title={
                  <>
                    {n.read ? null : <span className="visually-hidden">Belum dibaca. </span>}
                    <span style={{ color: n.read ? "var(--muted)" : "var(--text)" }}>{n.title}</span>
                  </>
                }
                sub={`${n.body} · ${formatDate(n.created_at)}`}
                end={n.read ? undefined : <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 5, background: "var(--accent)" }} />}
                href={link(n)}
              />
            ))}
          </List>
        ) : null}
      </Stack>
    </Screen>
  );
}
