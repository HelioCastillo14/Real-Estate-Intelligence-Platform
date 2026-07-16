import { mapZoneHealthApi } from "./types";
import type { ZoneHealth } from "./types";

/**
 * GET /zone-health/{corregimiento} vía el proxy de /api — cacheado en memoria por
 * corregimiento (9 zonas fijas, no cambia entre requests dentro de la sesión del
 * navegador, igual criterio que obtenerTransparencia()). null si la zona no existe en
 * absoluto (404, p.ej. zona_no_determinada) — distinto de coberturaCompositeInsuficiente
 * (200 real, zona real sin score, hoy solo Costa del Este).
 */
const cache = new Map<string, Promise<ZoneHealth | null>>();

export function obtenerZoneHealth(corregimiento: string): Promise<ZoneHealth | null> {
  let promise = cache.get(corregimiento);
  if (!promise) {
    promise = fetch(`/api/zone-health/${encodeURIComponent(corregimiento)}`)
      .then(async (res) => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`/zone-health/${corregimiento} respondió ${res.status}`);
        return mapZoneHealthApi(await res.json());
      })
      .catch((err) => {
        cache.delete(corregimiento); // no cachear un fallo — reintentar en la próxima visita
        throw err;
      });
    cache.set(corregimiento, promise);
  }
  return promise;
}
