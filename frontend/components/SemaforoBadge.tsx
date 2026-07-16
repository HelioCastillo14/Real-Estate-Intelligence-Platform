const SEMAFORO_CONFIG = {
  verde: { label: "Bajo mercado", dot: "bg-signal-green", bg: "bg-signal-green/10", text: "text-signal-green", border: "border-signal-green/30" },
  amarillo: { label: "Precio justo", dot: "bg-signal-amber", bg: "bg-signal-amber/10", text: "text-signal-amber", border: "border-signal-amber/30" },
  rojo: { label: "Sobre mercado", dot: "bg-signal-red", bg: "bg-signal-red/10", text: "text-signal-red", border: "border-signal-red/30" },
} as const;

export type CategoriaSemaforo = keyof typeof SEMAFORO_CONFIG;

export function SemaforoBadge({ categoria, compact = false }: { categoria: CategoriaSemaforo; compact?: boolean }) {
  const c = SEMAFORO_CONFIG[categoria];
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border ${c.bg} ${c.border} ${
        compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs"
      } font-medium ${c.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      <span>{c.label}</span>
    </div>
  );
}
