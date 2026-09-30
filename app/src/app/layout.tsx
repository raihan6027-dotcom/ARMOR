import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible, Big_Shoulders, Big_Shoulders_Stencil } from "next/font/google";

import { Providers } from "@/components/Providers";

import "./globals.css";

// "Big Shoulders Display" now ships as "Big Shoulders" with an optical-size axis;
// the display look is opsz 72 (set in globals.css).
const display = Big_Shoulders({
  subsets: ["latin"],
  axes: ["opsz"],
  variable: "--font-display",
  display: "swap",
  adjustFontFallback: false,
});
const stencil = Big_Shoulders_Stencil({
  subsets: ["latin"],
  axes: ["opsz"],
  variable: "--font-stencil",
  display: "swap",
  adjustFontFallback: false,
});
const body = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ARMOR",
  description:
    "ARMOR memeriksa wajah, suara, dan maksud setiap permintaan sebelum AI membuat konten.",
  applicationName: "ARMOR",
  appleWebApp: { capable: true, title: "ARMOR", statusBarStyle: "black-translucent" },
  icons: { apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  themeColor: "#06142A",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id" className={`${display.variable} ${stencil.variable} ${body.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
