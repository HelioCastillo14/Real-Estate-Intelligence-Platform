import Link from "next/link";

export function Header() {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-background/80 border-b border-border">
      <div className="max-w-[1720px] mx-auto px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <span className="font-display text-primary-foreground text-lg font-semibold leading-none">R</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-xl tracking-tight text-ink font-semibold">REIP</span>
            <span className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground hidden sm:inline">
              Panamá · Intelligence
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm">
          <Link href="/resultados" className="text-muted-foreground hover:text-ink transition-colors">
            Explorar catálogo
          </Link>
          <a href="#metodologia" className="text-muted-foreground hover:text-ink transition-colors">
            Metodología
          </a>
          <a href="#zonas" className="text-muted-foreground hover:text-ink transition-colors">
            Zonas cubiertas
          </a>
        </nav>

        <div className="flex items-center gap-3">
          <span className="hidden lg:flex items-center gap-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            <span className="w-1.5 h-1.5 rounded-full bg-signal-green animate-pulse" />
            Catálogo actualizado
          </span>
        </div>
      </div>
    </header>
  );
}
