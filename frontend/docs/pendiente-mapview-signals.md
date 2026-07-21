# Pendiente: MapView.tsx y Signals.tsx

Estos dos componentes se borraron de `frontend/components/` durante la migración de
`_lovable-import/` a Next.js (Épica 5) porque, en ese momento, ningún endpoint real
exponía los datos que consumían (`lat`/`lng` para `MapView`; `priceSignal`/compatibilidad
para `Signals`) — dejarlos en el árbol como componentes "vivos" sin ninguna fuente de
datos real habría sido código muerto que aparenta funcionar.

**Nunca se commitearon** — se crearon y se borraron dentro del mismo working tree de la
sesión de migración, sin ningún commit intermedio. `git log` no tiene rastro de ellos en
ninguna ruta (`frontend/components/MapView.tsx`, `frontend/components/Signals.tsx`), así
que no son recuperables vía `git show`/`git checkout`. Este archivo es la única copia que
queda de la última versión funcional de cada uno.

**Última versión funcional: 2026-07-16.**

Reconstruir `MapView.tsx` cuando exista `lat`/`lng` real en la respuesta de
`/search/filtros` (o un endpoint equivalente). Reconstruir `Signals.tsx` cuando haya un
endpoint de semáforo de precio conectado (`GET /valuation/semaforo/{id}` u otro) — la
versión de abajo ya incluye la corrección de paleta (escala de grises, SRS-035: el
`CompatibilityRing` y la barra de confiabilidad usan `var(--ink)`/`bg-ink` en vez de
colorear por valor, porque la única excepción de color permitida en todo el proyecto es
el semáforo de precio, no el score de compatibilidad ni la confiabilidad).

---

## `MapView.tsx`

Usa tiles de OpenFreeMap/Protomaps (`https://tiles.openfreemap.org/styles/liberty`) — no
OSM raster crudo, que era lo que traía el import de Lovable y contradecía la decisión ya
cerrada en CLAUDE.md (tiles gratuitos, sin API key).

```tsx
"use client";

import { useEffect, useRef } from "react";
import maplibregl, { Map as MLMap, Marker } from "maplibre-gl";
import type { Property } from "@/lib/types";

export function MapView({
  properties,
  hoveredId,
  onSelect,
  showZoneHealth = false,
}: {
  properties: Property[];
  hoveredId?: string | null;
  onSelect?: (id: string) => void;
  showZoneHealth?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markersRef = useRef<Record<string, Marker>>({});

  useEffect(() => {
    if (!container.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: container.current,
      // OpenFreeMap/Protomaps: tiles gratuitos, sin API key (decisión cerrada en CLAUDE.md).
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [-79.52, 8.985],
      zoom: 11.5,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      markersRef.current = {};
    };
  }, []);

  // Sync markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};

    properties.forEach((p) => {
      const el = document.createElement("button");
      el.className = "reip-pin";
      el.setAttribute("aria-label", p.title);
      el.dataset.id = p.id;
      el.innerHTML = `<span class="reip-pin__price">$${
        p.operation === "Alquiler"
          ? (p.price / 1000).toFixed(1) + "k"
          : p.price >= 1000 ? Math.round(p.price / 1000) + "k" : p.price
      }</span>`;

      const color =
        p.priceSignal === "under"
          ? "var(--signal-green)"
          : p.priceSignal === "over"
            ? "var(--signal-red)"
            : "var(--signal-amber)";
      el.style.setProperty("--pin-color", color);

      el.addEventListener("click", () => onSelect?.(p.id));

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([p.lng, p.lat])
        .addTo(map);
      markersRef.current[p.id] = marker;
    });
  }, [properties, onSelect]);

  // Sync hover
  useEffect(() => {
    Object.entries(markersRef.current).forEach(([id, m]) => {
      const el = m.getElement();
      el.classList.toggle("reip-pin--active", id === hoveredId);
    });
  }, [hoveredId]);

  return (
    <div className="relative w-full h-full">
      <div ref={container} className="w-full h-full" />
      {showZoneHealth && (
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-tr from-signal-green/25 via-signal-amber/15 to-signal-red/20 mix-blend-multiply" />
      )}
      <div
        title="Por privacidad, los pines representan una posición aproximada dentro del corregimiento, no la dirección exacta del inmueble."
        className="absolute bottom-2 right-2 z-10 pointer-events-auto rounded-full bg-card/95 backdrop-blur border border-border px-2.5 py-1 text-[10px] uppercase tracking-wider text-muted-foreground shadow-soft cursor-help"
      >
        ⓘ Ubicación aproximada por corregimiento
      </div>
      <style>{`
        .reip-pin {
          background: var(--pin-color);
          color: white;
          border: 2px solid oklch(1 0 0);
          border-radius: 999px;
          padding: 4px 10px;
          font-family: var(--font-sans);
          font-size: 11px;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 4px 12px oklch(0.2 0 0 / 0.25);
          transform-origin: center bottom;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
          white-space: nowrap;
        }
        .reip-pin:hover, .reip-pin--active {
          transform: scale(1.15);
          box-shadow: 0 6px 20px oklch(0.2 0 0 / 0.35);
          z-index: 10;
        }
        .reip-pin--active {
          outline: 2px solid var(--color-ink, var(--ink));
          outline-offset: 2px;
        }
      `}</style>
    </div>
  );
}
```

