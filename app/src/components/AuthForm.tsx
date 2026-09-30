"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api";
import { errorText } from "@/lib/messages";

import { useAuth } from "./Providers";
import { Banner, Field, PrimaryButton, Screen, Stack } from "./ui";

export function AuthForm({ mode }: { mode: "daftar" | "masuk" }) {
  const { login, register } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const signup = mode === "daftar";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setEmailError(null);
    setPasswordError(null);
    setFormError(null);
    if (!/^\S+@\S+\.\S+$/.test(email)) return setEmailError("Tulis alamat email yang valid.");
    if (password.length < 6) return setPasswordError("Kata sandi minimal 6 karakter.");
    setBusy(true);
    try {
      if (signup) await register(email, password);
      else await login(email, password);
      router.replace(signup ? "/enroll/" : "/beranda/");
    } catch (err) {
      const code = (err as ApiError).code;
      if (code === "EMAIL_TAKEN") setEmailError(errorText(err));
      else if (code === "UNAUTHORIZED") setPasswordError(errorText(err));
      else setFormError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title={signup ? "Daftar" : "Masuk"} back="/">
      <form onSubmit={submit} noValidate>
        <Stack>
          <p style={{ color: "var(--muted)" }}>
            {signup
              ? "Buat akun untuk mendaftarkan wajah dan mengatur siapa yang boleh memakainya."
              : "Masuk untuk melihat identitas, persetujuan, dan pemeriksaanmu."}
          </p>
          {formError ? <Banner error>{formError}</Banner> : null}
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            inputMode="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={emailError}
            required
          />
          <Field
            label="Kata sandi"
            type="password"
            autoComplete={signup ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            error={passwordError}
            hint={signup ? "Minimal 6 karakter." : undefined}
            required
          />
          <PrimaryButton type="submit" disabled={busy}>
            {busy ? "Memproses..." : signup ? "Buat akun" : "Masuk"}
          </PrimaryButton>
          <p style={{ textAlign: "center", color: "var(--muted)" }}>
            {signup ? (
              <>
                Sudah punya akun? <Link href="/masuk/">Masuk</Link>
              </>
            ) : (
              <>
                Belum punya akun? <Link href="/daftar/">Daftar</Link>
              </>
            )}
          </p>
        </Stack>
      </form>
    </Screen>
  );
}
