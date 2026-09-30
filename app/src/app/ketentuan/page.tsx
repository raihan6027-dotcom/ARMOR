"use client";

import { Markdown } from "@/components/Markdown";
import { Screen } from "@/components/ui";
import { LEGAL } from "@/content/legal";

export default function TermsPage() {
  return (
    <Screen title="Ketentuan layanan" back>
      <Markdown source={LEGAL.terms} />
    </Screen>
  );
}
