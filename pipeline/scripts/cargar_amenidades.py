"""Carga de la tabla amenidades (Feature 1.5.3) desde los 6 archivos de datos crudos.

Fuente de datos: pipeline/data/external/amenidades/ — 3 JSONL de Google Places
(San Francisco, Bella Vista, Costa del Este) + 3 GeoJSON de OSM Overpass (Betania,
Parque Lefevre, Pedregal). El archivo combinado
amenidades_betania_obarrio_cangrejo_marbella_osm.geojson se EXCLUYE explícitamente —
ver Context-MD/Ajuste_WBS_1_5_3_Esquema_Amenidades.md §2 (ninguna de sus 60 claves de
properties indica zona por punto individual, producto de una sola consulta Overpass
con bbox único cubriendo 4 zonas a la vez).

Esquema de destino: Ajuste_WBS_1_5_3_Esquema_Amenidades.md §4, migración
supabase/migrations/20260715040003_amenidades_create_table.sql.

fuente: determinada por presencia REAL de place_id en cada registro, nunca por nombre
de archivo — necesario porque amenidades_parque_lefevre_osm.geojson contiene 1
registro con origen real Google Places (@id="google_places/<place_id>", migrado desde
San Francisco por auditoría geométrica previa, con nota_auditoria propia en el JSON
de origen).

corregimiento_asignado: pipeline/zone_health/cruce_espacial_corregimiento.py::
asignar_corregimiento() se aplica a TODAS las filas sin excepción, incluyendo las de
origen Google Places — brecha que CLAUDE.md ya documentaba como pendiente (solo se
había aplicado ad hoc a los archivos OSM hasta ahora). NULL esperado para Costa del
Este (sin polígono en corregimientos_5zonas_poligonos_raw_osm.geojson).

geom_tipo_origen: OSM mezcla features Point (nodos) y Polygon (ways/edificios) — todo
se normaliza a Point; 'polygon_centroid' marca cuándo la coordenada es una
aproximación (centroide vía shapely), no la ubicación exacta del POI.

categoria: 6 categorías CRUDAS (Acta 1.3 §8 decisión 1), sin fusionar hospital+clinica
en "salud" — esa fusión es cómputo de Zone Health (normalizacion_amenidades.py,
Feature 1.4.3), no propiedad del dato fuente. Filas OSM cuyo tag amenity/shop/leisure
no mapea a ninguna de las 6 categorías se excluyen de la carga (violarían el CHECK de
la columna) — se cuentan y reportan en el resumen, nunca se descartan en silencio.

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — la llamada a cargar() queda comentada
a propósito en el bloque `if __name__ == "__main__"`, requiere habilitarla con
confirmación explícita del usuario (mismo protocolo que la migración CREATE TABLE).
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import find_dotenv, load_dotenv
from shapely.geometry import shape

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_AMENIDADES = REPO_ROOT / "pipeline" / "data" / "external" / "amenidades"

sys.path.insert(0, str(REPO_ROOT / "pipeline" / "zone_health"))
from cruce_espacial_corregimiento import cargar_poligonos, asignar_corregimiento  # noqa: E402

# Google Places: la columna `categoria` del JSONL ya viene en la taxonomia final
# (Acta 1.3 §8 decision 1), sin remapeo necesario.
CATEGORIAS_VALIDAS = {"supermercado", "farmacia", "hospital", "clinica", "parque", "colegio"}

# (tag OSM, valor) -> categoria CRUDA. A diferencia de MAPA_TAGS_OSM en
# normalizacion_amenidades.py (que fusiona amenity=clinic/hospital a "salud" para el
# computo de Zone Health), aqui se preservan separadas -- esa fusion es cosa del
# consumidor del dato (Feature 1.4.3), no del esquema de origen.
MAPA_TAGS_OSM = {
    ("shop", "supermarket"): "supermercado",
    ("leisure", "park"): "parque",
    ("amenity", "pharmacy"): "farmacia",
    ("amenity", "school"): "colegio",
    ("amenity", "clinic"): "clinica",
    ("amenity", "hospital"): "hospital",
}

FUENTES_GOOGLE_PLACES = {
    "San Francisco": RUTA_AMENIDADES / "amenidades_san_francisco_google_places.jsonl",
    "Bella Vista": RUTA_AMENIDADES / "amenidades_bella_vista_google_places.jsonl",
    "Costa del Este": RUTA_AMENIDADES / "amenidades_costa_del_este_google_places.jsonl",
}

FUENTES_OSM = {
    "Betania": RUTA_AMENIDADES / "amenidades_betania_osm.geojson",
    "Parque Lefevre": RUTA_AMENIDADES / "amenidades_parque_lefevre_osm.geojson",
    "Pedregal": RUTA_AMENIDADES / "amenidades_pedregal_osm.geojson",
}
# amenidades_betania_obarrio_cangrejo_marbella_osm.geojson EXCLUIDO -- ver docstring
# y Ajuste_WBS_1_5_3_Esquema_Amenidades.md §2.

# Caso de frontera geográfica documentado (distinto del caso Parque Lefevre <- San
# Francisco, que es un error de extracción ya corregido en el propio archivo fuente):
# POIs etiquetados como Costa del Este por Google Places que caen administrativamente
# dentro del polígono real de Parque Lefevre. Geografía real, no error -- ver
# Feature_1_3_7_Extraccion_Amenidades_Acta.md §5.3.
NOTA_FRONTERA_COSTA_DEL_ESTE_PARQUE_LEFEVRE = (
    "Frontera geográfica documentada mercado/administración -- "
    "Feature_1_3_7_Extraccion_Amenidades_Acta.md §5.3: POI etiquetado como Costa del "
    "Este cae administrativamente dentro del polígono de Parque Lefevre. No es error "
    "de extracción -- geografía real ya documentada."
)

INSERT_SQL = """
    insert into amenidades (
        categoria, nombre, geom, geom_tipo_origen, fuente, zona_etiquetada_origen,
        corregimiento_asignado, place_id, telefono, rating, propiedades_raw, nota_auditoria
    ) values (
        %(categoria)s, %(nombre)s,
        ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326),
        %(geom_tipo_origen)s, %(fuente)s, %(zona_etiquetada_origen)s,
        %(corregimiento_asignado)s, %(place_id)s, %(telefono)s, %(rating)s,
        %(propiedades_raw)s, %(nota_auditoria)s
    )
