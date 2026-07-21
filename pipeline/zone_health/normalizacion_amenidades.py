#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizacion_amenidades.py
=============================
Feature 1.4.3 -- Densidad de amenidades ponderada por categoria, a escala
0-1 por corregimiento, para el Zone Health Composite Index (peso 0.20).

SOLO cubre las 5 zonas con corregimiento administrativo real:
Bella Vista, Betania, Parque Lefevre, Pedregal, San Francisco.
El Cangrejo, Marbella, Obarrio (heredan de Bella Vista) y Costa del Este
(sin herencia, sin score compuesto) NO se tocan aqui -- que feature exacta
resuelve su herencia/visualizacion no esta confirmado en este repo (ver
LOG_EXTRACCION.md, seccion "Correccion de referencia de feature": una
referencia previa a "Feature 1.4.6" en este mismo docstring resulto ser
un numero inventado que se propago sin verificar entre los 3 scripts de
zone_health -- no se repite ese error aqui). Pedregal SI se calcula -- su exclusion
es solo de la visualizacion activa (Feature 5.x, amenidades debiles: 12
POIs vs. 32-52 promedio), no del computo del indice.

TAXONOMIA (Acta 1.3.7 SS7): 5 categorias finales. `hospital` y `clinica`
se fusionan en una sola categoria `salud` -- ver auditoria de sesgo abajo
sobre por que esta fusion es necesaria, no solo conveniente.

PESOS (ya decididos, fuente Encuesta SS2.3 + decision de farmacia):
  supermercado: 0.3137
  parque:       0.2549
  salud:        0.2353
  colegio:      0.0980
  farmacia:     0.0980
Los primeros 4 pesos vienen directo de la Encuesta SS2.3 (importancia
percibida por categoria de amenidad). `farmacia` NO tiene dato empirico
propio en la encuesta -- se le asigno el mismo peso que `colegio` (0.0980)
por decision de equipo documentada en el Acta de Feature 1.4.3, no por
promediar ni interpolar desde otros datos.

AUDITORIA DE SESGO PREVIA AL CALCULO (ver LOG_EXTRACCION.md para el detalle
completo, ambas correcciones fechadas 2026-07-09):

1. Bella Vista, categoria `hospital`: la extraccion original de Google
   Places tenia hospital=0 mientras clinica=1 y el resto de categorias
   tenian volumen normal -- el mismo patron de busqueda-por-categoria
   incompleta ya documentado para Costa del Este (Acta 1.3.7 SS7). Se
   re-extrajo por investigacion manual (sin acceso a API de Google Places
   en esta sesion) y se verifico CADA candidato programaticamente contra
   el poligono real de Bella Vista con
   `cruce_espacial_corregimiento.asignar_corregimiento()`. De 2 candidatos
   iniciales, 1 (Hospital Nacional) cayo fuera del poligono (~470m al sur,
   zona de Calidonia) y se descarto; no se encontro un segundo hospital
   real dentro del poligono confirmado (Hospital Paitilla y Hospital San
   Fernando tambien caen fuera, en San Francisco y Pueblo Nuevo
   respectivamente -- geografia real, no sesgo de busqueda). Conteo final:
   hospital=1 en Bella Vista (`amenidades_bella_vista_google_places.jsonl`).

2. Betania, las 5 categorias: el archivo OSM original
   (`amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`) tenia un
   hueco de COBERTURA ESPACIAL, no de subcategoria -- su bounding box de
   consulta cubria solo ~26% de la extension norte-sur del poligono real
   de Betania, dando supermercado=0, farmacia=0, salud=0 (3 de 5 categorias
   en cero, cuando ninguna otra zona tiene ceros). Se re-extrajo via
   Overpass API acotado al bbox completo del poligono real de Betania, y
   se filtro cada elemento devuelto con `asignar_corregimiento()` (217
   elementos en el bbox, 104 confirmados dentro del poligono real). Este
   archivo dedicado y ya filtrado es `amenidades_betania_osm.geojson`.
   El archivo original combinado NO se toco (queda disponible para quien
   trabaje El Cangrejo/Marbella/Obarrio, feature exacta sin confirmar --
   ver LOG_EXTRACCION.md). Verificacion adicional (2026-07-09): de esas 3
   zonas de herencia, El Cangrejo no tiene problema de cobertura (100% de
   coincidencia contra Overpass fresco), Obarrio tiene un hueco parcial
   (100% de los parques ausentes), y Marbella no se pudo verificar por no
   tener un poligono de limite real disponible en OSM. Detalle completo en
   LOG_EXTRACCION.md.

