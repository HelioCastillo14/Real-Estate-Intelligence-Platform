"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { Header } from "@/components/Header";
import { PropertyCard } from "@/components/PropertyCard";
import { PendingBadge } from "@/components/PendingBadge";
import { ZoneHealthPanel } from "@/components/ZoneHealthPanel";
import {
  ZONAS_VALIDAS,
  TIPOS_VALIDOS,
  mapPropiedadApi,
  mapSearchNlpResponseApi,
} from "@/lib/types";
import type {
  PropiedadFiltro,
  FiltrosBusquedaResponseApi,
  CandidatoNlp,
  FallbackNlp,
  SearchNlpResultado,
} from "@/lib/types";

const searchSchema = z.object({
  q: z.string().catch(""),
  zona: z.string().catch(""),
  tipo: z.string().catch(""),
  rec: z.coerce.number().int().min(0).max(5).catch(0),
  signal: z.enum(["todos", "verde", "amarillo", "rojo"]).catch("todos"),
});

type SearchState = z.infer<typeof searchSchema>;

export function Resultados() {
  const router = useRouter();
  const rawSearchParams = useSearchParams();

  const { q, zona, tipo, rec, signal } = useMemo<SearchState>(
    () =>
      searchSchema.parse({
        q: rawSearchParams.get("q") ?? "",
        zona: rawSearchParams.get("zona") ?? "",
        tipo: rawSearchParams.get("tipo") ?? "",
        rec: rawSearchParams.get("rec") ?? "0",
        signal: rawSearchParams.get("signal") ?? "todos",
      }),
    [rawSearchParams],
  );

  const modoNlp = q.trim().length > 0;
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [queryInput, setQueryInput] = useState(q);

  useEffect(() => setQueryInput(q), [q]);

  const setSearch = (patch: Partial<SearchState>) => {
    const next = { q, zona, tipo, rec, signal, ...patch };
    const params = new URLSearchParams();
    if (next.q) params.set("q", next.q);
    if (next.zona) params.set("zona", next.zona);
    if (next.tipo) params.set("tipo", next.tipo);
    if (next.rec) params.set("rec", String(next.rec));
    if (next.signal !== "todos") params.set("signal", next.signal);
    router.push(`/resultados?${params.toString()}`);
  };

  const submitReformulacion = () => {
    setSearch({ q: queryInput.trim() });
  };

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Header />

      {/* Search bar + filters */}
      <div className="border-b border-border bg-canvas">
        <div className="max-w-[1720px] mx-auto px-8 py-4 flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[240px] max-w-2xl relative">
            <input
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitReformulacion();
              }}
              placeholder="Búsqueda en lenguaje natural — Enter para buscar..."
              className="w-full h-11 pl-11 pr-20 rounded-xl bg-card border border-border text-sm text-ink placeholder:text-muted-foreground focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
              ⌕
            </span>
            {queryInput !== q && (
              <button
                onClick={submitReformulacion}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-primary text-primary-foreground px-3 py-1.5 text-xs font-medium hover:bg-primary/90"
              >
                Buscar
              </button>
            )}
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
          {modoNlp && (
            <FilterSelect
              label="Precio"
              value={signal}
              options={[
                ["todos", "Todos"],
                ["verde", "Bajo mercado"],
                ["amarillo", "Precio justo"],
                ["rojo", "Sobre mercado"],
              ]}
              onChange={(v) => setSearch({ signal: v as SearchState["signal"] })}
            />
          )}
        </div>
      </div>

      {/* Zone Health (5.2.6): se dispara una sola llamada, para la zona seleccionada en
          el filtro "Zona" — no una por cada corregimiento visible en los resultados (hasta
          9 llamadas simultáneas sin mapa donde mostrarlas no tendría dónde aterrizar). Con
          "Todas" no hay una sola zona que resolver, el panel no se renderiza. */}
      {zona && (
        <div className="max-w-[1720px] mx-auto px-8 pt-4">
          <ZoneHealthPanel corregimiento={zona} />
        </div>
      )}

      {modoNlp ? (
        <ResultadosNlp
          consulta={q}
          filtros={{ zona, tipo, rec, signal }}
          hoveredId={hoveredId}
          setHoveredId={setHoveredId}
          onLimpiarFiltros={() => setSearch({ zona: "", tipo: "", rec: 0, signal: "todos" })}
        />
      ) : (
        <ResultadosCatalogo
          filtros={{ zona, tipo, rec }}
          hoveredId={hoveredId}
          setHoveredId={setHoveredId}
          onLimpiarFiltros={() => setSearch({ zona: "", tipo: "", rec: 0 })}
        />
      )}
    </div>
  );
}

