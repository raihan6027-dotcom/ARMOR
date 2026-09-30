"use client";

import { Icon } from "@/components/Icon";
import { RequireAuth } from "@/components/Providers";
import { useToast } from "@/components/Toast";
import { Banner, Screen, Section, Segmented, Stack } from "@/components/ui";
import { raw } from "@/lib/api";
import { errorText, INTENT_LABEL } from "@/lib/messages";
import type { Profile } from "@/lib/types";
import { useLoad } from "@/lib/useLoad";

import s from "./izin.module.css";

type Decision = "ALLOW" | "REVIEW" | "DENY";
interface Permissions {
  identity_id: string;
  permissions: { FACE: Record<string, Decision>; VOICE: Record<string, Decision> };
  locked_intents: string[];
}

const ORDER = [
  "PERSONAL_CREATION",
  "PERSONAL_EDITING",
  "SATIRE_PARODY",
  "COMMERCIAL_USE",
  "POLITICAL_USE",
  "IMPERSONATION",
  "DEFAMATION",
  "SEXUAL_EXPLICIT",
  "DECEPTIVE",
];

const OPTIONS: { value: Decision; label: string }[] = [
  { value: "ALLOW", label: "Izinkan" },
  { value: "REVIEW", label: "Tinjau" },
  { value: "DENY", label: "Tolak" },
];

export default function PermissionsPage() {
  return (
    <RequireAuth>
      <PermissionEditor />
    </RequireAuth>
  );
}

function PermissionEditor() {
  const toast = useToast();
  const { data, error, setData } = useLoad(async () => {
    const profile = await raw<Profile>("/identity/profile");
    return raw<Permissions>(`/permissions?identity_id=${profile.identity_id}`);
  });

  async function change(intent: string, media: "FACE" | "VOICE", decision: Decision) {
    if (!data) return;
    try {
      await raw("/permissions", {
        method: "POST",
        body: JSON.stringify({ identity_id: data.identity_id, intent, media, decision }),
      });
      setData({ ...data, permissions: { ...data.permissions, [media]: { ...data.permissions[media], [intent]: decision } } });
      toast("Izin disimpan");
    } catch (err) {
      toast(errorText(err));
    }
  }

  return (
    <Screen title="Izin per tujuan" back="/identitas/">
      <Stack gap={20}>
        <p style={{ color: "var(--muted)" }}>
          Izinkan: orang lain boleh tanpa bertanya. Tinjau: kamu ditanya dulu lewat kotak consent. Tolak: selalu
          ditolak.
        </p>
        {error ? <Banner error>{errorText(error)}</Banner> : null}
        {data
          ? (["FACE", "VOICE"] as const).map((media) => (
              <Section key={media} title={media === "FACE" ? "Wajah" : "Suara"}>
                <ul className={s.list}>
                  {ORDER.map((intent) => {
                    const locked = data.locked_intents.includes(intent);
                    return (
                      <li key={intent} className={s.item}>
                        <span className={s.name}>
                          {INTENT_LABEL[intent]}
                          {locked ? (
                            <span className={s.locked}>
                              <Icon name="lock" size={16} /> Selalu ditolak
                            </span>
                          ) : null}
                        </span>
                        {locked ? null : (
                          <Segmented
                            label={`${INTENT_LABEL[intent]}, ${media === "FACE" ? "wajah" : "suara"}`}
                            value={data.permissions[media][intent]}
                            options={OPTIONS}
                            onChange={(v) => void change(intent, media, v)}
                          />
                        )}
                      </li>
                    );
                  })}
                </ul>
                {media === "VOICE" ? (
                  <p style={{ color: "var(--dim)", fontSize: 14 }}>
                    Meniru suara orang lain selalu butuh persetujuanmu, walaupun tujuannya diizinkan.
                  </p>
                ) : null}
              </Section>
            ))
          : null}
        <p style={{ color: "var(--dim)", fontSize: 14 }}>
          Peniruan, pencemaran nama, konten seksual, dan penipuan terkunci pada Tolak untuk semua orang, terdaftar atau
          tidak.
        </p>
      </Stack>
    </Screen>
  );
}
