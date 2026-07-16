"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PendingBadge } from "@/components/PendingBadge";
import type { PropiedadFiltro } from "@/lib/types";
import { warnOnce } from "@/lib/warnings";

export function PropertyDetail({ property }: { property: PropiedadFiltro }) {
  useEffect(() => {
    warnOnce(
      "detalle-solo-filtros",
      "Detalle de propiedad usa únicamente los 7 campos reales de /search/filtros (no hay GET /propiedades/{id}). " +
        "Sin fotos, descripción, lat/lng, compatibilidad (M1), semáforo/segmento (M2) ni confiabilidad — " +
        "GET /valuation/transparencia y los endpoints de semáforo/zone-health por id no están conectados en esta migración.",
    );
  }, []);

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
              Propiedad #{property.listingId}
            </h1>
            <div className="mt-3">
              <PendingBadge label="Título y dirección pendientes — no están en /search/filtros" />
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

        {/* Galería — sin imágenes reales */}
        <div className="mb-10 rounded-2xl border border-dashed border-border bg-canvas aspect-[16/6] flex items-center justify-center">
          <PendingBadge label="Galería de fotos pendiente — sin campo de imágenes en el backend" />
        </div>

        {/* Datos reales */}
        <div className="grid grid-cols-4 gap-4 mb-12">
          <QuickStat label="Área" value={property.areaM2 !== null ? `${property.areaM2}` : "—"} unit="m²" />
          <QuickStat label="Recámaras" value={property.bedrooms !== null ? String(property.bedrooms) : "—"} unit="" />
          <QuickStat label="Baños" value={property.bathrooms !== null ? String(property.bathrooms) : "—"} unit="" />
          <QuickStat label="Tipo" value={property.tipoInmueble} unit="" />
        </div>

        {/* Análisis pendiente — M1/M2/Quality Scorer sin endpoint por id */}
        <div className="grid grid-cols-4 gap-4 mb-12">
          <AnalysisCardPending
            eyebrow="M1 · Preference Matching"
            title="Compatibilidad"
            note="Requiere un perfil de usuario (POST /match/score) — no aplica a una vista de detalle sin contexto de búsqueda."
          />
          <AnalysisCardPending
            eyebrow="M2 · Valuation"
            title="Semáforo de precio"
            note="No existe GET /valuation/semaforo/{id} — solo GET /valuation/transparencia, sin conectar en esta migración."
          />
          <AnalysisCardPending
            eyebrow="M2 · Segmento"
            title="Posición de mercado"
            note="valuacion_segmento_kmeans.cluster_id no se expone por ningún endpoint todavía."
          />
          <AnalysisCardPending
            eyebrow="Quality Scorer"
            title="Confiabilidad del anuncio"
            note="valuacion_quality_scorer no se expone por ningún endpoint todavía."
          />
        </div>

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
          REIP · Datos: catálogo real vía POST /search/filtros (backend)
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
