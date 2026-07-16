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

`amenidades` no requiere resolución espacial (`ST_Within` contra `corregimientos.geom`): la
tabla ya tiene una columna directa `corregimiento_asignado`, poblada en la carga
(`pipeline/zone_health/cruce_espacial_corregimiento.py::asignar_corregimiento()`), que ya
resuelve los puntos de El Cangrejo/Marbella/Obarrio contra el polígono del padre (Bella
Vista) porque esos 3 nunca tuvieron polígono propio con el que cruzar — ningún row de
`amenidades` tiene `corregimiento_asignado` igual a esos 3 nombres. Filtrar amenidades por
`hereda_de` (si existe) o por el nombre propio (si no) es, por lo tanto, correcto y no
necesita PostGIS en este endpoint.

Costa del Este: decisión de esta sesión (no 404) — es una zona real y conocida del scope,
con amenidades propias reales (11 filas), solo sin composite. Devuelve 200 con
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
    where corregimiento_asignado = %(zona_amenidades)s
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
