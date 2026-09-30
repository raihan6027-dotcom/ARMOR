"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { CaseTimeline } from "@/components/CaseTimeline";
import { RequireAuth } from "@/components/Providers";
import { Banner, Empty, List, Row, Screen, Stack, StatusChip } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate } from "@/lib/messages";
import type { CaseDetail, CaseSummary } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

const KIND: Record<string, string> = { APPEAL: "Banding", DISPUTE: "Sengketa pendaftaran" };
const CHIP: Record<string, "REVIEW" | "ALLOW" | "NEUTRAL"> = { SUBMITTED: "NEUTRAL", REVIEWING: "REVIEW", RESOLVED: "ALLOW" };

export default function CasesPage() {
  return (
    <RequireAuth>
      <Suspense>
        <Cases />
      </Suspense>
    </RequireAuth>
  );
}

function Cases() {
  const id = useSearchParams().get("id");
  const list = useLoad(() => raw<{ items: CaseSummary[] }>("/cases"));
  const detail = useLoad(() => (id ? raw<CaseDetail>(`/cases/${id}`) : Promise.resolve(null)), id ?? "");

  if (id) {
    const d = detail.data;
    return (
      <Screen title={d ? KIND[d.kind] : "Kasus"} back="/kasus/">
        <Stack>
          {detail.error ? <Banner error>{errorText(detail.error)}</Banner> : null}
          {d ? (
            <>
              {d.note ? <p style={{ color: "var(--muted)" }}>{d.note}</p> : null}
              <CaseTimeline detail={d} />
              {d.resolution_note ? <Banner>{d.resolution_note}</Banner> : null}
            </>
          ) : null}
        </Stack>
      </Screen>
    );
  }

  return (
    <Screen title="Kasus" back="/identitas/">
      <Stack>
        {list.error ? <Banner error>{errorText(list.error)}</Banner> : null}
        {list.data && list.data.items.length === 0 ? (
          <Empty title="Belum ada kasus">
            <p style={{ color: "var(--muted)" }}>
              Banding atas keputusan yang ditolak dan sengketa pendaftaran wajah muncul di sini beserta statusnya.
            </p>
          </Empty>
        ) : null}
        {list.data && list.data.items.length > 0 ? (
          <List label="Kasus">
            {list.data.items.map((c) => (
              <Row
                key={c.case_id}
                icon="alert"
                title={KIND[c.kind]}
                sub={formatDate(c.created_at)}
                end={<StatusChip status={CHIP[c.status]} text={c.status_label} />}
                href={`/kasus/?id=${c.case_id}`}
              />
            ))}
          </List>
        ) : null}
      </Stack>
    </Screen>
  );
}
