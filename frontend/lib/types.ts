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
  /** Anuncio público original en inmopanama.com — botón "Contactar anunciante" (Feature 7.2.2). */
  listingUrl: string | null;

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
  listing_url: string | null;
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
    listingUrl: p.listing_url,
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

/**
 * Shape real de POST /search/nlp (backend/app/routers/search.py, SearchNlpResponse) —
 * verificado contra el código real y 5 llamadas en vivo (resultados + los 3 motivo de
 * fallback). tipo="resultados" trae criterios_extraidos + resultados, siempre null el
 * otro; tipo="fallback" trae fallback, siempre null criterios_extraidos/resultados.
 */
export interface SemaforoNlp {
  categoria: "verde" | "amarillo" | "rojo";
  precioPredicho: number;
  residual: number;
  maeReferencia: number;
  confianzaReducida: boolean;
  nComparables: number;
}

export interface CandidatoNlp {
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
  distanciaCoseno: number;
  semaforo: SemaforoNlp | null;
  motivoSinSemaforo: string | null;
}

export interface CriteriosExtraidos {
  zona: string | null;
  tipoInmueble: string | null;
  precioMin: number | null;
  precioMax: number | null;
  habitacionesMin: number | null;
  banosMin: number | null;
  confianza: number;
}

export interface FallbackNlp {
  motivo: "fuera_tema" | "cobertura" | "ambiguedad";
  mensaje: string;
  zonaMencionTexto: string | null;
  confianza: number;
}

export type SearchNlpResultado =
  | {
      tipo: "resultados";
      criteriosExtraidos: CriteriosExtraidos;
      nCandidatos: number;
      candidatos: CandidatoNlp[];
      respuestaFinal: string;
    }
  | { tipo: "fallback"; fallback: FallbackNlp };

interface SemaforoNlpApi {
  categoria: "verde" | "amarillo" | "rojo";
  precio_predicho: number;
  residual: number;
  mae_referencia: number;
  confianza_reducida: boolean;
  n_comparables: number;
}

interface CandidatoNlpApi {
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
  distancia_coseno: number;
  semaforo: SemaforoNlpApi | null;
  motivo_sin_semaforo: string | null;
}

interface SearchNlpResponseApi {
  consulta: string;
  tipo: "resultados" | "fallback";
  criterios_extraidos: {
    zona: string | null;
    tipo_inmueble: string | null;
    precio_min: number | null;
    precio_max: number | null;
    habitaciones_min: number | null;
    banos_min: number | null;
    confianza: number;
  } | null;
  resultados: {
    n_candidatos: number;
    candidatos: CandidatoNlpApi[];
    respuesta_final: string;
  } | null;
  fallback: {
    motivo: "fuera_tema" | "cobertura" | "ambiguedad";
    mensaje: string;
    zona_mencion_texto: string | null;
    confianza: number;
  } | null;
}

function mapCandidatoNlpApi(c: CandidatoNlpApi): CandidatoNlp {
  return {
    id: String(c.listing_id),
    listingId: c.listing_id,
    corregimiento: c.corregimiento,
    tipoInmueble: c.tipo_inmueble,
    priceUsd: c.price_usd,
    bedrooms: c.bedrooms,
    bathrooms: c.bathrooms,
    areaM2: c.area_m2,
    title: c.title,
    imagenes: c.imagenes,
    descripcion: c.descripcion,
    distanciaCoseno: c.distancia_coseno,
    semaforo: c.semaforo
      ? {
          categoria: c.semaforo.categoria,
          precioPredicho: c.semaforo.precio_predicho,
          residual: c.semaforo.residual,
          maeReferencia: c.semaforo.mae_referencia,
          confianzaReducida: c.semaforo.confianza_reducida,
          nComparables: c.semaforo.n_comparables,
        }
      : null,
    motivoSinSemaforo: c.motivo_sin_semaforo,
  };
}

export function mapSearchNlpResponseApi(data: SearchNlpResponseApi): SearchNlpResultado {
  if (data.tipo === "fallback") {
    const f = data.fallback!;
    return {
      tipo: "fallback",
      fallback: {
        motivo: f.motivo,
        mensaje: f.mensaje,
        zonaMencionTexto: f.zona_mencion_texto,
        confianza: f.confianza,
      },
    };
  }

  const ce = data.criterios_extraidos!;
  const r = data.resultados!;
  return {
    tipo: "resultados",
    criteriosExtraidos: {
      zona: ce.zona,
      tipoInmueble: ce.tipo_inmueble,
      precioMin: ce.precio_min,
      precioMax: ce.precio_max,
      habitacionesMin: ce.habitaciones_min,
      banosMin: ce.banos_min,
      confianza: ce.confianza,
    },
    nCandidatos: r.n_candidatos,
    candidatos: r.candidatos.map(mapCandidatoNlpApi),
    respuestaFinal: r.respuesta_final,
  };
}

