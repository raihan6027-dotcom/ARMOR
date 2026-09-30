import { expect, test } from "@playwright/test";

// A tiny valid PNG; the backend's FAKE face engine treats any decodable image as
// one clear face of the enrolled test person (development only).
const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AAIU" +
    "EQE8AAAXBgFB0KFeXAAAAABJRU5ErkJggg==",
  "base64",
);

test("intro -> daftar -> enroll (kamera palsu) -> periksa -> hasil", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  // Intro: skip to the welcome screen.
  await page.goto("/");
  await page.getByRole("button", { name: "Lewati" }).click();
  await expect(page.getByRole("heading", { name: /Protect Identity/ })).toBeVisible();

  // Sign up.
  await page.getByRole("link", { name: "Lindungi identitas saya" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Kata sandi").fill("rahasia123");
  await page.getByRole("button", { name: "Buat akun" }).click();

  // Enrollment: consent first, the button stays disabled until checked.
  await expect(page.getByRole("heading", { name: "Persetujuan pemrosesan wajah" })).toBeVisible({ timeout: 15_000 });
  const next = page.getByRole("button", { name: "Lanjut ke kamera" });
  await expect(next).toBeDisabled();
  await page.getByRole("checkbox").check();
  await next.click();

  // Three captures from Chromium's fake camera.
  const shoot = page.getByRole("button", { name: "Ambil foto" });
  await expect(shoot).toBeEnabled({ timeout: 15_000 });
  await expect(page.getByText("Lihat lurus ke kamera")).toBeVisible();
  await shoot.click();
  await expect(page.getByText("Palingkan kepala sedikit ke kiri")).toBeVisible();
  await shoot.click();
  await expect(page.getByText("Palingkan kepala sedikit ke kanan")).toBeVisible();
  await shoot.click();
  await expect(page.getByRole("heading", { name: "Identitas terlindungi" })).toBeVisible({ timeout: 20_000 });

  // Home shows the face as protected.
  await page.getByRole("link", { name: "Ke Beranda" }).click();
  await expect(page.getByText("Terlindungi")).toBeVisible();

  // Check a request with an image of oneself.
  await page.getByRole("link", { name: "Periksa", exact: true }).click();
  await page.getByRole("radio", { name: "Gambar" }).click();
  await page.locator('input[type="file"]').setInputFiles({ name: "foto.png", mimeType: "image/png", buffer: PNG });
  await page.getByLabel("Apa yang ingin dibuat?").fill("Buatkan avatar kartun dari wajah saya.");
  await page.getByRole("button", { name: "Periksa dengan ARMOR" }).click();

  await expect(page.getByRole("heading", { name: "Memeriksa" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "ALLOW" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Dibuat dengan AI · ARMOR")).toBeVisible();
});

test("periksa teks berbahaya tanpa orang menghasilkan keputusan dengan alasan", async ({ page }) => {
  const email = `e2e-text-${Date.now()}@example.com`;
  await page.goto("/daftar/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Kata sandi").fill("rahasia123");
  await page.getByRole("button", { name: "Buat akun" }).click();
  await expect(page).toHaveURL(/enroll/, { timeout: 15_000 });

  await page.goto("/periksa/");
  await page.getByRole("radio", { name: "Teks saja" }).click();
  await page.getByLabel("Apa yang ingin dibuat?").fill("Buat ilustrasi pemandangan gunung saat pagi.");
  await page.getByRole("button", { name: "Periksa dengan ARMOR" }).click();
  await expect(page.getByRole("status").filter({ hasText: /ALLOW|REVIEW|DENY/ })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "Hasil pemeriksaan" })).toBeVisible();
});
