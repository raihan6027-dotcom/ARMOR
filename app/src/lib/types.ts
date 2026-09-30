/** Shapes of backend responses that the OpenAPI schema leaves untyped (plain dicts). */

export interface Profile {
  identity_id: string;
  status: string;
  display_name?: string | null;
  is_child: boolean;
  face_enrolled: boolean;
  voice_enrolled: boolean;
  face_lock: LockLevel;
  voice_lock: LockLevel;
}

export type LockLevel = "NONE" | "COMMERCIAL_POLITICAL" | "ALL";

export interface WeekCounts {
  week_start: string;
  attempts: number;
  blocked: number;
  approved: number;
  pending: number;
}

export interface Activity {
  weeks: WeekCounts[];
  this_week: WeekCounts;
  totals: Omit<WeekCounts, "week_start">;
  recent: {
    request_id: string;
    identity_id: string;
    created_at: string;
    media_type: string | null;
    intent: string | null;
    decision: "ALLOW" | "REVIEW" | "DENY";
    reason_code: string;
    reason: string;
    sender: string;
  }[];
}

export interface ConsentItem {
  consent_id: string;
  identity_id: string;
  requester_email?: string | null;
  intent?: string | null;
  media?: string | null;
  prompt?: string | null;
  media_type?: string | null;
  status: "PENDING" | "GRANTED" | "DENIED" | "NONE";
  state: "PENDING" | "GRANTED" | "DENIED" | "REVOKED" | "EXPIRED" | "USED";
  validity?: string | null;
  expires_at?: string | null;
  answered_at?: string | null;
  created_at?: string | null;
}

export interface Notification {
  notification_id: string;
  kind: string;
  title: string;
  body: string;
  data: Record<string, string>;
  read: boolean;
  created_at: string;
}

export interface CircleMember {
  member_ref: string;
  identity_id: string;
  email: string | null;
  intents: string[] | null;
  media: string | null;
  expires_at: string | null;
  active: boolean;
  created_at: string;
}

export interface CaseSummary {
  case_id: string;
  kind: "APPEAL" | "DISPUTE";
  status: "SUBMITTED" | "REVIEWING" | "RESOLVED";
  status_label: string;
  created_at: string;
  priority: string;
}

export interface CaseDetail {
  case_id: string;
  kind: "APPEAL" | "DISPUTE";
  status: "SUBMITTED" | "REVIEWING" | "RESOLVED";
  status_label: string;
  request_id: string | null;
  note: string | null;
  outcome: string | null;
  resolution_note: string | null;
  timeline: { status: string; label: string; note: string | null; at: string }[];
  created_at: string;
}

export const LOCK_TEXT: Record<LockLevel, string> = {
  NONE: "Terbuka untuk pribadi",
  COMMERCIAL_POLITICAL: "Kunci komersial dan politik",
  ALL: "Kunci semua",
};

export const STATE_CHIP: Record<ConsentItem["state"], { status: "ALLOW" | "REVIEW" | "DENY" | "NEUTRAL"; text: string }> = {
  PENDING: { status: "REVIEW", text: "Menunggu" },
  GRANTED: { status: "ALLOW", text: "Disetujui" },
  DENIED: { status: "DENY", text: "Ditolak" },
  REVOKED: { status: "NEUTRAL", text: "Dicabut" },
  EXPIRED: { status: "NEUTRAL", text: "Kedaluwarsa" },
  USED: { status: "NEUTRAL", text: "Sudah dipakai" },
};

