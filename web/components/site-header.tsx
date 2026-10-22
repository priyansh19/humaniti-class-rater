import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid h-7 w-7 grid-cols-2 overflow-hidden rounded-md ring-1 ring-slate-300" aria-hidden>
            <span className="bg-slate-900" /><span className="bg-white" /><span className="bg-white" /><span className="bg-slate-900" />
          </span>
          Class Quality Rater
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link href="/" className="rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900">Assess</Link>
          <Link href="/about" className="rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900">Method &amp; eval</Link>
          <a href="https://github.com/priyansh19/humaniti-class-rater" className="rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-100 hover:text-slate-900">GitHub</a>
        </nav>
      </div>
    </header>
  );
}
