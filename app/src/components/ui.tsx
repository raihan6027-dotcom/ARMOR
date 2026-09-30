"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useId, useRef } from "react";

import { Icon, type IconName } from "./Icon";
import { useAuth } from "./Providers";
import s from "./ui.module.css";

type Status = "ALLOW" | "REVIEW" | "DENY";

export function Screen({
  title,
  back,
  tabs = false,
  action,
  children,
}: {
  title?: string;
  back?: string | true;
  tabs?: boolean;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  const router = useRouter();
  return (
    <main className={`${s.frame} ${tabs ? s.frameTabs : ""}`}>
      {title || back || action ? (
        <header className={s.header}>
          {back ? (
            typeof back === "string" ? (
              <Link href={back} className={s.iconButton} aria-label="Kembali">
                <Icon name="back" />
              </Link>
            ) : (
              <button type="button" className={s.iconButton} aria-label="Kembali" onClick={() => router.back()}>
                <Icon name="back" />
              </button>
            )
          ) : null}
          {title ? <h1>{title}</h1> : <span style={{ flex: 1 }} />}
          {action}
        </header>
      ) : null}
      {children}
      {tabs ? <TabBar /> : null}
    </main>
  );
}

export function Stack({ children, gap = 16 }: { children: React.ReactNode; gap?: number }) {
  return (
    <div className={s.stack} style={{ gap }}>
      {children}
    </div>
  );
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={s.section} aria-label={title}>
      <h2 className={s.sectionTitle}>{title}</h2>
      {children}
    </section>
  );
}

export function Lead({ children }: { children: React.ReactNode }) {
  return <p className={s.lead}>{children}</p>;
}

export function PrimaryButton({
  children,
  danger,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { danger?: boolean }) {
  return (
    <button type="button" {...props} className={`${s.primary} ${danger ? s.danger : ""}`}>
      {children}
    </button>
  );
}

export function PrimaryLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={s.primary}>
      {children}
    </Link>
  );
}

export function TextButton({
  children,
  danger,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { danger?: boolean }) {
  return (
    <button type="button" {...props} className={`${s.textLink} ${danger ? s.dangerText : ""}`}>
      {children}
    </button>
  );
}

export function TextLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={s.textLink}>
      {children}
    </Link>
  );
}

export function IconButton({
  icon,
  label,
  href,
  onClick,
}: {
  icon: IconName;
  label: string;
  href?: string;
  onClick?: () => void;
}) {
  if (href) {
    return (
      <Link href={href} className={s.iconButton} aria-label={label}>
        <Icon name={icon} />
      </Link>
    );
  }
  return (
    <button type="button" className={s.iconButton} aria-label={label} onClick={onClick}>
      <Icon name={icon} />
    </button>
  );
}

export function Field({
  label,
  error,
  hint,
  multiline,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> &
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
    label: string;
    error?: string | null;
    hint?: string;
    multiline?: boolean;
  }) {
  const id = useId();
  const described = error ? `${id}-err` : hint ? `${id}-hint` : undefined;
  const common = {
    id,
    className: s.input,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": described,
  };
  return (
    <div className={s.field}>
      <label className={s.label} htmlFor={id}>
        {label}
      </label>
      {multiline ? (
        <textarea {...(props as React.TextareaHTMLAttributes<HTMLTextAreaElement>)} {...common} />
      ) : (
        <input {...(props as React.InputHTMLAttributes<HTMLInputElement>)} {...common} />
      )}
      {error ? (
        <p id={`${id}-err`} className={s.fieldError} role="alert">
          <Icon name="alert" size={18} />
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className={s.hint}>
          {hint}
        </p>
      ) : null}
    </div>
  );
}

export function Checkbox({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <label className={s.checkbox}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{children}</span>
    </label>
  );
}

const STATUS_TEXT: Record<Status, string> = { ALLOW: "Diizinkan", REVIEW: "Ditinjau", DENY: "Ditolak" };
const STATUS_ICON: Record<Status, IconName> = { ALLOW: "check", REVIEW: "clock", DENY: "cross" };

export function StatusChip({ status, text }: { status: Status | "NEUTRAL"; text?: string }) {
  const known = status !== "NEUTRAL";
  return (
    <span className={`${s.chip} ${s[status]}`}>
      {known ? <Icon name={STATUS_ICON[status]} size={16} /> : null}
      {text ?? (known ? STATUS_TEXT[status] : "")}
    </span>
  );
}

export function Stamp({ status, caption }: { status: Status; caption?: string }) {
  return (
    <div className={`${s.stamp} ${s[status]}`} role="status">
      <span className={s.stampWord}>{status}</span>
      {caption ? <span style={{ color: "var(--text)", fontWeight: 700 }}>{caption}</span> : null}
    </div>
  );
}

export function Card({ children }: { children: React.ReactNode }) {
  return <div className={s.card}>{children}</div>;
}

export function List({ children, label }: { children: React.ReactNode; label?: string }) {
  return (
    <ul className={s.list} aria-label={label}>
      {children}
    </ul>
  );
}

