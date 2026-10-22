"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const NAV = [
  { href: "/", label: "Assess", tone: "hover:bg-violet-100 text-violet-800" },
  { href: "/advanced", label: "Advanced", tone: "hover:bg-pink-100 text-pink-800" },
  { href: "/history", label: "History", tone: "hover:bg-amber-100 text-amber-800" },
  { href: "/about", label: "Method & eval", tone: "hover:bg-emerald-100 text-emerald-800" },
  { href: "/status", label: "Status", tone: "hover:bg-sky-100 text-sky-800" },
];

export function SiteHeader() {
  const path = usePathname();
  const adv = path?.startsWith("/advanced") || path?.startsWith("/history");
  return (
    <header className="sticky top-0 z-20 border-b border-white/60 bg-white/70 backdrop-blur">
      <div className="rainbow-bar h-1 w-full" />
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-7 w-7 grid-cols-2 overflow-hidden rounded-md shadow ring-1 ring-violet-300" aria-hidden>
            <span className="bg-violet-600" /><span className="bg-amber-300" /><span className="bg-pink-400" /><span className="bg-sky-500" />
          </span>
          <span className="rainbow-text">Class Quality Rater</span>
        </Link>
        <nav className="flex flex-wrap items-center gap-1 text-sm">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className={cn("rounded-lg px-3 py-1.5 font-medium", n.tone, path === n.href && "bg-white shadow-sm ring-1 ring-slate-200")}>{n.label}</Link>
          ))}
          <span className={cn("ml-1 hidden rounded-full px-2.5 py-1 text-xs font-semibold sm:inline", adv ? "bg-pink-600 text-white" : "bg-violet-600 text-white")}>
            {adv ? "Advanced mode" : "Brief mode"}
          </span>
        </nav>
      </div>
    </header>
  );
}
