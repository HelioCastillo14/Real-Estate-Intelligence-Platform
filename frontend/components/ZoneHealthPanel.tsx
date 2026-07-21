"use client";

import { useEffect, useState } from "react";
import { obtenerZoneHealth } from "@/lib/zone-health";
import type { ZoneHealth } from "@/lib/types";

/**
 * Feature 5.2.6 — Control de capas Zone Health. El WBS lo describe como "toggles sobre
 * una capa de mapa", pero MapView.tsx no está reconstruido todavía
 * (frontend/docs/pendiente-mapview-signals.md) — esta es la versión sin mapa: un panel
 * con un toggle independiente por dimensión real de `desglose_dimensiones`, que
 * muestra/oculta la barra de esa dimensión. Los toggles NO están hardcodeados a un
 * número fijo (ni 4 ni 6) — se generan a partir de las claves que trae la respuesta real
 * del backend, para no desincronizarse si el desglose cambia.
 */
export function ZoneHealthPanel({ corregimiento }: { corregimiento: string }) {
  const [data, setData] = useState<ZoneHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dimensionesVisibles, setDimensionesVisibles] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    obtenerZoneHealth(corregimiento)
      .then((zh) => {
        if (cancelled) return;
        setData(zh);
        if (zh?.desgloseDimensiones) {
          const todasVisibles = Object.fromEntries(
            Object.keys(zh.desgloseDimensiones).map((k) => [k, true]),
          );
          setDimensionesVisibles(todasVisibles);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Error desconocido");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [corregimiento]);

  if (loading) {
    return (
      <div className="mb-4 rounded-2xl border border-border bg-canvas px-5 py-4 text-xs text-muted-foreground">
        Consultando Zone Health de {corregimiento}…
      </div>
    );
  }

  if (error) {
    return (
      <div className="mb-4 rounded-2xl border border-border bg-canvas px-5 py-4 text-xs text-muted-foreground">
        No se pudo cargar Zone Health de {corregimiento} ({error}).
      </div>
    );
  }

  if (!data) {
    return null; // 404 real — no debería pasar con zonas de ZONAS_VALIDAS, pero no rompe la vista
  }

  return (
    <div className="mb-4 rounded-2xl border border-border bg-card px-5 py-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-primary">
            Zone Health · {data.corregimiento}
          </div>
          {data.heredado && (
            <p className="mt-1 text-xs text-muted-foreground">
              Score heredado de <span className="text-ink">{data.heredaDe}</span> — {data.corregimiento} no es
              corregimiento oficial, no calcula su propio Zone Health.
            </p>
          )}
          {data.noVisualizado && (
            <p className="mt-1 text-xs text-muted-foreground italic">
              Se calcula, pero no forma parte de la visualización activa del mapa
              {data.motivoVisualizacion ? ` — ${data.motivoVisualizacion.split(" -- ")[0]}` : ""}.
            </p>
          )}
        </div>

        {data.zoneHealthScore !== null && (
          <div className="text-right shrink-0">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Score compuesto</div>
            <div className="font-display text-2xl text-ink font-semibold tabular-nums">
              {(data.zoneHealthScore * 100).toFixed(0)}
              <span className="text-sm text-muted-foreground">/100</span>
            </div>
          </div>
        )}
      </div>

      {data.coberturaCompositeInsuficiente || !data.desgloseDimensiones ? (
        <p className="mt-3 text-xs text-muted-foreground">
          Sin score compuesto — datos insuficientes para {data.corregimiento} ({data.estadoZoneHealth}).
        </p>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.keys(data.desgloseDimensiones).map((dim) => (
              <button
                key={dim}
                onClick={() => setDimensionesVisibles((prev) => ({ ...prev, [dim]: !prev[dim] }))}
                className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors capitalize ${
                  dimensionesVisibles[dim]
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-canvas text-muted-foreground border-border"
                }`}
              >
                {dim}
              </button>
            ))}
          </div>

          <div className="mt-4 space-y-2">
            {Object.entries(data.desgloseDimensiones)
              .filter(([dim]) => dimensionesVisibles[dim])
              .map(([dim, valor]) => (
                <div key={dim} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-xs text-muted-foreground capitalize">{dim}</span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-ink"
                      style={{ width: `${Math.max(0, Math.min(1, valor)) * 100}%` }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right text-xs text-ink tabular-nums">
                    {(valor * 100).toFixed(0)}
                  </span>
                </div>
              ))}
          </div>
        </>
      )}

      <p className="mt-4 text-[10px] text-muted-foreground italic">
        Vista de mapa pendiente — mostrando datos en formato lista mientras se reconstruye MapView.
      </p>
    </div>
  );
}
