"use client";

import { useEffect, useRef, useState } from "react";

import { Icon, type IconName } from "@/components/Icon";
import { RequireAuth } from "@/components/Providers";
import {
  Banner,
  Card,
  Checkbox,
  Field,
  PrimaryButton,
  Screen,
  Section,
  Stack,
  Stamp,
  type StepState,
  Steps,
  SuggestionChip,
  TextButton,
  TextLink,
} from "@/components/ui";
import { ApiError, api, call, raw } from "@/lib/api";
import { errorText, RISK_LABEL } from "@/lib/messages";

import s from "./periksa.module.css";

type Kind = "IMAGE" | "VIDEO" | "AUDIO" | "TEXT_ONLY";
type Phase = "pick" | "write" | "check" | "result";

interface Result {
  request_id: string;
  status: string;
  media_type: string;
  identity: { target: string; people: { source: string; target: string; quality_ok: boolean }[] };
  intent: { label: string; confidence: number; ai_available: boolean };
  risk: { score?: number | null; level?: string | null; ai_available: boolean; top_features?: { feature: string }[] };
  decision: {
    action: "ALLOW" | "REVIEW" | "DENY";
    reason_code: string;
    reason: string;
    suggestion?: string | null;
    label_required: boolean;
  };
  checks_unavailable: string[];
}

const KINDS: { kind: Kind; label: string; icon: IconName; accept?: string; field?: "image" | "video" | "audio"; limitMb?: number }[] = [
  { kind: "IMAGE", label: "Gambar", icon: "image", accept: "image/jpeg,image/png,image/webp", field: "image", limitMb: 8 },
  { kind: "VIDEO", label: "Video", icon: "video", accept: "video/mp4,video/webm,video/quicktime", field: "video", limitMb: 50 },
  { kind: "AUDIO", label: "Audio", icon: "mic", accept: "audio/*", field: "audio", limitMb: 15 },
  { kind: "TEXT_ONLY", label: "Teks saja", icon: "text" },
];

const EXAMPLES: Record<Kind, string[]> = {
  IMAGE: ["Buat karikatur superhero dari foto ini.", "Cerahkan foto saya ini.", "Buat avatar kartun dari wajah saya."],
  VIDEO: ["Buat animasi pendek saya melambaikan tangan.", "Stabilkan video saya yang goyang."],
  AUDIO: ["Pakai suara saya untuk narasi video liburan.", "Kurangi suara bising di rekaman saya."],
  TEXT_ONLY: ["Buat ilustrasi pemandangan gunung saat pagi.", "Buat poster ulang tahun bergaya kartun."],
};

const FACE_STEP: Record<string, string> = { face: "Wajah", face_video: "Wajah", voice: "Suara" };

export default function CheckPage() {
  return (
    <RequireAuth>
      <Check />
    </RequireAuth>
  );
}

function toDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