FORMULA:
  1. conteo_ponderado_zona = suma( peso_categoria * conteo_categoria )
     para las 5 categorias.
  2. Normalizacion min-max SIN inversion:
     score = (x - min) / (max - min)
     Sin inversion porque mas amenidades ponderadas es mejor -- a
     diferencia de seguridad (1.4.1), donde una tasa alta es peor.

LIMITACION CONOCIDA (n=5, mismo tratamiento que 1.4.1/1.4.2): min-max sobre
una muestra de 5 zonas es sensible a outliers y se recalcula por completo si
se agrega o quita una zona. Se documenta aqui para que quien consuma este
score en el Zone Health Composite Index no lo trate como una escala absoluta.

FUENTES DE DATOS:
  Google Places (categoria ya viene como campo `categoria` en el JSONL,
  valores `hospital`/`clinica` se fusionan aqui a `salud`):
    `pipeline/data/external/amenidades/amenidades_san_francisco_google_places.jsonl`
    `pipeline/data/external/amenidades/amenidades_bella_vista_google_places.jsonl`
  OSM (tags `amenity`/`shop`/`leisure`, sin columna `categoria` uniforme --
  se clasifica aqui con MAPA_TAGS_OSM; cada feature se re-verifica con
  `asignar_corregimiento()` antes de contar, no se asume que "estar en el
  archivo de la zona X" sea suficiente):
    `pipeline/data/external/amenidades/amenidades_betania_osm.geojson`
    `pipeline/data/external/amenidades/amenidades_parque_lefevre_osm.geojson`
    `pipeline/data/external/amenidades/amenidades_pedregal_osm.geojson`
"""

import json
import sys
from pathlib import Path

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cruce_espacial_corregimiento import cargar_poligonos, asignar_corregimiento  # noqa: E402

ZONAS_REALES = [
    "Bella Vista",
    "Betania",
    "Parque Lefevre",
    "Pedregal",
    "San Francisco",
]

CATEGORIAS = ["supermercado", "farmacia", "salud", "parque", "colegio"]

PESOS = {
    "supermercado": 0.3137,
    "parque": 0.2549,
    "salud": 0.2353,
    "colegio": 0.0980,
    "farmacia": 0.0980,
}

# categoria original del JSONL de Google Places -> categoria de la taxonomia
MAPA_CATEGORIA_GOOGLE_PLACES = {
    "supermercado": "supermercado",
    "farmacia": "farmacia",
    "clinica": "salud",
    "hospital": "salud",
    "parque": "parque",
    "colegio": "colegio",
}

# (tag OSM, valor) -> categoria de la taxonomia
MAPA_TAGS_OSM = {
    ("shop", "supermarket"): "supermercado",
    ("leisure", "park"): "parque",
    ("amenity", "pharmacy"): "farmacia",
    ("amenity", "school"): "colegio",
    ("amenity", "clinic"): "salud",
    ("amenity", "hospital"): "salud",
}

RUTA_AMENIDADES = Path(__file__).resolve().parents[1] / "data" / "external" / "amenidades"

RUTA_GOOGLE_PLACES = {
    "Bella Vista": RUTA_AMENIDADES / "amenidades_bella_vista_google_places.jsonl",
    "San Francisco": RUTA_AMENIDADES / "amenidades_san_francisco_google_places.jsonl",
}

RUTA_OSM = {
    "Betania": RUTA_AMENIDADES / "amenidades_betania_osm.geojson",
    "Parque Lefevre": RUTA_AMENIDADES / "amenidades_parque_lefevre_osm.geojson",
    "Pedregal": RUTA_AMENIDADES / "amenidades_pedregal_osm.geojson",
}

RUTA_SALIDA = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "zone_health_amenidades_1_4_3.json"
)


def calcular_conteo_ponderado(conteo_categorias: dict[str, int]) -> float:
    """Calcula el conteo ponderado de una zona: suma(peso * conteo) por categoria.

    Args:
        conteo_categorias: dict categoria -> conteo, debe tener exactamente
            las 5 claves de CATEGORIAS.

    Returns:
        conteo_ponderado_zona (float, sin normalizar).
    """
    return sum(PESOS[cat] * conteo_categorias.get(cat, 0) for cat in CATEGORIAS)


def normalizar_amenidades(conteos_ponderados: dict[str, float]) -> dict[str, float]:
    """Normaliza conteo_ponderado_zona a score_amenidades en [0,1].

    Formula: score = (x - min) / (max - min)

    Sin inversion: mas amenidades ponderadas es mejor, por lo que la zona
    con mayor conteo ponderado obtiene 1.0 y la de menor conteo obtiene 0.0.

    Args:
        conteos_ponderados: dict corregimiento -> conteo_ponderado_zona.
            Debe contener unicamente las 5 zonas reales listadas en
            ZONAS_REALES.

    Returns:
        dict corregimiento -> score_amenidades, cada valor en [0,1].
    """
    valores = list(conteos_ponderados.values())
    minimo, maximo = min(valores), max(valores)
    return {
        zona: (x - minimo) / (maximo - minimo)
        for zona, x in conteos_ponderados.items()
    }


def _contar_google_places(ruta: Path) -> dict[str, int]:
    conteo = {cat: 0 for cat in CATEGORIAS}
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            registro = json.loads(linea)
            cat = MAPA_CATEGORIA_GOOGLE_PLACES.get(registro["categoria"])
            if cat is not None:
                conteo[cat] += 1
    return conteo


def _contar_osm(ruta: Path, zona_esperada: str, poligonos: dict) -> dict[str, int]:
    """Cuenta features OSM por categoria, re-verificando cada punto contra el
    poligono real de `zona_esperada` -- no asume que "estar en el archivo de
    la zona X" sea suficiente (ver auditoria de Betania en el docstring del
    modulo: el archivo original de Betania estaba mal recortado).
    """
    conteo = {cat: 0 for cat in CATEGORIAS}
    with ruta.open(encoding="utf-8") as f:
        geojson = json.load(f)

    for feature in geojson["features"]:
        props = feature.get("properties", {})
        cat = None
        for tag in ("shop", "leisure", "amenity"):
            if tag in props and (tag, props[tag]) in MAPA_TAGS_OSM:
                cat = MAPA_TAGS_OSM[(tag, props[tag])]
                break
        if cat is None:
            continue

        punto = shape(feature["geometry"]).centroid
        zona = asignar_corregimiento(punto.y, punto.x, poligonos)
        if zona == zona_esperada:
            conteo[cat] += 1

    return conteo


def _cargar_conteos_por_zona() -> dict[str, dict[str, int]]:
    poligonos = cargar_poligonos()
    conteos = {}

    for zona, ruta in RUTA_GOOGLE_PLACES.items():
        conteos[zona] = _contar_google_places(ruta)

    for zona, ruta in RUTA_OSM.items():
        conteos[zona] = _contar_osm(ruta, zona, poligonos)

    faltantes = set(ZONAS_REALES) - conteos.keys()
    if faltantes:
        raise ValueError(f"Faltan conteos de amenidades para: {sorted(faltantes)}")

    return conteos


def main() -> None:
    conteos_por_categoria = _cargar_conteos_por_zona()
    conteos_ponderados = {
        zona: calcular_conteo_ponderado(conteos_por_categoria[zona])
        for zona in ZONAS_REALES
    }
    scores = normalizar_amenidades(conteos_ponderados)

    salida = {
        "feature": "1.4.3",
        "dimension": "amenidades",
        "peso_zone_health": 0.20,
        "metodo": "min-max sin inversion: (x - min) / (max - min)",
        "pesos_categoria": PESOS,
        "conteo_crudo_por_categoria": conteos_por_categoria,
        "conteo_ponderado": conteos_ponderados,
        "scores": scores,
        "correcciones_de_sesgo_aplicadas": {
            "bella_vista_hospital": "0 -> 1, ver LOG_EXTRACCION.md 2026-07-09",
            "betania_cobertura_espacial": "ver LOG_EXTRACCION.md 2026-07-09, archivo dedicado amenidades_betania_osm.geojson",
        },
    }

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_SALIDA.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Escrito: {RUTA_SALIDA}")
    for zona in ZONAS_REALES:
        print(f"  {zona}: conteo_ponderado={conteos_ponderados[zona]:.4f} score={scores[zona]:.4f}")


if __name__ == "__main__":
    main()
