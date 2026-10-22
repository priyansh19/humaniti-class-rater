import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "8x8 Class Quality Rater",
  description: "Rates an 8x8 kids' online class recording as Poor, Average, Good or Excellent with specific, timestamped evidence.",
  robots: { index: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <SiteHeader />
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 pb-10 pt-4 text-xs text-slate-500">
          Recordings are processed only on the analysis worker and deleted after each job. Only anonymised transcript text and derived numbers are sent to an LLM.
        </footer>
      </body>
    </html>
  );
}
