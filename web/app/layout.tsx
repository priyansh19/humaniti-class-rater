import type { Metadata, Viewport } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
import { THEME_SCRIPT } from "@/components/theme";

export const metadata: Metadata = {
  title: "8x8 Class Quality Rater",
  description: "Rates an 8x8 kids' online class recording as Poor, Average, Good or Excellent with specific, timestamped evidence.",
  robots: { index: false },
};
export const viewport: Viewport = {
  width: "device-width", initialScale: 1, viewportFit: "cover",
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#fbfaff" }, { media: "(prefers-color-scheme: dark)", color: "#0b0b16" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} /></head>
      <body className="min-h-screen">
        <SiteHeader />
        <main className="mx-auto max-w-6xl px-3 pb-28 pt-5 sm:px-4 sm:pt-8 md:pb-10">{children}</main>
        <footer className="mx-auto hidden max-w-6xl px-4 pb-10 pt-4 text-xs text-slate-500 md:block">
          Recordings are processed only on the analysis worker and deleted after each job. Only anonymised transcript text and derived numbers are sent to an LLM.
        </footer>
      </body>
    </html>
  );
}
