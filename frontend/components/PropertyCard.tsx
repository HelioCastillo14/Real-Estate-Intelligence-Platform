import Link from "next/link";
import type { PropiedadFiltro } from "@/lib/types";
import { PendingBadge } from "./PendingBadge";

export function PropertyCard({
  property,
  hovered,
  onHover,
}: {
  property: PropiedadFiltro;
  hovered?: boolean;
  onHover?: (id: string | null) => void;
}) {
  const pricePerM2 =
    property.areaM2 && property.areaM2 > 0 ? Math.round(property.priceUsd / property.areaM2) : null;

  return (
    <Link
      href={`/propiedad/${property.id}`}
      onMouseEnter={() => onHover?.(property.id)}
      onMouseLeave={() => onHover?.(null)}
      className={`group block rounded-xl bg-card border transition-all overflow-hidden p-4 ${
        hovered
          ? "border-primary/60 shadow-editorial -translate-y-0.5"
          : "border-border hover:border-primary/30 hover:shadow-soft"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            {property.corregimiento} · {property.tipoInmueble}
          </div>
          <h3 className="font-display text-lg text-ink font-medium leading-tight mt-0.5">
            Propiedad #{property.listingId}
          </h3>
        </div>
        <PendingBadge label="Ficha completa pendiente" />
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div className="font-display text-2xl text-ink font-semibold tabular-nums">
          ${property.priceUsd.toLocaleString()}
        </div>
        {pricePerM2 !== null && (
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground tabular-nums">
            ${pricePerM2.toLocaleString()}/m²
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/60">
        <span className="tabular-nums">
          <span className="text-ink font-medium">{property.areaM2 ?? "—"}</span> m²
        </span>
        <span className="w-1 h-1 rounded-full bg-border" />
        <span className="tabular-nums">
          <span className="text-ink font-medium">{property.bedrooms ?? "—"}</span> rec
        </span>
        <span className="w-1 h-1 rounded-full bg-border" />
        <span className="tabular-nums">
          <span className="text-ink font-medium">{property.bathrooms ?? "—"}</span> baños
        </span>
      </div>
    </Link>
  );
}
