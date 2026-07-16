"""Puebla `corregimientos.geom` con el polígono real de los 5 corregimientos oficiales.

Fuente: pipeline/data/external/corregimientos/corregimientos_5zonas_poligonos_raw_osm.geojson
(OSM Overpass, `boundary=administrative`, `admin_level=8`). Aprobado por Besto como fuente
de `geom` en vez de los shapefiles STRI/HDX que cita el docstring de `cargar_corregimientos.py`
(Feature 1.3.1) — esos shapefiles no existen en el repo, verificado (`find` sin resultados),
mientras que este GeoJSON sí está presente y cubre los 5 corregimientos oficiales.

El GeoJSON tiene 10 features: 5 son el polígono real que necesitamos (`Polygon`/`MultiPolygon`,
uno por corregimiento oficial), las otras 5 son ruido de la extracción de Overpass (1
`LineString` de una relación admin_centre, 4 `Point` sueltos) — se descartan explícitamente
por tipo de geometría, no por índice o nombre, para que el filtro no dependa del orden del
archivo.

Nombre OSM "Bethania" vs. nombre en DB "Betania": normalizado vía la propiedad `alt_name`
del propio feature GeoJSON (`alt_name: "Betania"`), no un diccionario hardcodeado a ciegas —
si OSM alguna vez deja de traer `alt_name` para esa relación, el script falla ruidosamente
(KeyError) en vez de insertar bajo un nombre que ya no coincide con el real.

Costa del Este: NO incluida. Verificado contra Overpass API (Nominatim + 3 búsquedas
progresivas, la última case-insensitive y sin restricción de tag) que no existe ningún
`way`/`relation` con geometría de área para "Costa del Este" en OSM — solo un `node` puntual.
Queda con `geom = NULL`, sin excepción, hasta que exista una fuente real. El resto de las 4
zonas no oficiales (El Cangrejo, Marbella, Obarrio) NO se tocan aquí — por decisión de schema
ya cerrada en Ajuste_WBS_1_5_2 (`geom` heredado no se duplica en esta tabla, la resolución de
qué polígono mostrar para una zona heredada vive en la capa de presentación de Épica 5).

Este script hace UPDATE, no INSERT — las 9 filas de `corregimientos` ya existen (cargadas por
`cargar_corregimientos.py` en una sesión anterior).

`geom` es `geometry(Polygon, 4326)` estricto (confirmado contra `geometry_columns` de PostGIS
tras un primer intento de ejecución real que falló con
`InvalidParameterValue: Geometry type (MultiPolygon) does not match column type (Polygon)` —
la transacción "todo o nada" revirtió limpio, sin escritura parcial). San Francisco es
`MultiPolygon` en OSM (4 sub-polígonos: 1.64%, 1.92%, 96.40%, 0.05% del área total — los 3
pequeños son islotes/exclaves de la digitalización de Overpass). Decisión explícita: se usa
solo el sub-polígono más grande (96.4% del área), se descartan los 3 fragmentos menores — no
se altera el tipo de columna a `geometry(Geometry, 4326)` porque `geom` es aproximación
visual, nunca insumo de modelo, y mantener `Polygon` estricto en los 5 es más simple que un
tipo mixto. Esto se hace explícito en el dry-run (no es una simplificación silenciosa).

Protocolo de ejecución: por defecto SOLO imprime dry-run (los 5 UPDATE con su WKT resumido y
el bounding box de cada polígono, para sanity check visual antes de tocar producción). Ejecutar
de verdad requiere el flag explícito `--ejecutar` — a diferencia de `cargar_corregimientos.py`/
`cargar_propiedades.py` (que dejan un comentario "queda comentada a propósito" pero llaman a
la función de carga sin condición de todas formas, bug real confirmado en ambos), aquí la
ejecución está genuinamente gateada por un flag de CLI, no por una línea de código comentada
que alguien puede pasar por alto.
"""
import argparse
import json
import os
from pathlib import Path

import psycopg2
from dotenv import find_dotenv, load_dotenv
from shapely.geometry import shape

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_GEOJSON = (
    REPO_ROOT / "pipeline" / "data" / "external" / "corregimientos"
    / "corregimientos_5zonas_poligonos_raw_osm.geojson"
)

GEOMETRIAS_UTILIZABLES = {"Polygon", "MultiPolygon"}

UPDATE_SQL = """
    update corregimientos
    set geom = ST_GeomFromText(%(wkt)s, 4326)
    where nombre = %(nombre)s
"""


