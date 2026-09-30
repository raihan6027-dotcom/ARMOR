"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { RequireAuth, useAuth } from "@/components/Providers";
import { useToast } from "@/components/Toast";
import { Field, List, PrimaryButton, Row, Screen, Section, Stack, Switch, TextButton } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText } from "@/lib/messages";

export default function AccountPage() {
  return (
    <RequireAuth>
      <Account />
    </RequireAuth>
  );
}

function Account() {
  const { me, refresh, logout } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [name, setName] = useState(me?.display_name ?? "");

  async function update(body: object, done: string) {
    try {
      await raw("/auth/me", { method: "PATCH", body: JSON.stringify(body) });
      await refresh();
      toast(done);
    } catch (err) {
      toast(errorText(err));
    }
  }

  return (
    <Screen title="Akun" tabs>
      <Stack gap={22}>
        <Section title="Profil">
          <p style={{ color: "var(--muted)" }}>{me?.email}</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void update({ display_name: name }, "Profil disimpan");
            }}
          >
            <Stack gap={10}>
              <Field label="Nama tampilan" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
              <PrimaryButton type="submit">Simpan</PrimaryButton>
            </Stack>
          </form>
        </Section>

        <Section title="Pengaturan">
          <List>
            <Row icon="settings" title="Bahasa" sub="Bahasa Indonesia" />
            <Row
              icon="bell"
              title="Notifikasi email"
              sub="Kirim juga lewat email, selain di aplikasi."
              end={
                <Switch
                  label="Notifikasi email"
                  checked={!!me?.email_notifications}
                  onChange={(v) => void update({ email_notifications: v }, v ? "Notifikasi email aktif" : "Notifikasi email mati")}
                />
              }
            />
          </List>
        </Section>

        <Section title="Informasi">
          <List>
            <Row icon="text" title="Ketentuan layanan" href="/ketentuan/" />
            <Row icon="lock" title="Kebijakan privasi" href="/privasi/" />
            <Row icon="info" title="Cara kerja ARMOR" href="/cara-kerja/" />
          </List>
        </Section>

        <TextButton
          danger
          onClick={() => {
            logout();
            router.replace("/");
          }}
        >
          Keluar
        </TextButton>
      </Stack>
    </Screen>
  );
}
