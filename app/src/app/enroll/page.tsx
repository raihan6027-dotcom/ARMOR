"use client";

import { useCallback, useRef, useState } from "react";

import { Camera, type CameraHandle, type CameraState, readFiles } from "@/components/Camera";
import cam from "@/components/camera.module.css";
import { FaceLines, ScanFrame, ShieldCheck } from "@/components/Logo3D";
import { RequireAuth } from "@/components/Providers";
import {
  Banner,
  Card,
  Checkbox,
  List,
  PrimaryButton,
  PrimaryLink,
  Row,
  Screen,
  Section,
  Stack,
  TextButton,
  TextLink,
} from "@/components/ui";
import { CONSENT_TEXT } from "@/content/consent";
import { ApiError, api, call } from "@/lib/api";
import { errorText } from "@/lib/messages";

type Step = "consent" | "camera" | "processing" | "done" | "duplicate";

const POSES = [
  { label: "Lihat lurus ke kamera", nose: 0 },
  { label: "Palingkan kepala sedikit ke kiri", nose: -7 },
  { label: "Palingkan kepala sedikit ke kanan", nose: 7 },
];

function PoseHead({ nose }: { nose: number }) {
  return (
    <svg width="40" height="46" viewBox="0 0 40 46" aria-hidden="true" className={cam.poseArrow}>
      <ellipse cx="20" cy="23" rx="15" ry="19" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d={`M${20 + nose} 18 l${nose > 0 ? 3 : nose < 0 ? -3 : 0} 9 h${nose > 0 ? -4 : nose < 0 ? 4 : 3}`} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx={13 + nose} cy="18" r="1.6" fill="currentColor" />
      <circle cx={27 + nose} cy="18" r="1.6" fill="currentColor" />
    </svg>
  );
}

export default function EnrollPage() {
  return (
    <RequireAuth>
      <Enroll />
    </RequireAuth>
  );
}

