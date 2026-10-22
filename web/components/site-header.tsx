"use client";
import { Activity, BookOpen, History, SlidersHorizontal, Sparkles } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme";
import { cn } from "@/lib/cn";

export const NAV = [
  { href: "/", label: "Assess", short: "Assess", icon: Sparkles },
  { href: "/advanced", label: "Advanced", short: "Advanced", icon: SlidersHorizontal },
  { href: "/history", label: "History", short: "History", icon: History },
  { href: "/about", label: "Method & eval", short: "Method", icon: BookOpen },
  { href: "/status", label: "Status", short: "Status", icon: Activity },
];
export const isActive = (path: string | null, href: string) => (href === "/" ? path === "/" || path === "/report" : !!path?.startsWith(href));

export function SiteHeader() {
  const path = usePathname();
  const adv = path?.startsWith("/advanced") || path?.startsWith("/history");
  return (
    <>
      <header className="sticky top-0 z-30 border-b border-white/60 bg-white/75 backdrop-blur-md">
        <div className="rainbow-bar h-0.5 w-full" />
        <div className="mx-auto flex h-12 max-w-6xl items-center justify-between gap-2 px-3 sm:h-14 sm:px-4">
          <Link href="/" className="tap flex min-w-0 items-center gap-2 font-semibold tracking-tight">
            <span className="grid h-7 w-7 shrink-0 grid-cols-2 overflow-hidden rounded-md shadow ring-1 ring-violet-300" aria-hidden>
              <span className="bg-violet-600" /><span className="bg-amber-300" /><span className="bg-pink-400" /><span className="bg-sky-500" />
            </span>
            <span className="rainbow-text truncate text-[15px] sm:text-base">Class Quality Rater</span>
          </Link>
          <nav className="hidden items-center gap-1 text-sm md:flex" aria-label="Main">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} aria-current={isActive(path, n.href) ? "page" : undefined}
                className={cn("tap rounded-lg px-3 py-1.5 font-medium text-slate-600 hover:bg-violet-50 hover:text-violet-800", isActive(path, n.href) && "bg-violet-100 text-violet-800")}>{n.label}</Link>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-2">
            <span className={cn("hidden rounded-full px-2.5 py-1 text-xs font-semibold text-white lg:inline", adv ? "bg-pink-600" : "bg-violet-600")}>{adv ? "Advanced" : "Brief"}</span>
            <ThemeToggle />
          </div>
        </div>
      </header>
      {/* Mobile bottom tab bar */}
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden">
        <ul className="grid grid-cols-5">
          {NAV.map((n) => {
            const on = isActive(path, n.href); const Icon = n.icon;
            return (
              <li key={n.href}>
                <Link href={n.href} aria-current={on ? "page" : undefined} className={cn("tap flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium", on ? "text-violet-700" : "text-slate-500")}>
                  <span className={cn("grid h-7 w-12 place-items-center rounded-full transition-colors", on && "bg-violet-100")}><Icon className="h-[18px] w-[18px]" /></span>
                  {n.short}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