def construir_filas(geojson: dict) -> list[dict]:
    """Filtra las features usables y arma {nombre_db, wkt, bounds} por corregimiento.

    Descarta por tipo de geometría (Polygon/MultiPolygon vs. LineString/Point), no por
    posición en el archivo — el orden de features en un export de Overpass no está
    garantizado entre corridas.
    """
    filas = []
    for feature in geojson["features"]:
        geom_type = feature.get("geometry", {}).get("type")
        if geom_type not in GEOMETRIAS_UTILIZABLES:
            continue

        props = feature["properties"]
        nombre_osm = props["name"]
        # Único caso de mismatch conocido OSM vs. DB: "Bethania" -> "Betania" (alt_name).
        nombre_db = props["alt_name"] if nombre_osm == "Bethania" else nombre_osm

        geom_shapely = shape(feature["geometry"])

        # geom es geometry(Polygon, 4326) estricto en la DB — un MultiPolygon (San
        # Francisco en este dataset) no encaja. Se usa solo el sub-polígono de mayor
        # área, explícito en el resumen impreso, nunca silencioso.
        multipolygon_partes_descartadas = 0
        if geom_shapely.geom_type == "MultiPolygon":
            partes = list(geom_shapely.geoms)
            area_total = geom_shapely.area
            parte_principal = max(partes, key=lambda p: p.area)
            multipolygon_partes_descartadas = len(partes) - 1
            pct_usado = 100 * parte_principal.area / area_total
            geom_shapely = parte_principal
        else:
            pct_usado = 100.0

        filas.append({
            "nombre_db": nombre_db,
            "nombre_osm": nombre_osm,
            "wkt": geom_shapely.wkt,
            "bounds": geom_shapely.bounds,  # (min_lon, min_lat, max_lon, max_lat)
            "multipolygon_partes_descartadas": multipolygon_partes_descartadas,
            "pct_area_usado": pct_usado,
        })
    return filas


def imprimir_dry_run(filas: list[dict]) -> None:
    print(f"Dry-run — {len(filas)} UPDATE de corregimientos.geom a generar:\n")
    for fila in filas:
        min_lon, min_lat, max_lon, max_lat = fila["bounds"]
        wkt_resumido = fila["wkt"][:120] + ("..." if len(fila["wkt"]) > 120 else "")
        print(f"- {fila['nombre_db']}" + (f" (OSM: {fila['nombre_osm']})" if fila['nombre_osm'] != fila['nombre_db'] else ""))
        print(f"    UPDATE corregimientos set geom = ST_GeomFromText(%(wkt)s, 4326) where nombre = '{fila['nombre_db']}'")
        print(f"    wkt (primeros 120 chars) = {wkt_resumido}")
        print(f"    wkt longitud total       = {len(fila['wkt'])} caracteres")
        print(f"    bounding box             = lon [{min_lon:.5f}, {max_lon:.5f}] · lat [{min_lat:.5f}, {max_lat:.5f}]")
        if fila["multipolygon_partes_descartadas"] > 0:
            print(
                f"    ADVERTENCIA MultiPolygon = {fila['multipolygon_partes_descartadas']} sub-polígono(s) "
                f"descartado(s), se usa solo el mayor ({fila['pct_area_usado']:.2f}% del área OSM original)"
            )
        print()

    nombres_cargados = {f["nombre_db"] for f in filas}
    faltantes = {"San Francisco", "Bella Vista", "Parque Lefevre", "Betania", "Pedregal"} - nombres_cargados
    if faltantes:
        print(f"ADVERTENCIA — oficiales sin polígono en este dry-run: {sorted(faltantes)}")
    print("Costa del Este: NO incluida (sin polígono en OSM, verificado — ver docstring del script).")
    print("El Cangrejo / Marbella / Obarrio: NO tocadas (geom heredado no se duplica en esta tabla, decisión de schema ya cerrada).")


def ejecutar_updates(filas: list[dict]) -> None:
    """Aplica los 5 UPDATE en una única transacción (todo o nada)."""
    database_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for fila in filas:
                    cur.execute(UPDATE_SQL, {"wkt": fila["wkt"], "nombre": fila["nombre_db"]})
                    if cur.rowcount != 1:
                        raise RuntimeError(
                            f"UPDATE para '{fila['nombre_db']}' afectó {cur.rowcount} filas, "
                            f"esperaba exactamente 1 — abortando transacción completa."
                        )
        print(f"{len(filas)} filas de corregimientos actualizadas con geom real.")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Ejecuta los UPDATE contra Supabase de verdad. Sin este flag, solo dry-run.",
    )
    args = parser.parse_args()

    with open(RUTA_GEOJSON, encoding="utf-8") as f:
        geojson = json.load(f)

    filas = construir_filas(geojson)
    assert len(filas) == 5, f"esperaba 5 polígonos oficiales usables, encontré {len(filas)}"

    imprimir_dry_run(filas)

    if not args.ejecutar:
        print("\nDry-run únicamente — nada se ejecutó contra Supabase. Correr con --ejecutar para aplicar de verdad.")
        return

    ejecutar_updates(filas)


if __name__ == "__main__":
    main()
