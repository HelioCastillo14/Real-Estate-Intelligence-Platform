#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizacion_walkability.py
==============================
Feature 1.4.4 -- Walkability como proxy de un solo componente (distancia
promedio a amenidades clave), a escala 0-1 por corregimiento, para el
Zone Health Composite Index (peso 0.15).

SOLO cubre las 5 zonas con corregimiento administrativo real:
Bella Vista, Betania, Parque Lefevre, Pedregal, San Francisco.
El Cangrejo, Marbella, Obarrio (heredan de Bella Vista) y Costa del Este
(sin herencia, sin score compuesto) NO se tocan aqui.

DECISION DE ALCANCE (Acta de Feature 1.4, seccion de walkability): esta
dimension NO incluye componente de red vial (densidad de interseccion,
longitud de acera, indice de conectividad de calles, etc.) porque ese dato
no existe en el repo -- se verifico explicitamente antes de implementar
(grep de tags `highway`/`footway`/`sidewalk` sobre todo `pipeline/data/`,
0 resultados, ni siquiera como subproducto de las consultas Overpass de
amenidades ya hechas para 1.4.3). Walkability queda redefinida como proxy
de UN solo componente: que tan cerca esta el centro de la zona de un
conjunto acotado de amenidades clave. No es una medida de caminabilidad en
el sentido urbanistico completo (no captura calidad de acera, sombra,
seguridad peatonal) -- es una aproximacion basada en distancia.

AMENIDADES CLAVE (Encuesta SS2.3 + SS2.2) y por que estas 3 y no otras:
  - supermercado: la categoria de mayor peso en la Encuesta SS2.3
    (0.3137, ver PESOS en normalizacion_amenidades.py) -- la amenidad que
    los encuestados reportan visitar con mas frecuencia regular.
  - parque: segunda categoria de mayor peso en SS2.3 (0.2549) -- proxy de
    espacio recreativo/verde accesible a pie.
  - metro: no es una categoria de la taxonomia de amenidades de 1.4.3
    (esa taxonomia cubre comercio/servicios, no transporte), pero la
    Encuesta SS2.2 (misma seccion de importancia percibida que respalda
    los pesos de transporte en 1.4.2) senala la cercania a una estacion de
    metro como el factor de movilidad peatonal mas mencionado -- de ahi
    que se incluya aqui como tercera amenidad clave en lugar de, por
    ejemplo, paradas de bus (mucho mas numerosas y por tanto un proxy de
    distancia poco discriminante entre zonas).
  Farmacia, salud y colegio (las otras 3 categorias de 1.4.3) quedan
  fuera de walkability por decision de alcance del Acta -- ya estan
  representadas, ponderadas, en la dimension de amenidades (1.4.3, peso
  0.20); incluirlas de nuevo aqui duplicaria su influencia en el indice
  compuesto.

METODO:
  1. Punto de referencia por zona: centroide del poligono real (shapely),
     usando el mismo filtro `geometry.type in (Polygon, MultiPolygon) AND
     properties.name` y el mismo mapeo Bethania->Betania ya implementados
     en `cruce_espacial_corregimiento.cargar_poligonos()` -- reutilizados
     aqui, no reimplementados.
  2. Para supermercado y parque: distancia minima (haversine, metros)
     desde el centroide contra el conjunto COMBINADO de amenidades de las
     5 zonas reales (no solo las de la propia zona) -- una zona puede
     estar mas cerca de un supermercado ubicado justo al otro lado de su
     limite administrativo, y esa cercania real no debe perderse por
     filtrar de mas. Se reutilizan las mismas fuentes y el mismo mapeo de
     categorias que 1.4.3 (`normalizacion_amenidades.RUTA_GOOGLE_PLACES`,
     `RUTA_OSM`, `MAPA_CATEGORIA_GOOGLE_PLACES`, `MAPA_TAGS_OSM`) -- para
     features OSM tipo Polygon se usa el centroide del poligono (mismo
     criterio que 1.4.3 para contar), para Point se usa la coordenada
     directa.
  3. Para metro: distancia minima contra las 30 estaciones completas de
     `metro_estaciones_final_30.jsonl` -- las 30, no solo las 4 con
     `corregimiento_id` ya poblado, porque aqui no importa a que
     corregimiento pertenece la estacion, solo su distancia geografica al
     centroide (una estacion fuera de las 5 zonas reales puede seguir
     siendo la mas cercana a una de ellas).
  4. distancia_promedio_m = promedio simple (sin ponderar) de las 3
     distancias minimas. Sin ponderacion entre categorias -- mismo
     criterio ya aceptado en 1.4.2 (transporte) para metro/bus: se
     documenta aqui como limitacion conocida, no como omision. En la
     practica esto trata "un supermercado a 200m" y "un metro a 200m"
     como equivalentes en su aporte al promedio, cuando su impacto real
     en la experiencia peatonal probablemente no es identico.
  5. Normalizacion: min-max invertido, misma direccion que seguridad
     (1.4.1) -- una distancia_promedio_m alta significa una zona MENOS
     caminable, y eso debe traducirse en un score BAJO.
     Formula: score = 1 - ((x - min) / (max - min))

