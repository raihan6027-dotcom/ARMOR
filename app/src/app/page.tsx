"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { Icon } from "@/components/Icon";
import s from "@/components/intro.module.css";
import { FaceLines, Logo3D, ScanFrame, ShieldCheck } from "@/components/Logo3D";
import { useAuth } from "@/components/Providers";
import { PrimaryLink, Steps, TextLink } from "@/components/ui";

type Phase = "logo" | "slogan" | "scan" | "done";

const SLOGANS: [string, string][] = [
  ["Protect", "Identity."],
  ["Preserve", "Consent."],
  ["Build", "Trust."],
];
const SCAN_LABELS = ["Mendeteksi wajah", "Mencocokkan wajah terdaftar", "Memeriksa izin pemilik"];
const SEEN_KEY = "armor.introSeen";

function reducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function IntroPage() {
  const { me, ready } = useAuth();
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("logo");
  const [slogan, setSlogan] = useState(0);
  const [step, setStep] = useState(0);
  const timers = useRef<number[]>([]);

  const clear = () => {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  };
  const at = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms));

  const finish = useCallback(() => {
    clear();
    setPhase("done");
    setSlogan(2);
    setStep(4);
    try {
      window.localStorage.setItem(SEEN_KEY, "1");
    } catch {
      /* per-viewer convenience only */
    }
  }, []);

  const start = useCallback(() => {
    clear();
    if (reducedMotion()) return finish();
    setPhase("logo");
    setSlogan(0);
    setStep(0);
    at(2000, () => setPhase("slogan"));
    at(3200, () => setSlogan(1));
    at(4400, () => setSlogan(2));
    at(5650, () => {
      setPhase("scan");
      setStep(0);
    });
    at(6700, () => setStep(1));
    at(7500, () => setStep(2));
    at(8300, () => setStep(3));
    at(8900, () => setStep(4));
    at(10400, finish);
  }, [finish]);

  useEffect(() => {
    let seen = false;
    try {
      seen = window.localStorage.getItem(SEEN_KEY) === "1";
    } catch {
      /* ignore */
    }
    // Returning visitors land on the welcome screen; the intro can be replayed.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (seen) finish();
    else start();
    return clear;
  }, [start, finish]);

  useEffect(() => {
    if (ready && me) router.replace("/beranda/");
  }, [ready, me, router]);

  const verified = step >= 4;

  if (phase === "done") {
    return (
      <main className={s.stage}>
        <section aria-label="Selamat datang di ARMOR" className={s.welcome}>
          <div className={`${s.welcomeTop} ${s.rise}`}>
            <span className={s.welcomeBrand}>ARMOR</span>
            <button type="button" aria-label="Putar ulang intro" onClick={start} className={s.skip} style={{ position: "static", width: 44, padding: 0, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
              <Icon name="replay" size={18} />
            </button>
          </div>
          <div className={s.hero}>
            <Logo3D mode="float" />
            <div aria-hidden="true" className={s.ground} />
          </div>
          <h1 className={s.headline}>
            <span className={s.rise} style={{ animationDelay: "0.1s" }}>Protect Identity.</span>
            <span className={s.rise} style={{ animationDelay: "0.2s" }}>Preserve Consent.</span>
            <span className={s.rise} style={{ animationDelay: "0.3s", color: "var(--accent-soft)" }}>Build Trust.</span>
          </h1>
          <p className={s.rise} style={{ animationDelay: "0.45s", marginTop: 14, color: "var(--muted)" }}>
            ARMOR memeriksa wajah, suara, dan maksud setiap permintaan sebelum AI membuat konten.
          </p>
          <div className={`${s.actions} ${s.rise}`} style={{ animationDelay: "0.6s" }}>
            <PrimaryLink href="/daftar/">Lindungi identitas saya</PrimaryLink>
            <TextLink href="/cara-kerja/">Lihat cara kerja ARMOR</TextLink>
            <TextLink href="/verifikasi/">Periksa apakah gambar dibuat lewat ARMOR</TextLink>
            <p style={{ textAlign: "center", color: "var(--muted)", fontSize: 15 }}>
              Sudah punya akun? <Link href="/masuk/">Masuk</Link>
            </p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className={s.stage}>
      <button type="button" onClick={finish} className={s.skip}>
        Lewati
      </button>

      {phase === "logo" ? (
        <section aria-label="Logo ARMOR" className={s.center}>
          <div className={s.logoWrap}>
            <div aria-hidden="true" className={s.ring} />
            <div aria-hidden="true" className={s.ringLate} />
            <Logo3D mode="spin" />
          </div>
          <div className={`${s.wordmark} ${s.rise}`} style={{ animationDelay: "0.6s" }}>
            ARMOR
          </div>
        </section>
      ) : null}

      {phase === "slogan" ? (
        <section aria-label="Slogan ARMOR" key={slogan} style={{ position: "absolute", inset: 0 }}>
          <div aria-hidden="true" className={s.flash} />
          <p className={s.slogan}>
            <span>{SLOGANS[slogan][0]}</span>
            <span className={s.sloganSoft}>{SLOGANS[slogan][1]}</span>
          </p>
        </section>
      ) : null}

      {phase === "scan" ? (
        <section aria-label="Pemindaian identitas" className={s.scene}>
          <ScanFrame ok={verified}>
            <FaceLines scanning={!verified} />
          </ScanFrame>
          {!verified ? (
            <div className={s.scanSteps}>
              <Steps
                steps={SCAN_LABELS.map((label, i) => ({
                  label,
                  state: step > i ? "done" : step === i ? "active" : "pending",
                }))}
              />
            </div>
          ) : (
            <div className={s.verified} role="status">
              <ShieldCheck />
              <span className={s.verifiedText}>Identitas terlindungi</span>
            </div>
          )}
        </section>
      ) : null}
    </main>
  );
}
