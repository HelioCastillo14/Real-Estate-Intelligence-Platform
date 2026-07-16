import { getBackendUrl } from "./backend";
import { mapPropiedadApi } from "./types";
import type { PropiedadFiltro, FiltrosBusquedaResponseApi } from "./types";

const PAGE_SIZE = 100; // máximo que acepta /search/filtros (backend valida limit <= 100)
const MAX_PAGINAS = 20; // cota de seguridad (2,000 filas) independiente de `total`

/**
 * No existe GET /propiedades/{id} ni un filtro por listing_id en
 * /search/filtros — es la única vía real hoy para "obtener una propiedad
 * por id" (decisión explícita, ver Resumen de sesión / traspaso Épica 5).
 * Pagina /search/filtros hasta encontrar el listing_id o agotar el
 * catálogo. Caro (hasta ~12 requests para 1,110 filas), pero real —
 * ningún dato se inventa. Server-side (Server Component) para no bloquear
 * el navegador con la paginación.
 */
export async function buscarPropiedadPorId(listingId: number): Promise<PropiedadFiltro | null> {
  let offset = 0;
  for (let pagina = 0; pagina < MAX_PAGINAS; pagina++) {
    const res = await fetch(`${getBackendUrl()}/search/filtros`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ limit: PAGE_SIZE, offset }),
      cache: "no-store",
    });
    if (!res.ok) {
      throw new Error(`/search/filtros respondió ${res.status} buscando listing_id=${listingId}`);
    }
    const data = (await res.json()) as FiltrosBusquedaResponseApi;
    const match = data.propiedades.find((p) => p.listing_id === listingId);
    if (match) return mapPropiedadApi(match);

    offset += PAGE_SIZE;
    if (offset >= data.total) return null;
  }
  return null;
}