function Check() {
  const [phase, setPhase] = useState<Phase>("pick");
  const [kind, setKind] = useState<Kind>("IMAGE");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [allowTraining, setAllowTraining] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [tick, setTick] = useState(0);
  const spec = KINDS.find((k) => k.kind === kind)!;

  useEffect(() => () => (preview ? URL.revokeObjectURL(preview) : undefined), [preview]);

  function pickFile(f: File | null) {
    setFileError(null);
    if (!f) return setFile(null);
    if (spec.limitMb && f.size > spec.limitMb * 1024 * 1024) {
      setFile(null);
      setFileError(`Berkas terlalu besar. Batasnya ${spec.limitMb} MB.`);
      return;
    }
    setFile(f);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(f));
  }

  async function run(text = prompt) {
    setError(null);
    setPhase("check");
    setTick(0);
    const timer = window.setInterval(() => setTick((t) => t + 1), 450);
    try {
      const body: Record<string, unknown> = { prompt: text, allow_training: allowTraining };
      if (file && spec.field) body[spec.field] = await toDataUrl(file);
      const res = await call(api.POST("/requests", { body: body as never }));
      // Let the step animation finish its walk before showing the result.
      await new Promise((r) => window.setTimeout(r, 1200));
      setResult(res as unknown as Result);
      setPhase("result");
    } catch (err) {
      setError(errorText(err));
      if ((err as ApiError).code === "FILE_TOO_LARGE") setFileError(errorText(err));
      setPhase("write");
    } finally {
      window.clearInterval(timer);
    }
  }

  function restart(keepPrompt = false) {
    setResult(null);
    if (!keepPrompt) setPrompt("");
    setPhase("write");
  }

  if (phase === "pick") {
    return (
      <Screen title="Periksa" tabs>
        <Stack>
          <p style={{ color: "var(--muted)" }}>Apa yang ingin kamu buat dengan AI? Pilih jenis masukannya.</p>
          <div className={s.kinds} role="radiogroup" aria-label="Jenis masukan">
            {KINDS.map((k) => (
              <button
                key={k.kind}
                type="button"
                role="radio"
                aria-checked={kind === k.kind}
                className={s.kind}
                onClick={() => {
                  setKind(k.kind);
                  setFile(null);
                  setFileError(null);
                  setPhase("write");
                }}
              >
                <Icon name={k.icon} size={28} />
                {k.label}
              </button>
            ))}
          </div>
        </Stack>
      </Screen>
    );
  }

  if (phase === "check") {
    return (
      <Screen title="Memeriksa">
        <CheckSteps kind={kind} tick={tick} />
      </Screen>
    );
  }

  if (phase === "result" && result) {
    return (
      <Screen title="Hasil" tabs>
        <ResultView result={result} kind={kind} onSuggestion={(t) => { setPrompt(t); void run(t); }} onEdit={() => restart(true)} onNew={() => { setFile(null); setPhase("pick"); setResult(null); setPrompt(""); }} />
      </Screen>
    );
  }

  return (
    <Screen title={spec.label} tabs action={<TextButton onClick={() => setPhase("pick")}>Ganti jenis</TextButton>}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!prompt.trim()) return setError("Tulis dulu apa yang ingin dibuat.");
          if (spec.field && !file) return setFileError("Pilih berkas dulu.");
          void run();
        }}
      >
        <Stack>
          {error ? <Banner error>{error}</Banner> : null}
          {spec.field ? (
            <div>
              <label className={s.upload}>
                <input
                  type="file"
                  accept={spec.accept}
                  className="visually-hidden"
                  onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
                />
                {file && preview && kind === "IMAGE" ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={preview} alt="Pratinjau berkas yang dipilih" className={s.preview} />
                ) : file ? (
                  <span className={s.fileName}>
                    <Icon name={spec.icon} /> {file.name}
                  </span>
                ) : (
                  <span className={s.uploadEmpty}>
                    <Icon name="upload" size={28} />
                    Pilih {spec.label.toLowerCase()} (maks. {spec.limitMb} MB)
                  </span>
                )}
              </label>
              {fileError ? (
                <p role="alert" style={{ color: "var(--deny)", marginTop: 6 }}>
                  {fileError}
                </p>
              ) : (
                <p style={{ color: "var(--dim)", fontSize: 14, marginTop: 6 }}>
                  Berkas hanya diperiksa di memori, lalu dibuang.
                </p>
              )}
            </div>
          ) : null}
          <Field
            label="Apa yang ingin dibuat?"
            multiline
            value={prompt}
            maxLength={2000}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Misalnya: buat avatar kartun dari foto saya."
          />
          <Section title="Contoh">
            <div className={s.examples}>
              {EXAMPLES[kind].map((ex) => (
                <SuggestionChip key={ex} onClick={() => setPrompt(ex)}>
                  {ex}
                </SuggestionChip>
              ))}
            </div>
          </Section>
          <Checkbox checked={allowTraining} onChange={setAllowTraining}>
            Izinkan prompt ini dipakai untuk memperbaiki model ARMOR. Hanya teksnya, tidak termasuk berkas.{" "}
            <a href="/ketentuan/">Selengkapnya</a>
          </Checkbox>
          <PrimaryButton type="submit">Periksa dengan ARMOR</PrimaryButton>
        </Stack>
      </form>
    </Screen>
  );
}

function CheckSteps({ kind, tick }: { kind: Kind; tick: number }) {
  const labels = ["Wajah", "Suara", "Nama", "Maksud", "Risiko", "Keputusan"];
  const skip = new Set(
    kind === "IMAGE" ? ["Suara"] : kind === "AUDIO" ? ["Wajah"] : kind === "TEXT_ONLY" ? ["Wajah", "Suara"] : [],
  );
  let n = 0;
  const steps = labels.map((label) => {
    if (skip.has(label)) return { label, state: "skipped" as StepState, note: "tidak ada" };
    const i = n++;
    return { label, state: (tick > i + 1 ? "done" : tick >= i ? "active" : "pending") as StepState };
  });
  return (
    <Stack gap={24}>
      <p style={{ color: "var(--muted)" }}>ARMOR memeriksa permintaanmu sebelum AI membuat apa pun.</p>
      <Steps steps={steps} />
    </Stack>
  );
}

function stepsFromResult(r: Result): { label: string; state: StepState; note?: string }[] {
  const unavailable = new Set(r.checks_unavailable.map((c) => FACE_STEP[c]).filter(Boolean));
  const kind = r.media_type as Kind;
  const faces = r.identity.people.filter((p) => p.source === "FACE");
  const media = (label: string, applies: boolean, detail: string) =>
    unavailable.has(label)
      ? { label, state: "unavailable" as StepState, note: "tidak tersedia" }
      : applies
        ? { label, state: "done" as StepState, note: detail }
        : { label, state: "skipped" as StepState, note: "tidak ada" };
  const faceNote = faces.length
    ? `${faces.length} wajah${faces.some((f) => !f.quality_ok) ? ", ada yang kurang jelas" : ""}`
    : "tidak ada wajah";
  return [
    media("Wajah", kind === "IMAGE" || kind === "VIDEO", faceNote),
    media("Suara", kind === "AUDIO" || kind === "VIDEO", ""),
    { label: "Nama", state: "skipped", note: "tidak ada" },
    { label: "Maksud", state: r.intent.label === "UNCERTAIN" ? "unavailable" : "done", note: r.intent.label === "UNCERTAIN" ? "belum jelas" : undefined },
    { label: "Risiko", state: "done", note: r.risk.level ? RISK_LABEL[r.risk.level] : undefined },
    { label: "Keputusan", state: "done", note: r.decision.action },
  ];
}

