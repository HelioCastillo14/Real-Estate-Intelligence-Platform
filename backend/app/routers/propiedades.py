"""Router `/propiedades` — `GET /propiedades/{listing_id}`, primera vez que se sirve una
propiedad individual completa (Épica 5, paso 2 del plan de dependencias de la sesión).

Router nuevo, no una extensión de `search.py` o `valuation.py` — decisión explícita:
`search.py` sirve listas/consultas (`/search/filtros`, `/search/nlp`), nunca un recurso
individual; `valuation.py` sirve un dataset agregado fijo (209 pares de test), no algo
indexado por `listing_id`. Este endpoint es la primera vez que el backend expone "una
propiedad, completa" como recurso propio — merece su propio router en vez de forzarlo
dentro de uno cuya responsabilidad ya está definida y es distinta.

Una sola query con 4 `LEFT JOIN` (no 4 queries separadas): `propiedades` es la tabla base
(siempre existe si el `listing_id` es válido), las otras 3 son opcionales por diseño —
`valuacion_semaforo_knn`/`valuacion_segmento_kmeans` no cubren las 135 propiedades sin
comparables suficientes en el KNN (1,177 - 1,042), `valuacion_quality_scorer` no cubre 9
propiedades sin descripción evaluable (1,177 - 1,168). Un `LEFT JOIN` deja esos campos en
`NULL` de forma natural — no hace falta lógica condicional en Python para decidir si la
propiedad "tiene" o "no tiene" cada pieza, la ausencia de fila ya lo expresa.

`lat`/`lng` vía `ST_X(geom)`/`ST_Y(geom)` — `NULL` si `geom` es `NULL` (244 propiedades sin
`geom`: Costa del Este sin polígono en OSM + zona_no_determinada, ver CLAUDE.md). PostGIS
devuelve `NULL` de estas funciones sobre geometría `NULL` sin lanzar error, no hace falta
un `CASE WHEN` explícito.

`cluster_id` se devuelve como entero crudo (0/1), sin resolver a texto — el mapeo
"Compacto/económico" / "Grande/premium" ya vive en el frontend
(`frontend/lib/cluster-label.ts`, `resolveClusterLabel()`), consistente con la decisión de
schema ya cerrada (`Feature_3_2_4_Etiquetado_Clusters_KMeans_Acta_Excepcion.md`): el texto
no se persiste en `valuacion_segmento_kmeans`, tampoco tiene sentido resolverlo aquí — sería
duplicar la misma decisión en dos lugares.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.pool import obtener_pool

router = APIRouter(prefix="/propiedades", tags=["propiedades"])


class PropiedadDetalleResponse(BaseModel):
    listing_id: int
    corregimiento: str
    tipo_inmueble: str
    price_usd: int
    bedrooms: int | None
    bathrooms: int | None
    area_m2: float | None
    title: str
    imagenes: list[str] | None
    descripcion: str | None
    lat: float | None
    lng: float | None
    ubicacion_aproximada: bool

    # valuacion_semaforo_knn — NULL si la propiedad no tiene cobertura KNN (135/1,177)
    precio_predicho: float | None
    categoria_semaforo: str | None
    confianza_reducida: bool | None

    # valuacion_segmento_kmeans — NULL si no tiene cobertura KNN (mismo pool que semáforo)
    cluster_id: int | None

    # valuacion_quality_scorer — NULL si no tiene descripción evaluable (9/1,177)
    completitud_informativa: int | None
    calidad_presentacion: int | None
    diferenciadores_amenidades: int | None
    transparencia_precio: int | None


SQL_DETALLE = """
    select
        p.listing_id, p.corregimiento, p.tipo_inmueble, p.price_usd, p.bedrooms,
        p.bathrooms, p.area_m2, p.title, p.imagenes, p.descripcion,
        ST_X(p.geom) as lng, ST_Y(p.geom) as lat, p.ubicacion_aproximada,
        s.precio_predicho, s.categoria_semaforo, s.confianza_reducida,
        k.cluster_id,
        q.completitud_informativa, q.calidad_presentacion,
        q.diferenciadores_amenidades, q.transparencia_precio
    from propiedades p
    left join valuacion_semaforo_knn s on s.listing_id = p.listing_id
    left join valuacion_segmento_kmeans k on k.listing_id = p.listing_id
    left join valuacion_quality_scorer q on q.listing_id = p.listing_id
    where p.listing_id = %(listing_id)s
"""


@router.get("/{listing_id}", response_model=PropiedadDetalleResponse)
def obtener_propiedad(listing_id: int) -> PropiedadDetalleResponse:
    db_pool = obtener_pool()
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(SQL_DETALLE, {"listing_id": listing_id})
            fila = cur.fetchone()
            if fila is None:
                raise HTTPException(status_code=404, detail=f"listing_id={listing_id} no existe.")
            columnas = [desc[0] for desc in cur.description]
            datos = dict(zip(columnas, fila))
    finally:
        db_pool.putconn(conn)

    if datos["area_m2"] is not None:
        datos["area_m2"] = float(datos["area_m2"])
    if datos["precio_predicho"] is not None:
        datos["precio_predicho"] = float(datos["precio_predicho"])

    return PropiedadDetalleResponse(**datos)
