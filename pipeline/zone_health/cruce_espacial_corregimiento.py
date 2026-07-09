#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cruce_espacial_corregimiento.py
================================
Feature 1.4 -- cruce punto-en-poligono (Acta 1.3 §6.3), antes solo documentado
como metodo pero nunca versionado como codigo (ver auditoria Feature 1.4,
2026-07-09: metro_estaciones_final_30.jsonl tenia corregimiento_id null en
30/30 registros porque este cruce nunca se ejecuto contra ese archivo).

Asigna corregimiento_id a un punto (lat, lng) usando shapely Point().contains()
contra los poligonos reales de las 5 zonas administrativas
(pipeline/data/external/corregimientos/corregimientos_5zonas_poligonos_raw_osm.geojson).
Un punto fuera de las 5 zonas reales devuelve None -- eso es el resultado
correcto para la mayoria de puntos de GTFS (MiBus cubre toda la ciudad), no
un error.
"""

import json
from pathlib import Path

from shapely.geometry import Point, shape

RUTA_COREGIMIENTOS = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "external"
    / "corregimientos"
    / "corregimientos_5zonas_poligonos_raw_osm.geojson"
)


def cargar_poligonos(ruta: Path = RUTA_COREGIMIENTOS) -> dict:
    """Carga los poligonos de limite administrativo (`boundary`) del geojson.

    El geojson mezcla relations (poligonos), ways y nodes (admin_centre) en
    un solo FeatureCollection -- solo las features con properties.type ==
    "boundary" tienen geometria de poligono utilizable; el resto se ignora.

    Nota: OSM registra Betania como "Bethania" (name) con alt_name "Betania".
    Se normaliza aqui a "Betania" para que coincida con el resto de los
    archivos del pipeline (seguridad, INEC/socioeconomico).

    Returns:
        dict corregimiento -> shapely Polygon/MultiPolygon.
    """
    with ruta.open(encoding="utf-8") as f:
        geojson = json.load(f)

    poligonos = {}
    for feature in geojson["features"]:
        props = feature.get("properties", {})
        if props.get("type") != "boundary":
            continue
        nombre = props.get("name")
        if nombre == "Bethania":
            nombre = "Betania"
        poligonos[nombre] = shape(feature["geometry"])
    return poligonos


def asignar_corregimiento(
    lat: float, lng: float, poligonos: dict
) -> str | None:
    """Devuelve el corregimiento cuyo poligono contiene el punto (lat, lng).

    geojson usa orden (lon, lat) -- shapely.geometry.Point espera (x, y),
    es decir (lng, lat). Invertir este orden produce asignaciones
    silenciosamente incorrectas sin lanzar error.

    Devuelve None si el punto no cae dentro de ninguno de los 5 poligonos
    reales (caso esperado para la mayoria de paradas fuera del scope de
    las 9 zonas).
    """
    punto = Point(lng, lat)
    for nombre, poligono in poligonos.items():
        if poligono.contains(punto) or poligono.touches(punto):
            return nombre
    return None


def asignar_corregimientos_batch(
    puntos: list[tuple[float, float]], poligonos: dict | None = None
) -> list[str | None]:
    """Aplica asignar_corregimiento a una lista de puntos (lat, lng)."""
    if poligonos is None:
        poligonos = cargar_poligonos()
    return [asignar_corregimiento(lat, lng, poligonos) for lat, lng in puntos]


def _actualizar_metro_estaciones() -> None:
    ruta_metro = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "external"
        / "metro"
        / "metro_estaciones_final_30.jsonl"
    )

    poligonos = cargar_poligonos()

    registros = []
    with ruta_metro.open(encoding="utf-8") as f:
        for linea in f:
            registro = json.loads(linea)
            registro["corregimiento_id"] = asignar_corregimiento(
                registro["lat"], registro["lng"], poligonos
            )
            registros.append(registro)

    with ruta_metro.open("w", encoding="utf-8") as f:
        for registro in registros:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    pobladas = sum(1 for r in registros if r["corregimiento_id"] is not None)
    print(f"metro_estaciones_final_30.jsonl actualizado: {pobladas}/{len(registros)} con corregimiento_id poblado")
    for r in registros:
        if r["corregimiento_id"] is not None:
            print(f"  {r['nombre']} -> {r['corregimiento_id']}")


if __name__ == "__main__":
    _actualizar_metro_estaciones()
