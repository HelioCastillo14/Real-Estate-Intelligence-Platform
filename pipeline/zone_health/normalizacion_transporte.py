#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizacion_transporte.py
=============================
Feature 1.4.2 -- Normalizacion de la variable de densidad de transporte
a escala 0-1 por corregimiento, para el Zone Health Composite Index
(peso 0.20).

SOLO cubre las 5 zonas con corregimiento administrativo real:
Bella Vista, Betania, Parque Lefevre, Pedregal, San Francisco.
El Cangrejo, Marbella, Obarrio (heredan de Bella Vista) y Costa del Este
(sin herencia, sin score compuesto) NO se tocan aqui -- que feature exacta
resuelve su herencia/visualizacion no esta confirmado en este repo. (Una
version previa de este docstring decia "Feature 1.4.6"; ese numero resulto
ser invencion propagada sin verificar entre los scripts de zone_health --
ver auditoria en pipeline/data/external/amenidades/LOG_EXTRACCION.md,
seccion "Correccion de referencia de feature", 2026-07-09.)

FUENTES DE DATOS:
  `pipeline/data/external/metro/metro_estaciones_final_30.jsonl` -- 30
  estaciones de metro con `corregimiento_id` ya poblado (null para las
  estaciones fuera del scope de 9 zonas).
  `pipeline/data/external/gtfs/paradas_mibus_gtfs.jsonl` -- 1,150 paradas
  de MiBus con `corregimiento_id` ya poblado (null para paradas fuera del
  scope).
  `pipeline/data/external/seguridad/seguridad_homicidios_2023.jsonl` --
  fuente de CONVENIENCIA para `superficie_km2` por zona (ya se cargaba en
  1.4.1 para el calculo de `tasa_por_100k`). NO es la fuente autoritativa
  del area real de cada poligono -- hay una auditoria pendiente (ver
  CLAUDE.md) sobre si este valor coincide con el calculo real del
  poligono en PostGIS. Aqui se usa tal cual existe, sin resolver esa
  auditoria.
"""

import json
from pathlib import Path

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

RUTA_GTFS = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "external"
    / "gtfs"
    / "paradas_mibus_gtfs.jsonl"
)

RUTA_SUPERFICIE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "external"
    / "seguridad"
    / "seguridad_homicidios_2023.jsonl"
)

RUTA_SALIDA = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "zone_health_transporte_1_4_2.json"
)


def normalizar_transporte(densidades: dict[str, float]) -> dict[str, float]:
    """Normaliza densidad de transporte (puntos/km2) a score_transporte en [0,1].

    Formula: score = (x - min) / (max - min)

    Sin inversion: mas densidad de transporte es mejor, por lo que la zona
    con mayor densidad obtiene 1.0 y la de menor densidad obtiene 0.0.

    Limitacion conocida (ponderacion igual metro/bus, decision formal 1.4.2):
    el conteo de puntos de transporte suma paradas de MiBus y estaciones de
    metro sin ponderar por tipo. Esto subestima la calidad real de
    transporte en zonas con metro, ya que una estacion de metro mueve
    ordenes de magnitud mas pasajeros y tiene mayor impacto en movilidad
    que una parada de bus individual -- pero ambas cuentan como "1 punto"
    en este conteo. Es un riesgo aceptado, no un bug, con el mismo
    tratamiento que la limitacion de n=5 documentada en
    normalizacion_seguridad.py (Feature 1.4.1): se documenta aqui para que
    quien consuma este score (Zone Health Composite Index)
    no lo trate como una medida completa de calidad de transporte.

    Args:
        densidades: dict corregimiento -> densidad de transporte
            (conteo total de puntos / superficie_km2). Debe contener
            unicamente las 5 zonas reales listadas en ZONAS_REALES.

    Returns:
        dict corregimiento -> score_transporte, cada valor en [0,1].
    """
    valores = list(densidades.values())
    minimo, maximo = min(valores), max(valores)
    return {
        zona: (x - minimo) / (maximo - minimo)
        for zona, x in densidades.items()
    }


def _contar_puntos_transporte(ruta_metro: Path, ruta_gtfs: Path) -> dict[str, int]:
    """Cuenta paradas GTFS + estaciones de metro por zona (sin ponderar).

    Filtra explicitamente por ZONAS_REALES -- las filas con
    corregimiento_id null (fuera del scope de 9 zonas) o correspondientes
    a las 4 zonas de herencia/exclusion se descartan.
    """
    conteos = {zona: 0 for zona in ZONAS_REALES}
    for ruta in (ruta_metro, ruta_gtfs):
        with ruta.open(encoding="utf-8") as f:
            for linea in f:
                registro = json.loads(linea)
                zona = registro.get("corregimiento_id")
                if zona in conteos:
                    conteos[zona] += 1
    return conteos


def _cargar_superficies_desde_jsonl(ruta: Path) -> dict[str, float]:
    superficies = {}
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            registro = json.loads(linea)
            zona = registro["corregimiento"]
            if zona in ZONAS_REALES and registro.get("superficie_km2") is not None:
                superficies[zona] = registro["superficie_km2"]
    faltantes = set(ZONAS_REALES) - superficies.keys()
    if faltantes:
        raise ValueError(
            f"Faltan superficie_km2 para: {sorted(faltantes)} en {ruta}"
        )
    return superficies


def main() -> None:
    conteos = _contar_puntos_transporte(RUTA_METRO, RUTA_GTFS)
    superficies = _cargar_superficies_desde_jsonl(RUTA_SUPERFICIE)

    densidades = {
        zona: conteos[zona] / superficies[zona] for zona in ZONAS_REALES
    }
    scores = normalizar_transporte(densidades)

    salida = {
        "feature": "1.4.2",
        "dimension": "transporte",
        "peso_zone_health": 0.20,
        "metodo": "min-max sin inversion: (x - min) / (max - min)",
        "conteo_puntos_transporte": conteos,
        "densidades_por_km2": densidades,
        "fuente_conteo_metro": str(
            RUTA_METRO.relative_to(Path(__file__).resolve().parents[2])
        ),
        "fuente_conteo_gtfs": str(
            RUTA_GTFS.relative_to(Path(__file__).resolve().parents[2])
        ),
        "fuente_superficie": str(
            RUTA_SUPERFICIE.relative_to(Path(__file__).resolve().parents[2])
        ),
        "scores": scores,
    }

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_SALIDA.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Escrito: {RUTA_SALIDA}")
    for zona, score in scores.items():
        print(f"  {zona}: {score:.4f}")


if __name__ == "__main__":
    main()