/**
 * Shape real de GET /valuation/transparencia (backend/app/routers/valuation.py,
 * TransparenciaResponse) — verificado en vivo. `propiedad_id` es literalmente
 * `listing_id` (confirmado contra pipeline/scripts/exportar_conjunto_test_semaforo_knn_3_5_1.py:116,
 * `"propiedad_id": listing_id_test.values` — no es un id distinto), así que sí se puede
 * detectar si una propiedad ya está en el conjunto de test comparando por listingId.
 * precio_real/precio_predicho en USD absoluto — misma escala que price_usd/precio_predicho
 * de GET /propiedades/{id}, verificado cruzando el mismo listing_id entre ambos endpoints
 * (valores idénticos), sin conversión de unidades necesaria.
 */
export interface ParPrediccion {
  propiedadId: number;
  precioReal: number;
  precioPredicho: number;
  diferenciaAbsoluta: number;
  zona: string;
}

export interface TransparenciaData {
  nMuestras: number;
  maeAbsoluto: number;
  maePorcentual: number;
  poblacionMaeAbsoluto: string;
  poblacionMaePorcentual: string;
  pares: ParPrediccion[];
}

interface TransparenciaResponseApi {
  resumen: {
    n_muestras: number;
    mae_absoluto: number;
    mae_porcentual: number;
    poblacion_mae_absoluto: string;
    poblacion_mae_porcentual: string;
  };
  pares: {
    propiedad_id: number;
    precio_real: number;
    precio_predicho: number;
    diferencia_absoluta: number;
    zona: string;
  }[];
}

export function mapTransparenciaApi(data: TransparenciaResponseApi): TransparenciaData {
  return {
    nMuestras: data.resumen.n_muestras,
    maeAbsoluto: data.resumen.mae_absoluto,
    maePorcentual: data.resumen.mae_porcentual,
    poblacionMaeAbsoluto: data.resumen.poblacion_mae_absoluto,
    poblacionMaePorcentual: data.resumen.poblacion_mae_porcentual,
    pares: data.pares.map((p) => ({
      propiedadId: p.propiedad_id,
      precioReal: p.precio_real,
      precioPredicho: p.precio_predicho,
      diferenciaAbsoluta: p.diferencia_absoluta,
      zona: p.zona,
    })),
  };
}

/**
 * Shape real de GET /zone-health/{corregimiento} (backend/app/routers/zone_health.py,
 * ZoneHealthResponse) — verificado en vivo (oficial: Betania; heredado: El Cangrejo;
 * sin composite: Costa del Este) el 2026-07-16, tras el fix de zona_etiquetada_origen.
 * `desglose_dimensiones` tiene 4 claves reales hoy (seguridad, amenidades, transporte,
 * walkability — socioeconómico se eliminó del composite, ver CLAUDE.md), no 6 y no un
 * número fijo asumido: se leen las claves que el objeto trae, no una lista hardcodeada,
 * para no desincronizarse si el backend cambia el desglose.
 */
export interface AmenidadZona {
  id: number;
  categoria: string;
  /** null en 14/238 filas de la tabla real — no asumir siempre presente. */
  nombre: string | null;
  lat: number | null;
  lng: number | null;
  rating: number | null;
}

export interface ZoneHealth {
  corregimiento: string;
  esOficial: boolean;
  heredaDe: string | null;
  /** true si el score/desglose de esta zona es el de heredaDe, no propio. */
  heredado: boolean;

  zoneHealthScore: number | null;
  /** Claves reales tal cual las devuelve el backend — no asumir un set fijo. */
  desgloseDimensiones: Record<string, number> | null;
  estadoZoneHealth: string;
  /** true = sin composite (hoy solo Costa del Este) — distinto de "zona inexistente" (404). */
  coberturaCompositeInsuficiente: boolean;

  noVisualizado: boolean;
  motivoVisualizacion: string | null;

  amenidades: AmenidadZona[];
}

interface AmenidadZonaApi {
  id: number;
  categoria: string;
  nombre: string | null;
  lat: number | null;
  lng: number | null;
  rating: number | null;
}

interface ZoneHealthApi {
  corregimiento: string;
  es_oficial: boolean;
  hereda_de: string | null;
  heredado: boolean;
  zone_health_score: number | null;
  desglose_dimensiones: Record<string, number> | null;
  estado_zone_health: string;
  cobertura_composite_insuficiente: boolean;
  no_visualizado: boolean;
  motivo_visualizacion: string | null;
  amenidades: AmenidadZonaApi[];
}

export function mapZoneHealthApi(z: ZoneHealthApi): ZoneHealth {
  return {
    corregimiento: z.corregimiento,
    esOficial: z.es_oficial,
    heredaDe: z.hereda_de,
    heredado: z.heredado,
    zoneHealthScore: z.zone_health_score,
    desgloseDimensiones: z.desglose_dimensiones,
    estadoZoneHealth: z.estado_zone_health,
    coberturaCompositeInsuficiente: z.cobertura_composite_insuficiente,
    noVisualizado: z.no_visualizado,
    motivoVisualizacion: z.motivo_visualizacion,
    amenidades: z.amenidades.map((a) => ({
      id: a.id,
      categoria: a.categoria,
      nombre: a.nombre,
      lat: a.lat,
      lng: a.lng,
      rating: a.rating,
    })),
  };
}