"""


def _fuente_y_place_id(props: dict) -> tuple[str, str | None]:
    """Determina `fuente` por presencia REAL de place_id, no por archivo de origen.

    Cubre las 2 formas en que place_id aparece en los datos crudos:
    - JSONL de Google Places: clave `place_id` explícita.
    - GeoJSON "OSM" con un registro migrado de Google Places (caso conocido de
      Parque Lefevre): @id con prefijo "google_places/<place_id>", sin clave
      `place_id` propia -- el place_id vive dentro de @id.
    Cualquier otro caso (nodos/ways reales de OSM, @id tipo "node/..."/"way/...")
    es osm_overpass.
    """
    if props.get("place_id"):
        return "google_places", props["place_id"]
    id_field = props.get("@id", "")
    if isinstance(id_field, str) and id_field.startswith("google_places/"):
        return "google_places", id_field[len("google_places/"):]
    return "osm_overpass", None


def _leer_google_places(ruta: Path, zona: str) -> tuple[list[dict], int]:
    filas = []
    excluidas = 0
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            registro = json.loads(linea)
            categoria = registro.get("categoria")
            if categoria not in CATEGORIAS_VALIDAS:
                excluidas += 1
                continue
            fuente, place_id = _fuente_y_place_id(registro)
            filas.append({
                "categoria": categoria,
                "nombre": registro.get("nombre"),
                "lat": registro["lat"],
                "lng": registro["lng"],
                "geom_tipo_origen": "point",
                "fuente": fuente,
                "zona_etiquetada_origen": zona,
                "place_id": place_id,
                "telefono": registro.get("telefono"),
                "rating": registro.get("rating"),
                "propiedades_raw": registro,
                "nota_auditoria": registro.get("nota_auditoria"),
            })
    return filas, excluidas


def _leer_osm(ruta: Path, zona: str) -> tuple[list[dict], int]:
    filas = []
    excluidas = 0
    with ruta.open(encoding="utf-8") as f:
        geojson = json.load(f)

    for feature in geojson["features"]:
        props = feature.get("properties", {})

        categoria = None
        for tag in ("shop", "leisure", "amenity"):
            if tag in props and (tag, props[tag]) in MAPA_TAGS_OSM:
                categoria = MAPA_TAGS_OSM[(tag, props[tag])]
                break
        if categoria is None:
            excluidas += 1
            continue

        geometry = feature["geometry"]
        if geometry["type"] == "Point":
            lng, lat = geometry["coordinates"]
            geom_tipo_origen = "point"
        else:
            centro = shape(geometry).centroid
            lng, lat = centro.x, centro.y
            geom_tipo_origen = "polygon_centroid"

        fuente, place_id = _fuente_y_place_id(props)

        filas.append({
            "categoria": categoria,
            "nombre": props.get("name"),
            "lat": lat,
            "lng": lng,
            "geom_tipo_origen": geom_tipo_origen,
            "fuente": fuente,
            "zona_etiquetada_origen": zona,
            "place_id": place_id,
            "telefono": props.get("telefono") if fuente == "google_places" else None,
            "rating": props.get("rating") if fuente == "google_places" else None,
            "propiedades_raw": props,
            "nota_auditoria": props.get("nota_auditoria"),
        })
    return filas, excluidas


def construir_filas() -> tuple[list[dict], dict]:
    """Lee las 6 fuentes, aplica asignar_corregimiento() a cada fila sin excepción.

    poligonos se carga una sola vez (5 zonas administrativas oficiales) y se reusa
    para las 238 filas -- Costa del Este no tiene polígono ahí, así que sus filas
    resuelven a None por diseño de la función, no por un bug de esta carga.
    """
    poligonos = cargar_poligonos()
    filas = []
    excluidas_por_zona = {}

    for zona, ruta in FUENTES_GOOGLE_PLACES.items():
        nuevas, excluidas = _leer_google_places(ruta, zona)
        filas.extend(nuevas)
        excluidas_por_zona[zona] = excluidas

    for zona, ruta in FUENTES_OSM.items():
        nuevas, excluidas = _leer_osm(ruta, zona)
        filas.extend(nuevas)
        excluidas_por_zona[zona] = excluidas

    for fila in filas:
        fila["corregimiento_asignado"] = asignar_corregimiento(
            fila["lat"], fila["lng"], poligonos
        )
        if (
            fila["zona_etiquetada_origen"] == "Costa del Este"
            and fila["corregimiento_asignado"] == "Parque Lefevre"
        ):
            fila["nota_auditoria"] = NOTA_FRONTERA_COSTA_DEL_ESTE_PARQUE_LEFEVRE

    return filas, excluidas_por_zona


def imprimir_resumen(filas: list[dict], excluidas_por_zona: dict) -> None:
    por_zona = Counter(f["zona_etiquetada_origen"] for f in filas)
    por_fuente = Counter(f["fuente"] for f in filas)
    con_nota = [f for f in filas if f.get("nota_auditoria")]
    nulos_por_zona = Counter(
        f["zona_etiquetada_origen"] for f in filas if f["corregimiento_asignado"] is None
    )

    print(f"Resumen de carga -- {len(filas)} filas a insertar en amenidades:\n")

    print("Filas por zona_etiquetada_origen:")
    for zona in list(FUENTES_GOOGLE_PLACES) + list(FUENTES_OSM):
        excl = excluidas_por_zona.get(zona, 0)
        extra = f"  (+{excl} excluidas, sin categoria mapeable)" if excl else ""
        print(f"  {zona}: {por_zona.get(zona, 0)}{extra}")

    print(f"\ncorregimiento_asignado = NULL: {sum(nulos_por_zona.values())} fila(s) en total")
    for zona, n in nulos_por_zona.items():
        print(f"  {zona}: {n}")

    print("\nfuente:")
    print(f"  google_places: {por_fuente.get('google_places', 0)}")
    print(f"  osm_overpass:  {por_fuente.get('osm_overpass', 0)}")

    print(f"\nnota_auditoria poblada: {len(con_nota)} fila(s)")
    for f in con_nota:
        print(f"  [{f['zona_etiquetada_origen']} | fuente={f['fuente']} | categoria={f['categoria']} | nombre={f['nombre']}]")
        print(f"    corregimiento_asignado = {f['corregimiento_asignado']}")
        print(f"    nota_auditoria = {f['nota_auditoria']}")


def cargar(filas: list[dict]) -> None:
    """Inserta las filas de amenidades en una única transacción (todo o nada)."""
    database_url = os.environ["DATABASE_URL"]

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for fila in filas:
                    params = dict(fila)
                    params["propiedades_raw"] = psycopg2.extras.Json(params["propiedades_raw"])
                    cur.execute(INSERT_SQL, params)
        # El `with conn:` hace commit al salir sin excepción, o rollback completo si
        # cualquier INSERT de la transacción falla (todo o nada).
        print(f"{len(filas)} filas insertadas en amenidades.")
    finally:
        conn.close()


def main() -> None:
    filas, excluidas_por_zona = construir_filas()
    imprimir_resumen(filas, excluidas_por_zona)

    # Habilitado con confirmación explícita del usuario (2026-07-15) tras revisión
    # del resumen y del dry-run previo.
    cargar(filas)


if __name__ == "__main__":
    main()
