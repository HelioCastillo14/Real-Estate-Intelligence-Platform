import { NextResponse } from "next/server";
import { getBackendUrl } from "@/lib/backend";

/**
 * Proxy same-origin hacia GET /valuation/transparencia — mismo motivo que los otros
 * proxies de /api/*: FastAPI no tiene CORS configurado. Dataset fijo (209 filas, no
 * cambia entre requests salvo reentrenamiento del modelo) — cacheable agresivamente,
 * a diferencia de /api/search/filtros y /api/search/nlp.
 */
export async function GET() {
  const res = await fetch(`${getBackendUrl()}/valuation/transparencia`, {
    // Dataset fijo del lado del backend (ver transparencia_valuacion.py) — cache de
    // Next.js habilitado, distinto del "no-store" de los proxies de búsqueda.
    next: { revalidate: 3600 },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
