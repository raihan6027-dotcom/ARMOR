"use client";

import { useState } from "react";

import { Icon } from "@/components/Icon";
import { Banner, Card, List, PrimaryButton, Row, Screen, Stack } from "@/components/ui";
import { api, call } from "@/lib/api";
import type { components } from "@/lib/api/schema";
import { errorText, formatDate } from "@/lib/messages";

import p from "../periksa/periksa.module.css";
import s from "./verifikasi.module.css";

type Verify = components["schemas"]["VerifyResponse"];

const METHOD: Record<string, string> = {
  METADATA: "Metadata bertanda tangan ARMOR di dalam berkas",
  HASH: "Sidik berkas atau piksel yang sama persis",
  PERCEPTUAL: "Kemiripan visual dengan gambar di registri",
};

const MAX_MB = 8;

function toDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => reject(r.error);
    r.readAsDataURL(file);
  });
}

/** Public: anyone can check an image, no account needed. */
export default function VerifyPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Verify | null>(null);

  function pick(f: File | null) {
    setError(null);
    setResult(null);
    if (preview) URL.revokeObjectURL(preview);
    if (f && f.size > MAX_MB * 1024 * 1024) {
      setFile(null);
      setPreview(null);
      setError(`Berkas terlalu besar. Batasnya ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    setPreview(f ? URL.createObjectURL(f) : null);
  }

  async function check() {
    if (!file) return setError("Pilih gambar dulu.");
    setBusy(true);
    setError(null);
    try {
      setResult((await call(api.POST("/shield/verify", { body: { image: await toDataUrl(file) } }))) as Verify);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen title="Verifikasi gambar" back="/">
      <Stack gap={18}>
        <p style={{ color: "var(--muted)" }}>
          Unggah gambar untuk memeriksa apakah gambar itu dibuat lewat ARMOR, kapan, dan bagaimana status izinnya. Tidak
          perlu akun, dan gambarnya tidak disimpan.
        </p>

        <label className={p.upload}>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="visually-hidden"
            onChange={(e) => pick(e.target.files?.[0] ?? null)}
          />
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Gambar yang akan diperiksa" className={p.preview} />
          ) : (
            <span className={p.uploadEmpty}>
              <Icon name="upload" size={28} />
              Pilih gambar (maks. {MAX_MB} MB)
            </span>
          )}
        </label>

        {error ? <Banner error>{error}</Banner> : null}
        <PrimaryButton onClick={check} disabled={busy}>
          {busy ? "Memeriksa..." : "Periksa keaslian"}
        </PrimaryButton>

        {result ? (
          <section aria-live="polite" aria-labelledby="verify-title">
            <Card>
              <Stack gap={12}>
                <h2 id="verify-title" className={result.verified ? s.ok : s.none}>
                  <Icon name={result.verified ? "shieldCheck" : "info"} size={24} />
                  {result.verified ? "Dibuat lewat ARMOR" : "Tidak ditemukan di ARMOR"}
                </h2>
                <p>{result.message}</p>
                {result.metadata_found && !result.metadata_valid ? (
                  <Banner error>Metadata ARMOR di berkas ini tidak sah. Jangan percayai isi metadatanya.</Banner>
                ) : null}
                {result.verified ? (
                  <List label="Rincian verifikasi">
                    <Row icon="clock" title="Dibuat" sub={formatDate(result.created_at)} />
                    <Row icon="shield" title="Status izin" sub={result.permission_text} />
                    <Row icon="check" title="Dicocokkan lewat" sub={METHOD[result.method]} />
                  </List>
                ) : null}
                {result.verified && result.simulated_generator ? (
                  <p style={{ color: "var(--dim)", fontSize: 14 }}>
                    Gambar ini dibuat oleh generator simulasi pada prototipe ARMOR.
                  </p>
                ) : null}
              </Stack>
            </Card>
          </section>
        ) : null}
      </Stack>
    </Screen>
  );
}