export function Row({
  icon,
  title,
  sub,
  end,
  href,
  onClick,
}: {
  icon?: IconName;
  title: React.ReactNode;
  sub?: React.ReactNode;
  end?: React.ReactNode;
  href?: string;
  onClick?: () => void;
}) {
  const inner = (
    <>
      {icon ? (
        <span className={s.rowIcon}>
          <Icon name={icon} />
        </span>
      ) : null}
      <span className={s.rowMain}>
        <span className={s.rowTitle}>{title}</span>
        {sub ? <span className={s.rowSub}>{sub}</span> : null}
      </span>
      <span className={s.rowEnd}>
        {end}
        {href || onClick ? <Icon name="chevron" size={18} /> : null}
      </span>
    </>
  );
  return (
    <li>
      {href ? (
        <Link href={href} className={s.row}>
          {inner}
        </Link>
      ) : onClick ? (
        <button type="button" className={s.row} onClick={onClick}>
          {inner}
        </button>
      ) : (
        <div className={s.row} style={{ cursor: "default" }}>
          {inner}
        </div>
      )}
    </li>
  );
}

export function Switch({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={s.switch}
      onClick={() => onChange(!checked)}
    />
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className={s.segmented}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={s.segment}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function OptionChips<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { value: T; label: string }[];
  value: T | null;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className={s.options}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={s.option}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function SuggestionChip({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button type="button" className={s.option} onClick={onClick}>
      {children}
    </button>
  );
}

export function BottomSheet({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      prev?.focus();
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className={s.sheetBackdrop} onClick={onClose}>
      <div
        className={s.sheet}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={ref}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={s.sheetHead}>
          <h2>{title}</h2>
          <IconButton icon="close" label="Tutup" onClick={onClose} />
        </div>
        {children}
      </div>
    </div>
  );
}

export type StepState = "pending" | "active" | "done" | "skipped" | "unavailable";

export function Steps({ steps }: { steps: { label: string; state: StepState; note?: string }[] }) {
  return (
    <ol className={s.steps} aria-live="polite">
      {steps.map((st) => (
        <li key={st.label} className={s.step}>
          <StepMark state={st.state} />
          <span className={s.stepLabel} style={{ color: st.state === "pending" ? "var(--dim)" : undefined }}>
            {st.label}
          </span>
          {st.note ? <span className={s.stepNote}>{st.note}</span> : null}
        </li>
      ))}
    </ol>
  );
}

function StepMark({ state }: { state: StepState }) {
  if (state === "done") {
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" aria-label="selesai" role="img">
        <circle cx="10" cy="10" r="10" fill="var(--allow)" />
        <path d="M5.5 10.5 L8.5 13.5 L14.5 7" fill="none" stroke="var(--bg)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  if (state === "active") {
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" className={s.pulse} aria-label="berjalan" role="img">
        <circle cx="10" cy="10" r="8.5" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
        <circle cx="10" cy="10" r="4" fill="var(--accent)" />
      </svg>
    );
  }
  if (state === "unavailable") {
    return (
      <svg width="22" height="22" viewBox="0 0 20 20" aria-label="tidak tersedia" role="img">
        <circle cx="10" cy="10" r="8.5" fill="none" stroke="var(--review)" strokeWidth="1.5" />
        <path d="M10 5.5v5.5M10 13.8v.4" stroke="var(--review)" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg width="22" height="22" viewBox="0 0 20 20" aria-label={state === "skipped" ? "tidak ada" : "menunggu"} role="img">
      <circle cx="10" cy="10" r="8.5" fill="none" stroke="var(--line)" strokeWidth="1.5" />
      {state === "skipped" ? <path d="M6 10h8" stroke="var(--dim)" strokeWidth="1.8" strokeLinecap="round" /> : null}
    </svg>
  );
}

export function Banner({ children, error }: { children: React.ReactNode; error?: boolean }) {
  return (
    <div className={`${s.banner} ${error ? s.bannerError : ""}`} role={error ? "alert" : "status"}>
      <span className={s.bannerIcon}>
        <Icon name={error ? "alert" : "info"} />
      </span>
      <div>{children}</div>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className={s.empty}>
      <h3>{title}</h3>
      {children}
    </div>
  );
}

export function TabBar() {
  const path = usePathname() || "/";
  const tabs: { href: string; label: string; icon: IconName; badge?: boolean }[] = [
    { href: "/beranda/", label: "Beranda", icon: "home" },
    { href: "/periksa/", label: "Periksa", icon: "scan" },
    { href: "/consent/", label: "Consent", icon: "inbox", badge: true },
    { href: "/identitas/", label: "Identitas", icon: "shield" },
    { href: "/akun/", label: "Akun", icon: "user" },
  ];
  return (
    <nav className={s.tabbar} aria-label="Navigasi utama">
      {tabs.map((t) => {
        const active = path === t.href || path.startsWith(t.href);
        return (
          <Link key={t.href} href={t.href} className={s.tab} aria-current={active ? "page" : undefined}>
            <Icon name={t.icon} />
            {t.label}
            {t.badge ? <PendingBadge /> : null}
          </Link>
        );
      })}
    </nav>
  );
}

function PendingBadge() {
  const { pendingConsent } = useAuth();
  if (!pendingConsent) return null;
  return (
    <span className={s.badge} aria-label={`${pendingConsent} menunggu jawaban`}>
      {pendingConsent}
    </span>
  );
}

export { s as uiStyles };
