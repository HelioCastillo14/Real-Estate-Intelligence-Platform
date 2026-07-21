import { getBackendUrl } from "./backend";
import { mapPropiedadDetalleApi } from "./types";
import type { PropiedadDetalle } from "./types";
import { sanitizePii } from "./sanitize-pii";

/**
 * GET /propiedades/{listing_id} (backend/app/routers/propiedades.py) — reemplaza el
 * workaround anterior de paginar /search/filtros buscando el listing_id en memoria
 * (hasta 12 requests para 1,110 filas). Server-side (Server Component), sin caché de
 * Next.js — el detalle debe reflejar el estado real de la DB en cada visita.
 *
 * `descripcion` se sanitiza de PII (Feature 7.2.2) AQUÍ, no en el render de
 * PropertyDetail.tsx: ese componente es "use client", así que cualquier prop que reciba
 * (incluida la `descripcion` cruda) se serializa en el payload de hidratación de
 * Next.js y viaja al navegador en el HTML/RSC aunque el JSX renderizado ya muestre el
 * texto sanitizado — verificado en vivo (listing_id=136553): el teléfono/email
 * aparecían sin redactar en el `<script>` de hidratación pese a que el DOM visible sí
 * mostraba "[contacto de terceros removido]". Sanitizar antes de construir el objeto
 * que cruza el límite servidor→cliente es la única forma real de que el dato crudo no
 * llegue al navegador. La columna en Supabase sigue intacta — este fetch es la única
 * lectura, M2/Quality Scorer consumen la DB directamente, no este objeto.
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
  const property = mapPropiedadDetalleApi(data);
  return { ...property, descripcion: sanitizePii(property.descripcion) };
}