## `Signals.tsx`

```tsx
import type { PriceSignal as Signal } from "@/lib/types";

const configs: Record<Signal, { label: string; dot: string; bg: string; text: string; border: string }> = {
  under: {
    label: "Bajo mercado",
    dot: "bg-signal-green",
    bg: "bg-signal-green/10",
    text: "text-signal-green",
    border: "border-signal-green/30",
  },
  fair: {
    label: "Precio justo",
    dot: "bg-signal-amber",
    bg: "bg-signal-amber/10",
    text: "text-signal-amber",
    border: "border-signal-amber/30",
  },
  over: {
    label: "Sobre mercado",
    dot: "bg-signal-red",
    bg: "bg-signal-red/10",
    text: "text-signal-red",
    border: "border-signal-red/30",
  },
};

export function PriceBadgeUnavailable({ compact = false }: { compact?: boolean }) {
  return (
    <div
      title="El modelo aún no tiene suficientes datos de esta zona o tipo de propiedad para calcular el semáforo de precio."
      className={`inline-flex items-center gap-2 rounded-full border border-border bg-muted text-muted-foreground ${
        compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs"
      } font-medium`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
      <span>Valoración no disponible en esta zona</span>
    </div>
  );
}

export function PriceBadge({
  signal,
  deltaPct,
  compact = false,
}: {
  signal: Signal;
  deltaPct: number;
  compact?: boolean;
}) {
  const c = configs[signal];
  const sign = deltaPct > 0 ? "+" : "";
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border ${c.bg} ${c.border} ${
        compact ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs"
      } font-medium ${c.text}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      <span>{c.label}</span>
      <span className="tabular-nums opacity-70">
        {sign}
        {deltaPct.toFixed(1)}%
      </span>
    </div>
  );
}

export function CompatibilityRing({ value, size = 56 }: { value: number; size?: number }) {
  const stroke = size < 60 ? 4 : 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = (value / 100) * c;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-border)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--ink)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c}`}
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className="font-display text-base font-semibold text-ink tabular-nums">{value}</span>
        <span className="text-[8px] uppercase tracking-wider text-muted-foreground mt-0.5">match</span>
      </div>
    </div>
  );
}
```

**Nota:** ambos archivos, tal como están pegados arriba, importan `Property` y
`PriceSignal` desde `@/lib/types` — ese tipo de 32 campos ya no existe (se reemplazó por
`PropiedadFiltro`, 7 campos, el shape real de `/search/filtros`). Al reconstruirlos habrá
que adaptar los tipos al shape real vigente en ese momento, no copiar-pegar literal.
