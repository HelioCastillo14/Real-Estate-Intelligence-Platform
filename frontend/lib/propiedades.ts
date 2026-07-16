import { getBackendUrl } from "./backend";
import { mapPropiedadDetalleApi } from "./types";
import type { PropiedadDetalle } from "./types";

/**
 * GET /propiedades/{listing_id} (backend/app/routers/propiedades.py) — reemplaza el
 * workaround anterior de paginar /search/filtros buscando el listing_id en memoria
 * (hasta 12 requests para 1,110 filas). Server-side (Server Component), sin caché de
 * Next.js — el detalle debe reflejar el estado real de la DB en cada visita.
 */
export async function obtenerPropiedadPorId(listingId: number): Promise<PropiedadDetalle | null> {
  const res = await fetch(`${getBackendUrl()}/propiedades/${listingId}`, {
    cache: "no-store",
  });

  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`GET /propiedades/${listingId} respondió ${res.status}`);
  }

  const data = await res.json();
  return mapPropiedadDetalleApi(data);
}
