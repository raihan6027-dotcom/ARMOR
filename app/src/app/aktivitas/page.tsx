"use client";

import { RequireAuth } from "@/components/Providers";
import { Banner, Empty, List, Row, Screen, Section, Stack, StatusChip } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, formatDate, INTENT_LABEL, MEDIA_LABEL } from "@/lib/messages";
import type { Activity, WeekCounts } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

import s from "./aktivitas.module.css";

const SERIES: { key: keyof Omit<WeekCounts, "week_start" | "attempts">; label: string; color: string }[] = [
  { key: "blocked", label: "Diblokir", color: "var(--deny)" },
  { key: "approved", label: "Disetujui", color: "var(--allow)" },
  { key: "pending", label: "Menunggu", color: "var(--review)" },
];

export default function ActivityPage() {
  return (
    <RequireAuth>
      <Dashboard />
    </RequireAuth>
  );
}

function Chart({ weeks }: { weeks: WeekCounts[] }) {
  const max = Math.max(1, ...weeks.map((w) => w.attempts));
  const W = 320;
  const H = 160;
  const band = W / weeks.length;
  const bar = Math.min(26, band * 0.6);
  return (
    <figure className={s.figure}>
      <svg viewBox={`0 0 ${W} ${H + 22}`} role="img" aria-label="Grafik upaya penggunaan per minggu" className={s.chart}>
        {weeks.map((w, i) => {
          let y = H;
          const x = i * band + (band - bar) / 2;
          return (
            <g key={w.week_start}>
              {SERIES.map((sr) => {
                const h = (w[sr.key] / max) * (H - 8);
                y -= h;
                return h > 0 ? <rect key={sr.key} x={x} y={y} width={bar} height={h} fill={sr.color} rx={2} /> : null;
              })}
              <text x={x + bar / 2} y={H + 16} textAnchor="middle" className={s.tick}>
                {new Date(`${w.week_start}T00:00:00`).toLocaleDateString("id-ID", { day: "numeric", month: "short" })}
              </text>
            </g>
          );
        })}
        <line x1="0" y1={H} x2={W} y2={H} stroke="var(--line)" />
      </svg>
      <figcaption className={s.legend}>
        {SERIES.map((sr) => (
          <span key={sr.key}>
            <i style={{ background: sr.color }} aria-hidden="true" /> {sr.label}
          </span>
        ))}
      </figcaption>
      <table className="visually-hidden">
        <caption>Upaya per minggu</caption>
        <thead>
          <tr>
            <th>Minggu</th>
            {SERIES.map((sr) => (
              <th key={sr.key}>{sr.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((w) => (
            <tr key={w.week_start}>
              <td>{w.week_start}</td>
              {SERIES.map((sr) => (
                <td key={sr.key}>{w[sr.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

const DECISION: Record<string, "ALLOW" | "REVIEW" | "DENY"> = { ALLOW: "ALLOW", REVIEW: "REVIEW", DENY: "DENY" };

function Dashboard() {
  const { data, error } = useLoad(() => raw<Activity>("/dashboard/activity?weeks=8"));
  return (
    <Screen title="Aktivitas" back="/identitas/">
      <Stack gap={22}>
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {data ? (
          <>
            <div className={s.totals}>
              <span><strong>{data.totals.attempts}</strong>upaya</span>
              <span style={{ color: "var(--deny)" }}><strong>{data.totals.blocked}</strong>diblokir</span>
              <span style={{ color: "var(--allow)" }}><strong>{data.totals.approved}</strong>disetujui</span>
              <span style={{ color: "var(--review)" }}><strong>{data.totals.pending}</strong>menunggu</span>
            </div>
            <p style={{ color: "var(--dim)", fontSize: 14 }}>Delapan minggu terakhir.</p>
            <Chart weeks={data.weeks} />
            <Section title="Kejadian terbaru">
              {data.recent.length === 0 ? (
                <Empty title="Belum ada aktivitas">
                  <p style={{ color: "var(--muted)" }}>
                    Setiap kali seseorang mencoba memakai wajah atau suaramu lewat layanan yang memakai ARMOR, catatannya
                    muncul di sini.
                  </p>
                </Empty>
              ) : (
                <List label="Kejadian terbaru">
                  {data.recent.map((e) => (
                    <Row
                      key={`${e.request_id}-${e.identity_id}`}
                      icon={e.decision === "DENY" ? "shield" : "info"}
                      title={e.sender}
                      sub={`${INTENT_LABEL[e.intent ?? ""] ?? e.intent} · ${MEDIA_LABEL[e.media_type ?? ""] ?? ""} · ${formatDate(e.created_at)}. ${e.reason}`}
                      end={<StatusChip status={DECISION[e.decision]} />}
                    />
                  ))}
                </List>
              )}
            </Section>
          </>
        ) : null}
      </Stack>
    </Screen>
  );
}
