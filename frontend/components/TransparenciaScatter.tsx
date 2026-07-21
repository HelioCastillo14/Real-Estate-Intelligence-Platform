"use client";

import type { ParPrediccion } from "@/lib/types";

const WIDTH = 600;
const HEIGHT = 380;
const MARGIN = { top: 16, right: 16, bottom: 40, left: 64 };

function formatoCompacto(valor: number): string {
  if (valor >= 1_000_000) return `$${(valor / 1_000_000).toFixed(1)}M`;
  if (valor >= 1_000) return `$${Math.round(valor / 1000)}K`;
  return `$${Math.round(valor)}`;
}

/**
 * Scatter predicho (x) vs. real (y) sobre los 209 pares de test + opcionalmente la
 * propiedad actual como punto destacado. Sin color nuevo — la paleta del proyecto
 * reserva el color exclusivamente para el semáforo de precio (CLAUDE.md §1); la
 * distinción "209 de test" vs. "esta propiedad" es por tamaño + anillo de superficie,
 * no por hue, consistente con esa restricción.
 */
export function TransparenciaScatter({
  pares,
  propiedadActual,
}: {
  pares: ParPrediccion[];
  propiedadActual: { precioReal: number; precioPredicho: number } | null;
}) {
  const todosValores = pares.flatMap((p) => [p.precioReal, p.precioPredicho]);
  if (propiedadActual) todosValores.push(propiedadActual.precioReal, propiedadActual.precioPredicho);

  const min = 0;
  const max = Math.max(...todosValores) * 1.05;

  const escalaX = (v: number) => MARGIN.left + (v / max) * (WIDTH - MARGIN.left - MARGIN.right);
  const escalaY = (v: number) => HEIGHT - MARGIN.bottom - (v / max) * (HEIGHT - MARGIN.top - MARGIN.bottom);

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => max * f);

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="w-full h-auto" role="img" aria-label="Precio predicho vs. precio real, 209 propiedades de test">
        {/* Gridlines — hairline, recesivas */}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={escalaY(t)} y2={escalaY(t)} stroke="var(--border)" strokeWidth={1} />
            <text x={MARGIN.left - 8} y={escalaY(t)} textAnchor="end" dominantBaseline="middle" className="fill-muted-foreground" fontSize={10}>
              {formatoCompacto(t)}
            </text>
            <text x={escalaX(t)} y={HEIGHT - MARGIN.bottom + 16} textAnchor="middle" className="fill-muted-foreground" fontSize={10}>
              {formatoCompacto(t)}
            </text>
          </g>
        ))}

        {/* Línea de referencia y=x (predicción perfecta) */}
        <line
          x1={escalaX(min)}
          y1={escalaY(min)}
          x2={escalaX(max)}
          y2={escalaY(max)}
          stroke="var(--muted-foreground)"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* 209 puntos de test */}
        {pares.map((p) => (
          <circle
            key={p.propiedadId}
            cx={escalaX(p.precioPredicho)}
            cy={escalaY(p.precioReal)}
            r={4}
            fill="var(--muted-foreground)"
            fillOpacity={0.5}
            stroke="var(--card)"
            strokeWidth={2}
          >
            <title>
              {p.zona} · listing_id={p.propiedadId} · real {formatoCompacto(p.precioReal)} · predicho {formatoCompacto(p.precioPredicho)}
            </title>
          </circle>
        ))}

        {/* Propiedad actual — destacada, sin color nuevo (solo tamaño + anillo) */}
        {propiedadActual && (
          <circle
            cx={escalaX(propiedadActual.precioPredicho)}
            cy={escalaY(propiedadActual.precioReal)}
            r={7}
            fill="var(--ink)"
            stroke="var(--card)"
            strokeWidth={3}
          >
            <title>
              Esta propiedad · real {formatoCompacto(propiedadActual.precioReal)} · predicho{" "}
              {formatoCompacto(propiedadActual.precioPredicho)}
            </title>
          </circle>
        )}

        <text x={WIDTH / 2} y={HEIGHT - 4} textAnchor="middle" className="fill-muted-foreground" fontSize={10}>
          Precio predicho por el modelo
        </text>
        <text x={12} y={HEIGHT / 2} textAnchor="middle" className="fill-muted-foreground" fontSize={10} transform={`rotate(-90 12 ${HEIGHT / 2})`}>
          Precio real
        </text>
      </svg>

      {/* Leyenda — siempre presente, 2 series */}
      <div className="flex items-center gap-6 mt-2 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/50" />
          209 propiedades de test
        </span>
        {propiedadActual && (
          <span className="inline-flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-ink" />
            Esta propiedad
          </span>
        )}
        <span className="inline-flex items-center gap-2">
          <span className="w-3 h-px border-t border-dashed border-muted-foreground" />
          Predicción perfecta (y=x)
        </span>
      </div>
    </div>
  );
}
