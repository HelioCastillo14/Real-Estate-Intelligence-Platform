import { mapTransparenciaApi } from "./types";
import type { TransparenciaData } from "./types";

/**
 * Dataset fijo (209 filas de test, MAE verificado — ver transparencia_valuacion.py). Se
 * cachea en memoria del lado del cliente para no re-fetchear en cada navegación entre
 * Detalles dentro de la misma sesión del navegador — a diferencia de /search/filtros o
 * /propiedades/{id}, este dataset no cambia por propiedad ni por request.
 */
let cachePromise: Promise<TransparenciaData> | null = null;

export function obtenerTransparencia(): Promise<TransparenciaData> {
  if (!cachePromise) {
    cachePromise = fetch("/api/valuation/transparencia")
      .then((res) => {
        if (!res.ok) throw new Error(`/valuation/transparencia respondió ${res.status}`);
        return res.json();
      })
      .then(mapTransparenciaApi)
      .catch((err) => {
        cachePromise = null; // no cachear un fallo — reintentar en la próxima visita
        throw err;
      });
  }
  return cachePromise;
}
