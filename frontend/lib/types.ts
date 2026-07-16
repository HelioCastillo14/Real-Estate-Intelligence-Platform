/**
 * Shape real de POST /search/filtros (backend/app/routers/search.py,
 * PropiedadFiltroResponse) — verificado contra la respuesta real del endpoint,
 * no inferido. Reemplaza el tipo Property (32 campos) usado durante la
 * migración inicial desde Lovable: ese tipo modelaba datos que ningún
 * endpoint real expone todavía (imágenes, lat/lng, compatibilidad, semáforo,
 * confiabilidad, segmento, operación venta/alquiler).
 */
export interface PropiedadFiltro {
  id: string; // String(listingId) — para usarlo en rutas de Next.js
  listingId: number;
  corregimiento: string;
  tipoInmueble: string;
  priceUsd: number;
  bedrooms: number | null;
  bathrooms: number | null;
  areaM2: number | null;
  title: string;
  /** null si el anuncio no tiene fotos (1 de 1,177 filas hoy, listing_id=137025) — nunca []. */
  imagenes: string[] | null;
  /** null en 9 filas con descripcion_fuente="ninguna" — no confundir con string vacío. */
  descripcion: string | null;
}

/**
 * Zonas y tipos válidos aceptados por /search/filtros — copiados de
 * backend/app/services/busqueda_estructurada.py (ZONAS_VALIDAS, TIPOS_VALIDOS),
 * no inventados. Si el backend cambia esta lista, este archivo queda
 * desactualizado — no hay endpoint que la exponga para leerla en vivo.
 */
export const ZONAS_VALIDAS = [
  "San Francisco",
  "Bella Vista",
  "Parque Lefevre",
  "Betania",
  "Pedregal",
  "El Cangrejo",
  "Marbella",
  "Obarrio",
  "Costa del Este",
] as const;

export const TIPOS_VALIDOS = ["Apartamento", "Casa", "Edificio", "Local", "Terreno"] as const;

export interface FiltrosBusquedaRequest {
  zona?: string;
  tipo_inmueble?: string;
  precio_min?: number;
  precio_max?: number;
  habitaciones_min?: number;
  banos_min?: number;
  limit?: number;
  offset?: number;
}

interface PropiedadFiltroApi {
  listing_id: number;
  corregimiento: string;
  tipo_inmueble: string;
  price_usd: number;
  bedrooms: number | null;
  bathrooms: number | null;
  area_m2: number | null;
  title: string;
  imagenes: string[] | null;
  descripcion: string | null;
}

export interface FiltrosBusquedaResponseApi {
  total: number;
  limit: number;
  offset: number;
  propiedades: PropiedadFiltroApi[];
}

export function mapPropiedadApi(p: PropiedadFiltroApi): PropiedadFiltro {
  return {
    id: String(p.listing_id),
    listingId: p.listing_id,
    corregimiento: p.corregimiento,
    tipoInmueble: p.tipo_inmueble,
    priceUsd: p.price_usd,
    bedrooms: p.bedrooms,
    bathrooms: p.bathrooms,
    areaM2: p.area_m2,
    title: p.title,
    imagenes: p.imagenes,
    descripcion: p.descripcion,
  };
}

/**
 * Shape real de GET /propiedades/{listing_id} (backend/app/routers/propiedades.py,
 * PropiedadDetalleResponse) — verificado contra la respuesta real del endpoint (3 casos:
 * cobertura completa, cobertura parcial, 404). Superset de PropiedadFiltro: agrega
 * lat/lng, ubicacion_aproximada, y los 3 bloques de valuación (semáforo KNN, segmento
 * KMeans, quality scorer) — cada uno null si el LEFT JOIN no encontró fila, no por
 * ausencia de endpoint.
 */
export interface PropiedadDetalle {
  id: string;
  listingId: number;
  corregimiento: string;
  tipoInmueble: string;
  priceUsd: number;
  bedrooms: number | null;
  bathrooms: number | null;
  areaM2: number | null;
  title: string;
  imagenes: string[] | null;
  descripcion: string | null;
  lat: number | null;
  lng: number | null;
  ubicacionAproximada: boolean;

  /** null si listing_id no tiene fila en valuacion_semaforo_knn (135/1,177 sin cobertura KNN). */
  precioPredicho: number | null;
  categoriaSemaforo: "verde" | "amarillo" | "rojo" | null;
  confianzaReducida: boolean | null;

  /** cluster_id crudo (0/1) — resolver con resolveClusterLabel(), no aquí. null = sin cobertura KNN. */
  clusterId: number | null;

  /** null si listing_id no tiene fila en valuacion_quality_scorer (9/1,177 sin descripción evaluable). */
  completitudInformativa: number | null;
  calidadPresentacion: number | null;
  diferenciadoresAmenidades: number | null;
  transparenciaPrecio: number | null;
}

interface PropiedadDetalleApi {
  listing_id: number;
  corregimiento: string;
  tipo_inmueble: string;
  price_usd: number;
  bedrooms: number | null;
  bathrooms: number | null;
  area_m2: number | null;
  title: string;
  imagenes: string[] | null;
  descripcion: string | null;
  lat: number | null;
  lng: number | null;
  ubicacion_aproximada: boolean;
  precio_predicho: number | null;
  categoria_semaforo: "verde" | "amarillo" | "rojo" | null;
  confianza_reducida: boolean | null;
  cluster_id: number | null;
  completitud_informativa: number | null;
  calidad_presentacion: number | null;
  diferenciadores_amenidades: number | null;
  transparencia_precio: number | null;
}

export function mapPropiedadDetalleApi(p: PropiedadDetalleApi): PropiedadDetalle {
  return {
    id: String(p.listing_id),
    listingId: p.listing_id,
    corregimiento: p.corregimiento,
    tipoInmueble: p.tipo_inmueble,
    priceUsd: p.price_usd,
    bedrooms: p.bedrooms,
    bathrooms: p.bathrooms,
    areaM2: p.area_m2,
    title: p.title,
    imagenes: p.imagenes,
    descripcion: p.descripcion,
    lat: p.lat,
    lng: p.lng,
    ubicacionAproximada: p.ubicacion_aproximada,
    precioPredicho: p.precio_predicho,
    categoriaSemaforo: p.categoria_semaforo,
    confianzaReducida: p.confianza_reducida,
    clusterId: p.cluster_id,
    completitudInformativa: p.completitud_informativa,
    calidadPresentacion: p.calidad_presentacion,
    diferenciadoresAmenidades: p.diferenciadores_amenidades,
    transparenciaPrecio: p.transparencia_precio,
  };
}
