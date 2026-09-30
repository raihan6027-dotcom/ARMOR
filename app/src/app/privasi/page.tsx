"use client";

import { Markdown } from "@/components/Markdown";
import { Screen } from "@/components/ui";
import { LEGAL } from "@/content/legal";

export default function PrivacyPage() {
  return (
    <Screen title="Kebijakan privasi" back>
      <Markdown source={LEGAL.privacy} />
    </Screen>
  );
}