function ResultView({
  result,
  kind,
  onSuggestion,
  onEdit,
  onNew,
}: {
  result: Result;
  kind: Kind;
  onSuggestion: (text: string) => void;
  onEdit: () => void;
  onNew: () => void;
}) {
  const [current, setCurrent] = useState(result);
  const d = current.decision;
  const failSafe = d.reason_code === "CHECK_UNAVAILABLE";
  const unclearIntent = d.reason_code === "INTENT_UNCLEAR";
  const blurry = current.identity.people.some((p) => !p.quality_ok);

  return (
    <Stack gap={22}>
      <Stamp status={d.action} />
      <p style={{ textAlign: "center", fontSize: 18 }}>{d.reason}</p>

      {d.action === "ALLOW" ? (
        <Card>
          <Stack gap={10}>
            <span className={s.shieldLabel}>
              <Icon name="shieldCheck" size={18} /> Dibuat dengan AI · ARMOR
            </span>
            <p style={{ color: "var(--muted)" }}>
              Hasil dari generator selalu diberi label ini agar orang lain tahu konten tersebut buatan AI.
            </p>
          </Stack>
        </Card>
      ) : null}

      {d.action === "REVIEW" ? (
        <ReviewActions result={current} failSafe={failSafe} unclear={unclearIntent} blurry={blurry && kind === "IMAGE"} onEdit={onEdit} onUpdate={setCurrent} />
      ) : null}

      {d.action === "DENY" ? (
        <Stack gap={12}>
          {d.suggestion ? (
            <Section title="Coba prompt yang aman">
              <SuggestionChip onClick={() => onSuggestion(d.suggestion!)}>{d.suggestion}</SuggestionChip>
            </Section>
          ) : null}
          <TextLink href={`/banding/?request=${current.request_id}`}>Ajukan banding</TextLink>
        </Stack>
      ) : null}

      <Section title="Hasil pemeriksaan">
        <Steps steps={stepsFromResult(current)} />
      </Section>

      <TextButton onClick={onNew}>Periksa permintaan lain</TextButton>
    </Stack>
  );
}

function ReviewActions({
  result,
  failSafe,
  unclear,
  blurry,
  onEdit,
  onUpdate,
}: {
  result: Result;
  failSafe: boolean;
  unclear: boolean;
  blurry: boolean;
  onEdit: () => void;
  onUpdate: (r: Result) => void;
}) {
  const [asked, setAsked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const poll = useRef<number | null>(null);

  useEffect(() => () => (poll.current ? window.clearInterval(poll.current) : undefined), []);

  async function ask() {
    setBusy(true);
    setError(null);
    try {
      await call(api.POST("/consent/request", { body: { request_id: result.request_id } }));
      setAsked(true);
      poll.current = window.setInterval(async () => {
        try {
          const detail = await raw<{ status: string; decision: Result["decision"] }>(`/requests/${result.request_id}`);
          if (detail.status === "FINAL") {
            if (poll.current) window.clearInterval(poll.current);
            onUpdate({ ...result, status: "FINAL", decision: detail.decision });
          }
        } catch {
          /* keep waiting */
        }
      }, 5000);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (failSafe) {
    return (
      <Banner>
        Salah satu pemeriksaan sedang tidak tersedia. Demi keamanan, permintaan ini ditahan sampai pemeriksaan bisa
        dijalankan lagi. Kamu tidak perlu melakukan apa pun sekarang; coba periksa ulang nanti.
      </Banner>
    );
  }
  return (
    <Stack gap={12}>
      {blurry ? <Banner>Ada wajah yang kurang jelas di gambar. Foto yang lebih terang bisa diperiksa lebih pasti.</Banner> : null}
      {error ? <Banner error>{error}</Banner> : null}
      {unclear ? (
        <>
          <p style={{ color: "var(--muted)" }}>Tambahkan konteks tujuanmu, lalu periksa lagi.</p>
          <PrimaryButton onClick={onEdit}>Tambah konteks</PrimaryButton>
        </>
      ) : result.identity.target !== "OTHER" ? (
        <>
          <p style={{ color: "var(--muted)" }}>
            Permintaan ini ditahan untuk ditinjau. Tambahkan konteks tujuanmu jika ingin memeriksanya lagi.
          </p>
          <PrimaryButton onClick={onEdit}>Tambah konteks</PrimaryButton>
        </>
      ) : asked ? (
        <Card>
          <p role="status" style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <Icon name="clock" /> Menunggu. Kami akan memberi tahu jika statusnya berubah.
          </p>
        </Card>
      ) : (
        <>
          <PrimaryButton onClick={ask} disabled={busy}>
            Minta persetujuan
          </PrimaryButton>
          <TextButton onClick={onEdit}>Tambah konteks dan periksa lagi</TextButton>
        </>
      )}
    </Stack>
  );
}
