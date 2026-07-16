"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PendingBadge } from "@/components/PendingBadge";
import type { PropiedadDetalle } from "@/lib/types";
import { warnOnce } from "@/lib/warnings";
import { sanitizeText } from "@/lib/sanitize-text";
import { resolveClusterLabel } from "@/lib/cluster-label";

export function PropertyDetail({ property }: { property: PropiedadDetalle }) {
  const [imgIdx, setImgIdx] = useState(0);

  useEffect(() => {
    if (property.ubicacionAproximada) {
      warnOnce(
        "detalle-ubicacion-aproximada",
        `listing_id=${property.listingId}: geom generado dentro del polígono del corregimiento padre (zona no oficial sin polígono propio), no del polígono real de ${property.corregimiento}.`,
      );
    }
  }, [property.ubicacionAproximada, property.listingId, property.corregimiento]);

  const imagenes = property.imagenes ?? [];
  const pricePerM2 =
    property.areaM2 && property.areaM2 > 0 ? Math.round(property.priceUsd / property.areaM2) : null;

  return (
    <div className="min-h-screen bg-background">
      <Header />

      {/* Breadcrumb */}
      <div className="border-b border-border bg-canvas">
        <div className="max-w-[1400px] mx-auto px-8 py-3 text-xs text-muted-foreground flex items-center gap-2">
          <Link href="/" className="hover:text-ink">Inicio</Link>
          <span>/</span>
          <Link href="/resultados" className="hover:text-ink">Resultados</Link>
          <span>/</span>
          <span className="text-ink">{property.corregimiento}</span>
        </div>
      </div>

      <main className="max-w-[1400px] mx-auto px-8 py-8">
        {/* Header row */}
        <div className="flex items-start justify-between gap-8 mb-8">
          <div className="min-w-0 flex-1">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              {property.tipoInmueble} · {property.corregimiento}
            </div>
            <h1 className="font-display text-4xl md:text-5xl text-ink font-medium leading-tight mt-2">
              {sanitizeText(property.title)}
            </h1>
            <div className="mt-3">
              <PendingBadge label="Dirección exacta pendiente — no está en /search/filtros" />
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="font-display text-4xl text-ink font-semibold tabular-nums">
              ${property.priceUsd.toLocaleString()}
            </div>
            {pricePerM2 !== null && (
              <div className="text-xs text-muted-foreground mt-1 tabular-nums">
                ${pricePerM2.toLocaleString()} / m²
              </div>
            )}
          </div>
        </div>

        {/* Galería */}
        {imagenes.length > 0 ? (
          <div className="grid grid-cols-[1fr_160px] gap-3 mb-10">
            <div className="relative aspect-[16/10] rounded-2xl overflow-hidden bg-muted">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imagenes[imgIdx]}
                alt={sanitizeText(property.title)}
                className="w-full h-full object-cover"
              />
              <div className="absolute bottom-4 right-4 px-3 py-1.5 rounded-full bg-background/90 backdrop-blur text-xs tabular-nums">
                {imgIdx + 1} / {imagenes.length}
              </div>
            </div>
            <div className="grid grid-rows-4 gap-3 overflow-y-auto max-h-[420px]">
              {imagenes.map((img, i) => (
                <button
                  key={img}
                  onClick={() => setImgIdx(i)}
                  className={`relative rounded-xl overflow-hidden bg-muted border-2 transition-all aspect-[4/3] ${
                    imgIdx === i ? "border-primary" : "border-transparent hover:border-border"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={img} alt="" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mb-10 rounded-2xl border border-dashed border-border bg-canvas aspect-[16/6] flex items-center justify-center">
            <span className="text-sm text-muted-foreground">Sin fotos disponibles en el anuncio original</span>
          </div>
        )}

        {/* Datos reales */}
        <div className="grid grid-cols-4 gap-4 mb-12">
          <QuickStat label="Área" value={property.areaM2 !== null ? `${property.areaM2}` : "—"} unit="m²" />
          <QuickStat label="Recámaras" value={property.bedrooms !== null ? String(property.bedrooms) : "—"} unit="" />
          <QuickStat label="Baños" value={property.bathrooms !== null ? String(property.bathrooms) : "—"} unit="" />
          <QuickStat label="Tipo" value={property.tipoInmueble} unit="" />
        </div>

        {/* Análisis */}
        <div className="grid grid-cols-4 gap-4 mb-12">
          <AnalysisCardPending
            eyebrow="M1 · Preference Matching"
            title="Compatibilidad"
            note="Requiere un perfil de usuario (POST /match/score) — no aplica a una vista de detalle sin contexto de búsqueda."
          />

          <AnalysisCard eyebrow="M2 · Valuation" title="Semáforo de precio">
            {property.categoriaSemaforo ? (
              <>
                <div className="mt-3">
                  <SemaforoBadge categoria={property.categoriaSemaforo} />
                </div>
                <div className="mt-3 space-y-1.5 text-xs">
                  <RowKV k="Precio predicho" v={`$${Math.round(property.precioPredicho ?? 0).toLocaleString()}`} />
                  <RowKV k="Confianza" v={property.confianzaReducida ? "Reducida" : "Normal"} />
                </div>
              </>
            ) : (
              <NoDisponible />
            )}
          </AnalysisCard>

          <AnalysisCard eyebrow="M2 · Segmento" title="Posición de mercado">
            {property.clusterId !== null ? (
              <div className="mt-3 font-display text-xl text-ink font-medium">
                {resolveClusterLabel(property.clusterId)}
              </div>
            ) : (
              <NoDisponible />
            )}
          </AnalysisCard>

          <AnalysisCard eyebrow="Quality Scorer" title="Confiabilidad del anuncio">
            {property.completitudInformativa !== null ? (
              <div className="mt-3 space-y-1.5 text-xs">
                <RowKV k="Completitud informativa" v={`${property.completitudInformativa}/5`} />
                <RowKV k="Calidad de presentación" v={`${property.calidadPresentacion}/5`} />
                <RowKV k="Diferenciadores/amenidades" v={`${property.diferenciadoresAmenidades}/5`} />
                <RowKV k="Transparencia de precio" v={`${property.transparenciaPrecio}/5`} />
              </div>
            ) : (
              <NoDisponible />
            )}
          </AnalysisCard>
        </div>

        {/* Descripción original */}
        <section className="mb-12">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-3">
            Descripción original del anuncio
          </div>
          <div className="rounded-2xl border border-border bg-canvas p-6">
            {property.descripcion ? (
              <>
                <p className="text-ink leading-relaxed whitespace-pre-line font-display text-lg">
                  {sanitizeText(property.descripcion)}
                </p>
                <div className="mt-4 text-[11px] text-muted-foreground italic">
                  Texto sin edición — es el insumo del Quality Scorer.
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Sin descripción disponible en el anuncio original.</p>
            )}
          </div>
        </section>

        <div className="rounded-2xl border border-border bg-card p-6 max-w-md">
          <Link
            href="/resultados"
            className="block text-center rounded-xl border border-border bg-canvas px-5 py-3 text-sm text-ink hover:border-primary/50 transition-colors"
          >
            ← Volver a resultados
          </Link>
        </div>
      </main>

      <footer className="border-t border-border bg-canvas mt-16">
        <div className="max-w-[1400px] mx-auto px-8 py-6 text-xs text-muted-foreground">
          REIP · Datos: catálogo real vía GET /propiedades/{"{"}id{"}"} (backend)
        </div>
      </footer>
    </div>
  );
}

function QuickStat({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="border-l-2 border-border pl-3">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="font-display text-2xl text-ink font-semibold tabular-nums">{value}</span>
        {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
      </div>
    </div>
  );
}

function AnalysisCardPending({ eyebrow, title, note }: { eyebrow: string; title: string; note: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 flex flex-col">
      <div className="text-[10px] uppercase tracking-[0.18em] text-primary">{eyebrow}</div>
      <h3 className="mt-1 font-display text-base text-ink font-medium">{title}</h3>
      <div className="mt-3">
        <PendingBadge />
      </div>
      <p className="mt-3 text-xs text-muted-foreground leading-relaxed">{note}</p>
    </div>
  );
}

function AnalysisCard({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 flex flex-col">
      <div className="text-[10px] uppercase tracking-[0.18em] text-primary">{eyebrow}</div>
      <h3 className="mt-1 font-display text-base text-ink font-medium">{title}</h3>
      <div className="flex-1">{children}</div>
    </div>
  );
}

/**
 * "No disponible para esta propiedad" — deliberadamente distinto del PendingBadge de
 * "endpoint pendiente" que se usaba antes: GET /propiedades/{id} ya existe, esto es
 * ausencia real de cobertura de modelo para este listing_id puntual (LEFT JOIN sin
 * fila), no un hueco de backend.
 */
function NoDisponible() {
  return (
    <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-border bg-muted text-muted-foreground px-3 py-1.5 text-xs font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
      No disponible para esta propiedad
    </div>
  );
}

function RowKV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between border-b border-border/60 pb-1.5 last:border-b-0">
      <span className="text-muted-foreground">{k}</span>
      <span className="text-ink font-medium tabular-nums">{v}</span>
    </div>
  );
}

const SEMAFORO_CONFIG = {
  verde: { label: "Bajo mercado", dot: "bg-signal-green", bg: "bg-signal-green/10", text: "text-signal-green", border: "border-signal-green/30" },
  amarillo: { label: "Precio justo", dot: "bg-signal-amber", bg: "bg-signal-amber/10", text: "text-signal-amber", border: "border-signal-amber/30" },
  rojo: { label: "Sobre mercado", dot: "bg-signal-red", bg: "bg-signal-red/10", text: "text-signal-red", border: "border-signal-red/30" },
} as const;

function SemaforoBadge({ categoria }: { categoria: "verde" | "amarillo" | "rojo" }) {
  const c = SEMAFORO_CONFIG[categoria];
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border ${c.bg} ${c.border} px-3 py-1.5 text-xs font-medium ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      <span>{c.label}</span>
    </div>
  );
}
