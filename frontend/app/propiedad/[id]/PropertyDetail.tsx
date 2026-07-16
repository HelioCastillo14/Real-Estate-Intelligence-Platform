"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { PendingBadge } from "@/components/PendingBadge";
import { SemaforoBadge } from "@/components/SemaforoBadge";
import { TransparenciaScatter } from "@/components/TransparenciaScatter";
import type { PropiedadDetalle, TransparenciaData, ZoneHealth, AmenidadZona } from "@/lib/types";
import { warnOnce } from "@/lib/warnings";
import { sanitizeText } from "@/lib/sanitize-text";
import { resolveClusterLabel } from "@/lib/cluster-label";
import { obtenerTransparencia } from "@/lib/transparencia";
import { obtenerZoneHealth } from "@/lib/zone-health";

export function PropertyDetail({ property }: { property: PropiedadDetalle }) {
  const [imgIdx, setImgIdx] = useState(0);
  const [transparencia, setTransparencia] = useState<TransparenciaData | null>(null);
  const [transparenciaError, setTransparenciaError] = useState<string | null>(null);
  const [zoneHealth, setZoneHealth] = useState<ZoneHealth | null>(null);
  const [zoneHealthLoading, setZoneHealthLoading] = useState(true);
  const [zoneHealthError, setZoneHealthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    obtenerTransparencia()
      .then((data) => {
        if (!cancelled) setTransparencia(data);
      })
      .catch((err) => {
        if (!cancelled) setTransparenciaError(err instanceof Error ? err.message : "Error desconocido");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setZoneHealthLoading(true);
    setZoneHealthError(null);
    obtenerZoneHealth(property.corregimiento)
      .then((zh) => {
        if (!cancelled) setZoneHealth(zh);
      })
      .catch((err) => {
        if (!cancelled) setZoneHealthError(err instanceof Error ? err.message : "Error desconocido");
      })
      .finally(() => {
        if (!cancelled) setZoneHealthLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [property.corregimiento]);

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

        {/* Transparencia del modelo (5.3.5) */}
        <section className="mb-12">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-3">
            M2 · Transparencia — Cómo se calculó el precio
          </div>
          <div className="rounded-2xl border border-border bg-card p-6">
            {transparenciaError ? (
              <p className="text-sm text-muted-foreground">
                No se pudo cargar el conjunto de transparencia ({transparenciaError}).
              </p>
            ) : !transparencia ? (
              <p className="text-sm text-muted-foreground">Cargando conjunto de transparencia…</p>
            ) : (
              <div className="grid grid-cols-[1fr_220px] gap-8">
                <div>
                  <TransparenciaScatter
                    pares={transparencia.pares}
                    propiedadActual={
                      property.precioPredicho !== null
                        ? { precioReal: property.priceUsd, precioPredicho: property.precioPredicho }
                        : null
                    }
                  />
                  {property.precioPredicho === null && (
                    <p className="mt-3 text-xs text-muted-foreground italic">
                      Esta propiedad no tiene predicción de precio disponible — se muestra el desempeño
                      general del modelo sobre las {transparencia.nMuestras} propiedades de test.
                    </p>
                  )}
                </div>
                <div className="space-y-4">
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">MAE</div>
                    <div className="font-display text-2xl text-ink font-semibold tabular-nums">
                      ${Math.round(transparencia.maeAbsoluto).toLocaleString()}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1 tabular-nums">
                      {transparencia.maePorcentual.toFixed(1)}% del precio promedio del catálogo
                    </div>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    {transparencia.poblacionMaeAbsoluto}
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Servicios cercanos (5.3.6) */}
        <section className="mb-12">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-3">
            Servicios cercanos — {property.corregimiento}
          </div>
          <div className="rounded-2xl border border-border bg-card p-6">
            {zoneHealthLoading ? (
              <p className="text-sm text-muted-foreground">Consultando amenidades de {property.corregimiento}…</p>
            ) : zoneHealthError ? (
              <p className="text-sm text-muted-foreground">
                No se pudo cargar Zone Health ({zoneHealthError}).
              </p>
            ) : zoneHealth === null ? (
              <NoDisponible label="No disponible para esta propiedad — zona sin cobertura de Zone Health" />
            ) : zoneHealth.amenidades.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Sin amenidades registradas para {property.corregimiento}.
              </p>
            ) : (
              <>
                {zoneHealth.heredado && (
                  <p className="mb-4 text-xs text-muted-foreground">
                    Servicios de <span className="text-ink">{zoneHealth.heredaDe}</span> — {property.corregimiento}{" "}
                    no tiene amenidades propias catalogadas, hereda las de su zona contenedora.
                  </p>
                )}
                <AmenidadesPorCategoria amenidades={zoneHealth.amenidades} />
                <p className="mt-4 text-[10px] text-muted-foreground italic">
                  Vista de mapa pendiente — mostrando datos en formato lista mientras se reconstruye MapView.
                </p>
              </>
            )}
          </div>
        </section>

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
function NoDisponible({ label = "No disponible para esta propiedad" }: { label?: string }) {
  return (
    <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-border bg-muted text-muted-foreground px-3 py-1.5 text-xs font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
      {label}
    </div>
  );
}

/**
 * Feature 5.3.6 — agrupa amenidades reales por categoría (6 posibles: parque, colegio,
 * farmacia, supermercado, clinica, hospital). Sin mapa (MapView.tsx pendiente,
 * frontend/docs/pendiente-mapview-signals.md), así que es una lista categorizada, no
 * pines — el Done del WBS pide "al menos 3 categorías visibles", que esta vista cumple
 * mostrando todas las categorías reales presentes, no un subconjunto fijo.
 */
function AmenidadesPorCategoria({ amenidades }: { amenidades: AmenidadZona[] }) {
  const porCategoria = new Map<string, AmenidadZona[]>();
  for (const a of amenidades) {
    const lista = porCategoria.get(a.categoria) ?? [];
    lista.push(a);
    porCategoria.set(a.categoria, lista);
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Array.from(porCategoria.entries()).map(([categoria, lista]) => (
        <div key={categoria} className="border-l-2 border-border pl-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {categoria} <span className="tabular-nums">({lista.length})</span>
          </div>
          <ul className="mt-1.5 space-y-1">
            {lista.slice(0, 5).map((a) => (
              <li key={a.id} className="text-xs text-ink truncate">
                {a.nombre ?? "Sin nombre registrado"}
                {a.rating !== null && (
                  <span className="text-muted-foreground tabular-nums"> · {a.rating.toFixed(1)}★</span>
                )}
              </li>
            ))}
            {lista.length > 5 && (
              <li className="text-[11px] text-muted-foreground">+{lista.length - 5} más</li>
            )}
          </ul>
        </div>
      ))}
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

