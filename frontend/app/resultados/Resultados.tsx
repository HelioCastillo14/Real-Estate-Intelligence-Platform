"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { Header } from "@/components/Header";
import { PropertyCard } from "@/components/PropertyCard";
import { PendingBadge } from "@/components/PendingBadge";
import { ZONAS_VALIDAS, TIPOS_VALIDOS, mapPropiedadApi } from "@/lib/types";
import type { PropiedadFiltro, FiltrosBusquedaResponseApi } from "@/lib/types";
import { warnOnce } from "@/lib/warnings";

const searchSchema = z.object({
  q: z.string().catch(""),
  zona: z.string().catch(""),
  tipo: z.string().catch(""),
  rec: z.coerce.number().int().min(0).max(5).catch(0),
});

type SearchState = z.infer<typeof searchSchema>;

export function Resultados() {
  const router = useRouter();
  const rawSearchParams = useSearchParams();

  const { q, zona, tipo, rec } = useMemo<SearchState>(
    () =>
      searchSchema.parse({
        q: rawSearchParams.get("q") ?? "",
        zona: rawSearchParams.get("zona") ?? "",
        tipo: rawSearchParams.get("tipo") ?? "",
        rec: rawSearchParams.get("rec") ?? "0",
      }),
    [rawSearchParams],
  );

  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [list, setList] = useState<PropiedadFiltro[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (q) {
      warnOnce(
        "resultados-q-sin-nlp",
        "El campo de búsqueda libre no filtra resultados — no está conectado a POST /search/nlp todavía, solo los filtros estructurados (zona/tipo/recámaras) llaman al backend real.",
      );
    }
  }, [q]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch("/api/search/filtros", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        zona: zona || undefined,
        tipo_inmueble: tipo || undefined,
        habitaciones_min: rec > 0 ? rec : undefined,
        limit: 20,
        offset: 0,
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`/search/filtros respondió ${res.status}`);
        return res.json() as Promise<FiltrosBusquedaResponseApi>;
      })
      .then((data) => {
        if (cancelled) return;
        setList(data.propiedades.map(mapPropiedadApi));
        setTotal(data.total);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Error desconocido consultando /search/filtros");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [zona, tipo, rec]);

  const setSearch = (patch: Partial<SearchState>) => {
    const next = { q, zona, tipo, rec, ...patch };
    const params = new URLSearchParams();
    if (next.q) params.set("q", next.q);
    if (next.zona) params.set("zona", next.zona);
    if (next.tipo) params.set("tipo", next.tipo);
    if (next.rec) params.set("rec", String(next.rec));
    router.push(`/resultados?${params.toString()}`);
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      {/* Search bar + filters */}
      <div className="border-b border-border bg-canvas">
        <div className="max-w-[1720px] mx-auto px-8 py-4 flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[240px] max-w-2xl relative">
            <input
              value={q}
              onChange={(e) => setSearch({ q: e.target.value })}
              placeholder="Búsqueda en lenguaje natural (aún no filtra resultados)..."
              className="w-full h-11 pl-11 pr-4 rounded-xl bg-card border border-border text-sm text-ink placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
              ⌕
            </span>
          </div>

          <FilterSelect
            label="Zona"
            value={zona}
            options={[["", "Todas"], ...ZONAS_VALIDAS.map((z) => [z, z] as [string, string])]}
            onChange={(v) => setSearch({ zona: v })}
          />
          <FilterSelect
            label="Tipo"
            value={tipo}
            options={[["", "Todos"], ...TIPOS_VALIDOS.map((t) => [t, t] as [string, string])]}
            onChange={(v) => setSearch({ tipo: v })}
          />
          <FilterSelect
            label="Recámaras"
            value={String(rec)}
            options={[
              ["0", "Todas"],
              ["1", "1+"],
              ["2", "2+"],
              ["3", "3+"],
              ["4", "4+"],
            ]}
            onChange={(v) => setSearch({ rec: Number(v) })}
          />
        </div>
      </div>

      {/* Body: list only — sin mapa, no hay lat/lng en /search/filtros */}
      <div className="flex-1 max-w-[1200px] w-full mx-auto">
        <div className="px-6 py-5 sticky top-0 bg-background/95 backdrop-blur border-b border-border z-10">
          <div className="flex items-baseline justify-between">
            <div className="font-display text-2xl text-ink font-medium">
              {loading ? "Cargando…" : `${total ?? list.length} propiedades`}
            </div>
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
              ordenado por precio
            </div>
          </div>
        </div>

        <div className="p-6">
          <div className="mb-4">
            <PendingBadge label="Mapa pendiente — /search/filtros no devuelve lat/lng (geom vacío en la tabla)" />
          </div>

          {error ? (
            <ErrorState message={error} />
          ) : loading ? (
            <div className="text-sm text-muted-foreground">Consultando /search/filtros…</div>
          ) : list.length === 0 ? (
            <EmptyState onReset={() => setSearch({ zona: "", tipo: "", rec: 0 })} />
          ) : (
            <div className="space-y-4">
              {list.map((p) => (
                <PropertyCard key={p.id} property={p} hovered={hoveredId === p.id} onHover={setHoveredId} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className="uppercase tracking-wider">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-lg bg-card border border-border px-3 text-sm text-ink focus:outline-none focus:border-primary"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </label>
  );
}

function EmptyState({ onReset }: { onReset: () => void }) {
  return (
    <div className="text-center py-16 px-6 border border-dashed border-border rounded-2xl bg-canvas">
      <div className="text-4xl mb-4">◌</div>
      <h3 className="font-display text-2xl text-ink font-medium">Ninguna propiedad cumple estos criterios</h3>
      <p className="mt-3 text-sm text-muted-foreground max-w-md mx-auto">
        Los filtros que aplicaste no coinciden con propiedades en el catálogo actual. Prueba
        limpiar filtros o ampliar tu rango.
      </p>
      <button
        onClick={onReset}
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
      >
        Limpiar filtros
      </button>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="text-center py-16 px-6 border border-dashed border-border rounded-2xl bg-canvas">
      <h3 className="font-display text-2xl text-ink font-medium">No se pudo consultar el backend</h3>
      <p className="mt-3 text-sm text-muted-foreground max-w-md mx-auto">{message}</p>
    </div>
  );
}