function Enroll() {
  const text = CONSENT_TEXT.face;
  const [step, setStep] = useState<Step>("consent");
  const [agreed, setAgreed] = useState(false);
  const [shots, setShots] = useState<string[]>([]);
  const [problem, setProblem] = useState<string | null>(null);
  const [camState, setCamState] = useState<CameraState>("starting");
  const [caseId, setCaseId] = useState<string | null>(null);
  const camera = useRef<CameraHandle>(null);
  const onCamState = useCallback((st: CameraState) => setCamState(st), []);

  async function submit(images: string[]) {
    setStep("processing");
    setProblem(null);
    try {
      await call(
        api.POST("/identity/enroll", {
          body: { images, consent: { agreed: true, text_version: text.version } },
        }),
      );
      setStep("done");
    } catch (err) {
      const e = err as ApiError;
      if (e.code === "FACE_ALREADY_REGISTERED") {
        setCaseId((e.details as { case_id?: string } | undefined)?.case_id ?? null);
        setStep("duplicate");
        return;
      }
      const index = (e.details as { capture?: number } | undefined)?.capture;
      setProblem(errorText(err));
      if (typeof index === "number") {
        // Retake only the capture that failed.
        setShots(images.slice(0, index));
      } else {
        setShots([]);
      }
      setStep("camera");
    }
  }

  function capture() {
    const shot = camera.current?.capture();
    if (!shot) return;
    setProblem(null);
    const next = [...shots, shot];
    setShots(next);
    if (next.length === 3) void submit(next);
  }

  async function upload(files: FileList | null) {
    const images = await readFiles(files);
    if (images.length !== 3) {
      setProblem("Pilih tepat tiga foto: lurus, sedikit ke kiri, dan sedikit ke kanan.");
      return;
    }
    await submit(images);
  }

  if (step === "consent") {
    return (
      <Screen title="Daftarkan wajah" back="/beranda/">
        <Stack>
          <h2 style={{ fontSize: 22 }}>{text.title}</h2>
          <p style={{ color: "var(--muted)" }}>{text.intro}</p>
          <List label="Isi persetujuan">
            {text.sections.map((sec) => (
              <Row key={sec.heading} title={sec.heading} sub={sec.text} />
            ))}
          </List>
          <p style={{ color: "var(--muted)" }}>{text.closing}</p>
          <Checkbox checked={agreed} onChange={setAgreed}>
            Saya setuju wajah saya diproses seperti dijelaskan di atas.
          </Checkbox>
          <PrimaryButton disabled={!agreed} onClick={() => setStep("camera")}>
            Lanjut ke kamera
          </PrimaryButton>
          <p style={{ color: "var(--dim)", fontSize: 13, textAlign: "center" }}>Versi teks: {text.version}</p>
        </Stack>
      </Screen>
    );
  }

  if (step === "processing") {
    return (
      <Screen title="Memproses">
        <Stack gap={24}>
          <ScanFrame>
            <FaceLines scanning />
          </ScanFrame>
          <p role="status" style={{ textAlign: "center", color: "var(--muted)" }}>
            Memeriksa kualitas dan mencocokkan tiga foto. Foto tidak disimpan.
          </p>
        </Stack>
      </Screen>
    );
  }

  if (step === "duplicate") {
    return (
      <Screen title="Wajah sudah terdaftar" back="/beranda/">
        <Stack>
          <p>Wajah ini sudah terdaftar atas akun lain, jadi ARMOR tidak membuat pendaftaran kedua.</p>
          <p style={{ color: "var(--muted)" }}>
            Jika ini wajahmu, kamu bisa mengajukan sengketa. Peninjau ARMOR akan memeriksa dan, bila terbukti,
            memindahkan pendaftaran kepadamu atau menghapus pendaftaran yang salah. Selama itu, wajahmu tetap
            dilindungi.
          </p>
          {caseId ? (
            <Banner>Sengketa sudah dibuka otomatis. Nomor kasus: {caseId.slice(0, 8)}.</Banner>
          ) : null}
          <PrimaryLink href="/kasus/">Ajukan sengketa</PrimaryLink>
          <TextLink href="/beranda/">Nanti saja</TextLink>
        </Stack>
      </Screen>
    );
  }

  if (step === "done") {
    return (
      <Screen>
        <Stack gap={24}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, marginTop: 40 }} role="status">
            <ShieldCheck size={56} />
            <h1 style={{ color: "var(--allow)", textAlign: "center", fontSize: 34 }}>Identitas terlindungi</h1>
          </div>
          <Section title="Yang kini dilindungi">
            <List>
              <Row icon="check" title="Wajah" sub="Terdaftar. Foto sudah dihapus, hanya pola terenkripsi yang disimpan." />
              <Row icon="mic" title="Suara" sub="Belum didaftarkan." href="/identitas/" />
              <Row icon="text" title="Nama dan alias" sub="Belum diatur." href="/identitas/" />
            </List>
          </Section>
          <PrimaryLink href="/beranda/">Ke Beranda</PrimaryLink>
        </Stack>
      </Screen>
    );
  }

  const pose = POSES[shots.length] ?? POSES[2];
  const blocked = camState === "denied" || camState === "unavailable";
  return (
    <Screen title="Ambil tiga foto" back="/beranda/">
      <Stack>
        {problem ? <Banner error>{problem}</Banner> : null}
        {blocked ? (
          <Card>
            <Stack gap={10}>
              <strong>{camState === "denied" ? "Izin kamera ditolak" : "Kamera tidak tersedia"}</strong>
              <p style={{ color: "var(--muted)" }}>
                {camState === "denied"
                  ? "Buka pengaturan situs di browser (ikon gembok di bilah alamat), izinkan Kamera, lalu muat ulang halaman."
                  : "Perangkat ini tidak punya kamera yang bisa dipakai. Kamu bisa memilih tiga foto dari galeri."}
              </p>
              <label style={{ fontWeight: 700 }}>
                Pilih 3 foto
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  onChange={(e) => void upload(e.target.files)}
                  style={{ display: "block", marginTop: 8 }}
                />
              </label>
            </Stack>
          </Card>
        ) : (
          <>
            <Camera ref={camera} onState={onCamState} />
            <div className={cam.pose} aria-live="polite">
              <PoseHead nose={pose.nose} />
              {pose.label}
            </div>
            <div className={cam.dots} aria-label={`Foto ${shots.length + 1} dari 3`}>
              {POSES.map((p, i) => (
                <span
                  key={p.label}
                  className={cam.dot}
                  data-state={i < shots.length ? "done" : i === shots.length ? "current" : "pending"}
                />
              ))}
            </div>
            <PrimaryButton onClick={capture} disabled={camState !== "ready"}>
              Ambil foto
            </PrimaryButton>
            {shots.length ? <TextButton onClick={() => setShots([])}>Ulangi dari awal</TextButton> : null}
          </>
        )}
        <p style={{ color: "var(--dim)", fontSize: 14, textAlign: "center" }}>
          Pastikan hanya kamu di dalam bingkai dan wajah cukup terang. Tiga sudut berbeda membuktikan wajah
          asli, bukan foto yang dipegang di depan kamera.
        </p>
      </Stack>
    </Screen>
  );
}