LIMITACION CONOCIDA (n=5, mismo tratamiento que 1.4.1/1.4.2/1.4.3): min-max
sobre 5 zonas es sensible a outliers y se recalcula por completo si se
agrega o quita una zona. No tratar este score como una escala absoluta de
caminabilidad.

FUENTES DE DATOS:
  Centroides de zona:
    `pipeline/data/external/corregimientos/corregimientos_5zonas_poligonos_raw_osm.geojson`
    (via `cruce_espacial_corregimiento.cargar_poligonos()`)
  Amenidades supermercado/parque (mismas fuentes que 1.4.3):
    `pipeline/data/external/amenidades/amenidades_bella_vista_google_places.jsonl`
    `pipeline/data/external/amenidades/amenidades_san_francisco_google_places.jsonl`
    `pipeline/data/external/amenidades/amenidades_betania_osm.geojson`
    `pipeline/data/external/amenidades/amenidades_parque_lefevre_osm.geojson`
    `pipeline/data/external/amenidades/amenidades_pedregal_osm.geojson`
  Metro:
    `pipeline/data/external/metro/metro_estaciones_final_30.jsonl` (30/30 filas)
"""

import json
import math
import sys
from pathlib import Path

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cruce_espacial_corregimiento import cargar_poligonos  # noqa: E402
from normalizacion_amenidades import (  # noqa: E402
    MAPA_CATEGORIA_GOOGLE_PLACES,
    MAPA_TAGS_OSM,
    RUTA_GOOGLE_PLACES,
    RUTA_OSM,
)

ZONAS_REALES = [
    "Bella Vista",
    "Betania",
    "Parque Lefevre",
    "Pedregal",
    "San Francisco",
]

RUTA_METRO = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "external"
    / "metro"
    / "metro_estaciones_final_30.jsonl"
)

RUTA_SALIDA = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "zone_health_walkability_1_4_4.json"
)


def distancia_haversine_metros(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """Distancia en metros sobre la esfera terrestre entre dos puntos (lat, lng).

    Radio terrestre medio: 6,371,000 m. Suficiente para distancias del
    orden de decenas de km dentro del scope de las 9 zonas -- no se
    requiere un modelo elipsoidal mas preciso a esta escala.
    """
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def distancia_minima_metros(
    centroide: tuple[float, float], puntos: list[tuple[float, float]]
) -> float:
    """Distancia minima (metros) desde un centroide (lat, lng) al mas
    cercano de una lista de puntos (lat, lng). `puntos` no puede estar vacia.
    """
    lat_c, lng_c = centroide
    return min(
        distancia_haversine_metros(lat_c, lng_c, lat_p, lng_p)
        for lat_p, lng_p in puntos
    )


def calcular_distancias_zona(
    centroide: tuple[float, float],
    puntos_supermercado: list[tuple[float, float]],
    puntos_parque: list[tuple[float, float]],
    puntos_metro: list[tuple[float, float]],
) -> dict[str, float]:
    """Calcula las 3 distancias minimas (metros) y su promedio simple para
    una zona, dado su centroide y los 3 conjuntos combinados de puntos.

    Returns:
        dict con distancia_supermercado_m, distancia_parque_m,
        distancia_metro_m, distancia_promedio_m.
    """
    dist_supermercado = distancia_minima_metros(centroide, puntos_supermercado)
    dist_parque = distancia_minima_metros(centroide, puntos_parque)
    dist_metro = distancia_minima_metros(centroide, puntos_metro)
    promedio = (dist_supermercado + dist_parque + dist_metro) / 3
    return {
        "distancia_supermercado_m": dist_supermercado,
        "distancia_parque_m": dist_parque,
        "distancia_metro_m": dist_metro,
        "distancia_promedio_m": promedio,
    }


def normalizar_walkability(promedios: dict[str, float]) -> dict[str, float]:
    """Normaliza distancia_promedio_m a score_walkability en [0,1] via
    min-max invertido.

    Formula: score = 1 - ((x - min) / (max - min))

    Por que se invierte: una distancia promedio alta significa una zona
    menos caminable (las amenidades clave estan mas lejos de su centro), y
    eso debe traducirse en un score de walkability BAJO. Sin la inversion,
    la zona mas alejada de sus amenidades clave terminaria con el score
    mas alto -- al reves de lo que representa la dimension (mismo criterio
    que seguridad, 1.4.1).

    Args:
        promedios: dict corregimiento -> distancia_promedio_m. Debe
            contener unicamente las 5 zonas reales listadas en
            ZONAS_REALES.

    Returns:
        dict corregimiento -> score_walkability, cada valor en [0,1].
    """
    valores = list(promedios.values())
    minimo, maximo = min(valores), max(valores)
    return {
        zona: 1 - ((x - minimo) / (maximo - minimo))
        for zona, x in promedios.items()
    }


def _cargar_centroides() -> dict[str, tuple[float, float]]:
    """Centroide (lat, lng) de cada una de las 5 zonas reales, via
    `cruce_espacial_corregimiento.cargar_poligonos()` (mismo filtro
    Polygon/MultiPolygon + name, mismo mapeo Bethania->Betania).
    """
    poligonos = cargar_poligonos()
    centroides = {}
    for zona, poligono in poligonos.items():
        centroide = poligono.centroid
        centroides[zona] = (centroide.y, centroide.x)  # (lat, lng)
    return centroides


def _punto_representativo(geometry: dict) -> tuple[float, float]:
    """(lat, lng) de una geometria GeoJSON: coordenada directa si es Point,
    centroide si es Polygon/MultiPolygon (mismo criterio que 1.4.3 para
    contar features OSM con geometria de area).
    """
    figura = shape(geometry)
    if geometry["type"] == "Point":
        lng, lat = geometry["coordinates"]
        return (lat, lng)
    centroide = figura.centroid
    return (centroide.y, centroide.x)


def _cargar_puntos_supermercado_y_parque() -> tuple[
    list[tuple[float, float]], list[tuple[float, float]]
]:
    """Puntos (lat, lng) de supermercado y parque, combinados de las 5
    zonas reales -- reutiliza las mismas fuentes y mapeos de categoria de
    `normalizacion_amenidades` (1.4.3), sin volver a declararlos.
    """
    puntos_supermercado: list[tuple[float, float]] = []
    puntos_parque: list[tuple[float, float]] = []

    for ruta in RUTA_GOOGLE_PLACES.values():
        with ruta.open(encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                registro = json.loads(linea)
                cat = MAPA_CATEGORIA_GOOGLE_PLACES.get(registro["categoria"])
                if cat == "supermercado":
                    puntos_supermercado.append((registro["lat"], registro["lng"]))
                elif cat == "parque":
                    puntos_parque.append((registro["lat"], registro["lng"]))

    for ruta in RUTA_OSM.values():
        with ruta.open(encoding="utf-8") as f:
            geojson = json.load(f)
        for feature in geojson["features"]:
            props = feature.get("properties", {})
            cat = None
            for tag in ("shop", "leisure", "amenity"):
                if tag in props and (tag, props[tag]) in MAPA_TAGS_OSM:
                    cat = MAPA_TAGS_OSM[(tag, props[tag])]
                    break
            if cat not in ("supermercado", "parque"):
                continue
            punto = _punto_representativo(feature["geometry"])
            if cat == "supermercado":
                puntos_supermercado.append(punto)
            else:
                puntos_parque.append(punto)

    return puntos_supermercado, puntos_parque


def _cargar_puntos_metro(ruta: Path = RUTA_METRO) -> list[tuple[float, float]]:
    """Puntos (lat, lng) de las 30 estaciones de metro completas -- no se
    filtra por `corregimiento_id`, ver docstring del modulo."""
    puntos = []
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            registro = json.loads(linea)
            puntos.append((registro["lat"], registro["lng"]))
    return puntos


def main() -> None:
    centroides = _cargar_centroides()
    puntos_supermercado, puntos_parque = _cargar_puntos_supermercado_y_parque()
    puntos_metro = _cargar_puntos_metro()

    distancias_por_zona = {
        zona: calcular_distancias_zona(
            centroides[zona], puntos_supermercado, puntos_parque, puntos_metro
        )
        for zona in ZONAS_REALES
    }
    promedios = {
        zona: distancias_por_zona[zona]["distancia_promedio_m"]
        for zona in ZONAS_REALES
    }
    scores = normalizar_walkability(promedios)

    salida = {
        "feature": "1.4.4",
        "dimension": "walkability",
        "peso_zone_health": 0.15,
        "metodo": "proxy de distancia a amenidades clave (supermercado, parque, metro); min-max invertido: 1 - ((x - min) / (max - min))",
        "amenidades_clave": ["supermercado", "parque", "metro"],
        "sin_componente_red_vial": "decision de Acta 1.4 -- no existe dato de red vial en el repo (verificado por grep de tags highway/footway/sidewalk sobre pipeline/data/, 0 resultados)",
        "distancias_por_zona_m": distancias_por_zona,
        "scores": scores,
    }

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_SALIDA.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Escrito: {RUTA_SALIDA}")
    for zona in ZONAS_REALES:
        print(
            f"  {zona}: distancia_promedio_m={promedios[zona]:.1f} score={scores[zona]:.4f}"
        )


if __name__ == "__main__":
    main()
