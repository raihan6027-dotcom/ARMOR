import { formatDate } from "@/lib/messages";
import type { CaseDetail } from "@/lib/types";

import s from "./timeline.module.css";

const ORDER = ["SUBMITTED", "REVIEWING", "RESOLVED"];
const LABEL: Record<string, string> = { SUBMITTED: "Diajukan", REVIEWING: "Ditinjau", RESOLVED: "Selesai" };

/** Vertical timeline: Diajukan, Ditinjau, Selesai. Future steps are shown dimmed. */
export function CaseTimeline({ detail }: { detail: CaseDetail }) {
  const reached = new Map(detail.timeline.map((e) => [e.status, e]));
  return (
    <ol className={s.timeline} aria-label="Status kasus">
      {ORDER.map((status) => {
        const ev = reached.get(status);
        return (
          <li key={status} className={s.item} data-done={ev ? "true" : undefined}>
            <span className={s.dot} aria-hidden="true" />
            <span className={s.body}>
              <strong>{LABEL[status]}</strong>
              {ev ? <span className={s.when}>{formatDate(ev.at)}</span> : <span className={s.when}>belum</span>}
              {ev?.note ? <span className={s.note}>{ev.note}</span> : null}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
