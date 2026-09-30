import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// Accessibility scan (axe, the same rule engine Lighthouse uses) of every screen,
// including the ones behind sign-in that Lighthouse cannot reach on its own.
const PUBLIC = ["/daftar/", "/masuk/", "/cara-kerja/", "/ketentuan/", "/privasi/", "/verifikasi/"];
const SIGNED_IN = [
  "/beranda/",
  "/periksa/",
  "/consent/",
  "/identitas/",
  "/identitas/izin/",
  "/identitas/lingkaran/",
  "/aktivitas/",
  "/data-saya/",
  "/notifikasi/",
  "/akun/",
  "/kasus/",
  "/enroll/",
];

async function scan(page: import("@playwright/test").Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState("networkidle");
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const problems = result.violations.map((v) => `${path} ${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
  expect(problems).toEqual([]);
}

test("layar publik lolos pemeriksaan aksesibilitas", async ({ page }) => {
  for (const path of PUBLIC) await scan(page, path);
});

test("layar setelah masuk lolos pemeriksaan aksesibilitas", async ({ page }) => {
  await page.goto("/daftar/");
  await page.getByLabel("Email").fill(`e2e-a11y-${Date.now()}@example.com`);
  await page.getByLabel("Kata sandi").fill("rahasia123");
  await page.getByRole("button", { name: "Buat akun" }).click();
  await expect(page).toHaveURL(/enroll/, { timeout: 15_000 });
  for (const path of SIGNED_IN) await scan(page, path);
});