function ResultadosCatalogo({
  filtros,
  hoveredId,
  setHoveredId,
  onLimpiarFiltros,
}: {
  filtros: { zona: string; tipo: string; rec: number };
  hoveredId: string | null;
  setHoveredId: (id: string | null) => void;
  onLimpiarFiltros: () => void;
}) {
  const [list, setList] = useState<PropiedadFiltro[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch("/api/search/filtros", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        zona: filtros.zona || undefined,
        tipo_inmueble: filtros.tipo || undefined,
        habitaciones_min: filtros.rec > 0 ? filtros.rec : undefined,
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
  }, [filtros.zona, filtros.tipo, filtros.rec]);

  return (
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
          <EmptyState
            title="Ninguna propiedad cumple estos criterios"
            body="Los filtros que aplicaste no coinciden con propiedades en el catálogo actual. Prueba limpiar filtros o ampliar tu rango."
            onReset={onLimpiarFiltros}
          />
        ) : (
          <div className="space-y-4">
            {list.map((p) => (
              <PropertyCard key={p.id} property={p} hovered={hoveredId === p.id} onHover={setHoveredId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ResultadosNlp({
  consulta,
  filtros,
  hoveredId,
  setHoveredId,
  onLimpiarFiltros,
}: {
  consulta: string;
  filtros: { zona: string; tipo: string; rec: number; signal: string };
  hoveredId: string | null;
  setHoveredId: (id: string | null) => void;
  onLimpiarFiltros: () => void;
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultado, setResultado] = useState<SearchNlpResultado | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setResultado(null);

    fetch("/api/search/nlp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consulta, k: 20 }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`/search/nlp respondió ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        setResultado(mapSearchNlpResponseApi(data));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Error desconocido consultando /search/nlp");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // Solo re-dispara con una consulta nueva — los filtros de abajo son refinamiento
    // local, no deben re-disparar /search/nlp (2.6-4s medido por llamada, 2 golpes a
    // Gemini — inviable como fetch reactivo a cada cambio de filtro).
  }, [consulta]);

  const candidatos: CandidatoNlp[] = useMemo(
    () => (resultado?.tipo === "resultados" ? resultado.candidatos : []),
    [resultado],
  );

  const listFiltrada = useMemo(() => {
    return candidatos.filter((c) => {
      if (filtros.zona && c.corregimiento !== filtros.zona) return false;
      if (filtros.tipo) {
        const plural: Record<string, string> = {
          Apartamento: "Apartamentos",
          Casa: "Casas",
          Edificio: "Edificios",
          Local: "Locales",
          Terreno: "Terrenos",
        };
        if (c.tipoInmueble !== (plural[filtros.tipo] ?? filtros.tipo)) return false;
      }
      if (filtros.rec > 0 && (c.bedrooms ?? 0) < filtros.rec) return false;
      if (filtros.signal !== "todos" && c.semaforo?.categoria !== filtros.signal) return false;
      return true;
    });
  }, [candidatos, filtros]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-24">
        <div className="text-center">
          <span className="inline-block w-4 h-4 rounded-full border-2 border-primary border-t-transparent animate-spin mb-4" />
          <div className="font-display text-xl text-ink">Interpretando tu búsqueda...</div>
          <p className="mt-2 text-sm text-muted-foreground">
            Puede tardar unos segundos — combina extracción de intención (NLP) y evaluación de precio (KNN).
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 max-w-[1200px] w-full mx-auto p-6">
        <ErrorState message={error} />
      </div>
    );
  }

  if (resultado?.tipo === "fallback") {
    return (
      <div className="flex-1 max-w-[1200px] w-full mx-auto p-6">
        <FallbackPanel fallback={resultado.fallback} />
      </div>
    );
  }

  return (
    <div className="flex-1 max-w-[1200px] w-full mx-auto">
      <div className="px-6 py-5 sticky top-0 bg-background/95 backdrop-blur border-b border-border z-10">
        <div>
          <div className="font-display text-2xl text-ink font-medium">
            {listFiltrada.length} {listFiltrada.length === 1 ? "propiedad" : "propiedades"}
          </div>
          <div className="text-xs text-muted-foreground mt-1">
            Interpretado como: <span className="text-ink italic">&quot;{consulta}&quot;</span>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="mb-4">
          <PendingBadge label="Mapa pendiente — /search/nlp no devuelve lat/lng" />
        </div>

        {candidatos.length === 0 ? (
          <EmptyState
            title="No encontramos propiedades para esta búsqueda"
            body="Prueba reformular tu búsqueda arriba con otra zona, tipo de propiedad o presupuesto."
            onReset={onLimpiarFiltros}
            hideReset
          />
        ) : listFiltrada.length === 0 ? (
          <EmptyState
            title="Ningún resultado de tu búsqueda cumple este filtro"
            body="Prueba ajustarlo o reformula tu búsqueda arriba."
            onReset={onLimpiarFiltros}
          />
        ) : (
          <div className="space-y-4">
            {listFiltrada.map((c) => (
              <PropertyCard
                key={c.id}
                property={c}
                hovered={hoveredId === c.id}
                onHover={setHoveredId}
                semaforo={c.semaforo?.categoria ?? null}
                motivoSinSemaforo={c.motivoSinSemaforo}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function FallbackPanel({ fallback }: { fallback: FallbackNlp }) {
  return (
    <div className="p-8 rounded-2xl bg-accent/40 border border-accent">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-primary mb-3">
        <span className="w-1.5 h-1.5 rounded-full bg-primary" />
        Necesito precisar tu búsqueda
      </div>
      <h3 className="font-display text-3xl text-ink font-medium leading-tight">{fallback.mensaje}</h3>
      {fallback.zonaMencionTexto && (
        <p className="mt-3 text-sm text-muted-foreground">
          Zona mencionada: <span className="text-ink italic">{fallback.zonaMencionTexto}</span>
        </p>
      )}
      <p className="mt-4 text-xs text-muted-foreground">
        Edita tu búsqueda en la barra de arriba y presiona Enter para intentar de nuevo.
      </p>
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

function EmptyState({
  title,
  body,
  onReset,
  hideReset = false,
}: {
  title: string;
  body: string;
  onReset: () => void;
  hideReset?: boolean;
}) {
  return (
    <div className="text-center py-16 px-6 border border-dashed border-border rounded-2xl bg-canvas">
      <div className="text-4xl mb-4">◌</div>
      <h3 className="font-display text-2xl text-ink font-medium">{title}</h3>
      <p className="mt-3 text-sm text-muted-foreground max-w-md mx-auto">{body}</p>
      {!hideReset && (
        <button
          onClick={onReset}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-primary text-primary-foreground px-5 py-2.5 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Limpiar filtros
        </button>
      )}
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
