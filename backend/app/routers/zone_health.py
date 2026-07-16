"""Router `/zone-health` — `GET /zone-health/{corregimiento}`, único endpoint del plan de
traspaso de Épica 5 que no existía en absoluto (no una conexión a algo ya construido).
Destraba 5.2.6 (toggles Zone Health en Resultados) y 5.3.6 (mapa de amenidades en Detalle).

Auditoría previa (no asumida, verificada contra la base real el 2026-07-16):

`desglose_dimensiones` tiene 4 claves reales (`seguridad`, `amenidades`, `transporte`,
`walkability`), no 5 — falta `socioeconomico` pese a que CLAUDE.md documenta un peso de 0.15
para esa dimensión en el composite. Se devuelven las 4 claves tal cual están en la tabla, sin
inventar una quinta — el gap queda como hallazgo aparte para el equipo, no algo que este
endpoint deba resolver.

Los 3 corregimientos heredados de Bella Vista (El Cangrejo, Marbella, Obarrio) YA tienen
`zone_health_score`/`desglose_dimensiones` duplicados con el valor del padre directamente en
su propia fila — no hace falta un segundo query ni resolver `hereda_de` en Python, el dato ya
viene resuelto en la tabla. Se expone `heredado=true` (mismo criterio que
`ubicacion_aproximada` en `propiedades.py`) para que el frontend sepa que ese score no es
propio de la zona.

`amenidades` no requiere resolución espacial (`ST_Within` contra `corregimientos.geom`) — se
filtra por `zona_etiquetada_origen` (la zona del lote de extracción, 6 valores posibles: los
5 corregimientos oficiales con datos + Costa del Este), no por `corregimiento_asignado`
(resuelto geométricamente contra el polígono, Feature 1.4.3). Corregido 2026-07-16, sesión de
Épica 5 frontend — la primera versión de este endpoint usaba `corregimiento_asignado`, lo que
le regalaba a Parque Lefevre 13 de los 24 POIs de Costa del Este (caen dentro del polígono de
Parque Lefevre por proximidad geográfica, pero fueron extraídos y etiquetados como Costa del
Este en origen) y dejaba a Costa del Este con `amenidades: []` pese a tener 24 POIs reales.
Ya documentado como pendiente antes de esta corrección en
`Feature_1_4_Zone_Health_Composite_Index_Documentacion_Granular.md` §10 ("Presentación de los
13 POIs de Costa del Este que caen en Parque Lefevre — Pendiente para Feature 5.3.6").
Para El Cangrejo/Marbella/Obarrio (heredados de Bella Vista) el resultado no cambia:
`zona_etiquetada_origen` nunca toma esos 3 nombres (nunca hubo lote de extracción propio para
ellos), así que sigue resolviendo a `hereda_de` igual que antes.

**Nota de deuda técnica, no resuelta aquí:** 4 POIs físicos están cargados dos veces con `id`
distinto — una vez desde el lote de Costa del Este (Google Places) y otra desde el lote de
Parque Lefevre (OSM): Boston School International, Parque Felipe Motta, Este Park, The Casco
School. Con este fix ya no aparecen duplicados dentro de una misma respuesta (cada uno cae en
la zona de su propio `zona_etiquetada_origen`), pero siguen siendo 2 filas separadas en la
tabla — deduplicación pendiente, requiere decisión de qué registro es canónico.

Costa del Este: decisión de esta sesión (no 404) — es una zona real y conocida del scope,
con amenidades propias reales (24 POIs tras este fix), solo sin composite. Devuelve 200 con
`zone_health_score`/`desglose_dimensiones` en `NULL` (ya vienen así en la fila) y
`cobertura_composite_insuficiente=true` explícito, para que el frontend distinga "esta zona
no tiene composite" de "esta zona no existe". 404 se reserva para nombres que no están en la
tabla en absoluto — incluye `zona_no_determinada`, que no es una fila de `corregimientos`.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.pool import obtener_pool

router = APIRouter(prefix="/zone-health", tags=["zone-health"])


class AmenidadResponse(BaseModel):
    id: int
    categoria: str
    nombre: str | None
    lat: float | None
    lng: float | None
    rating: float | None


class ZoneHealthResponse(BaseModel):
    corregimiento: str
    es_oficial: bool
    hereda_de: str | None
    heredado: bool

    zone_health_score: float | None
    desglose_dimensiones: dict[str, float] | None
    estado_zone_health: str
    cobertura_composite_insuficiente: bool

    no_visualizado: bool
    motivo_visualizacion: str | None

    amenidades: list[AmenidadResponse]


SQL_CORREGIMIENTO = """
    select nombre, es_oficial, hereda_de, zone_health_score, desglose_dimensiones,
        estado_zone_health, no_visualizado, motivo_visualizacion
    from corregimientos
    where nombre = %(corregimiento)s
"""

SQL_AMENIDADES = """
    select id, categoria, nombre, ST_Y(geom) as lat, ST_X(geom) as lng, rating
    from amenidades
    where zona_etiquetada_origen = %(zona_amenidades)s
    order by categoria, nombre
"""


@router.get("/{corregimiento}", response_model=ZoneHealthResponse)
def obtener_zone_health(corregimiento: str) -> ZoneHealthResponse:
    db_pool = obtener_pool()
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(SQL_CORREGIMIENTO, {"corregimiento": corregimiento})
            fila = cur.fetchone()
            if fila is None:
                raise HTTPException(
                    status_code=404, detail=f"corregimiento={corregimiento!r} no existe."
                )
            columnas = [desc[0] for desc in cur.description]
            datos = dict(zip(columnas, fila))

            zona_amenidades = datos["hereda_de"] or datos["nombre"]
            cur.execute(SQL_AMENIDADES, {"zona_amenidades": zona_amenidades})
            columnas_amenidades = [desc[0] for desc in cur.description]
            amenidades = [
                dict(zip(columnas_amenidades, fila_amenidad))
                for fila_amenidad in cur.fetchall()
            ]
    finally:
        db_pool.putconn(conn)

    if datos["zone_health_score"] is not None:
        datos["zone_health_score"] = float(datos["zone_health_score"])
    for amenidad in amenidades:
        if amenidad["rating"] is not None:
            amenidad["rating"] = float(amenidad["rating"])

    return ZoneHealthResponse(
        corregimiento=datos["nombre"],
        es_oficial=datos["es_oficial"],
        hereda_de=datos["hereda_de"],
        heredado=datos["hereda_de"] is not None,
        zone_health_score=datos["zone_health_score"],
        desglose_dimensiones=datos["desglose_dimensiones"],
        estado_zone_health=datos["estado_zone_health"],
        cobertura_composite_insuficiente=datos["zone_health_score"] is None,
        no_visualizado=datos["no_visualizado"],
        motivo_visualizacion=datos["motivo_visualizacion"],
        amenidades=[AmenidadResponse(**a) for a in amenidades],
    )
