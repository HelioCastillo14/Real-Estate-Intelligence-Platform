#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalizacion_seguridad.py
===========================
Feature 1.4.1 -- Normalizacion de la variable de seguridad (SIEC) a escala 0-1
por corregimiento, para el Zone Health Composite Index (peso 0.30).

SOLO cubre las 5 zonas con corregimiento administrativo real y `tasa_por_100k`
propia: Bella Vista, Betania, Parque Lefevre, Pedregal, San Francisco.
El Cangrejo, Marbella, Obarrio (heredan de Bella Vista) y Costa del Este
(sin herencia, sin score compuesto) se resuelven en Feature 1.4.6 y
deliberadamente NO se tocan aqui.

FUENTE DE DATOS -- NOTA DE HIGIENE (sesion REIP, ver decision log 1.4.1):
  El archivo canonico `pipeline/data/External/SEIC/seguridad_homicidios_2023.jsonl`
  tiene `tasa_por_100k` en null para las 5 zonas -- el join con poblacion (INEC)
  que produce la tasa no se aplico ahi. Los valores ya computados (los que
  documenta CLAUDE.md: 14.83, 4.74, 21.01, 15.60, 3.26) viven en un archivo
  aparentemente mal archivado: `pipeline/data/External/INEC/seguridad_homicidios_2023 (1).jsonl`
  (carpeta INEC en vez de SEIC, sufijo "(1)" de una segunda descarga). Este modulo
  lee de ese archivo porque es la unica fuente con el computo ya hecho, pero el
  problema de archivado en si queda fuera del alcance de 1.4.1 -- pendiente de que
  el equipo lo revise en Feature 1.3.
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

RUTA_ENTRADA = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "External"
    / "INEC"
    / "seguridad_homicidios_2023 (1).jsonl"
)

RUTA_SALIDA = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "zone_health_seguridad_1_4_1.json"
)


def normalizar_seguridad(tasas_por_100k: dict[str, float]) -> dict[str, float]:
    """Normaliza tasa_por_100k a score_seguridad en [0,1] via min-max invertido.

    Formula: score = 1 - ((x - min) / (max - min))

    Por que se invierte: una tasa de homicidios alta significa una zona mas
    peligrosa, y eso debe traducirse en un score de seguridad BAJO. Sin la
    inversion, Parque Lefevre (la tasa mas alta, 21.01) terminaria con el
    score de seguridad mas alto -- exactamente al reves de lo que representa
    la dimension.

    Limitacion conocida (n=5, decision formal 1.4.1): min-max sobre una
    muestra tan pequeña es muy sensible a valores extremos. Parque Lefevre
    (21.01) esta muy por encima del resto del rango (3.26-15.60 en las otras
    4 zonas), por lo que domina el denominador (max - min) y comprime la
    escala relativa de las demas zonas hacia scores mas altos de lo que su
    posicion real ameritaria. Si en el futuro se agrega o quita una zona a
    este calculo, todos los scores cambian -- no solo el de la zona nueva --
    porque el rango completo se recalcula. Esto es un riesgo aceptado, no
    un bug: se documenta aqui para que quien consuma este score (Feature
    1.4.6, Zone Health Composite Index) no lo trate como una escala absoluta.

    Args:
        tasas_por_100k: dict corregimiento -> tasa_por_100k. Debe contener
            unicamente las 5 zonas reales listadas en ZONAS_REALES.

    Returns:
        dict corregimiento -> score_seguridad, cada valor en [0,1].
    """
    valores = list(tasas_por_100k.values())
    minimo, maximo = min(valores), max(valores)
    return {
        zona: 1 - ((x - minimo) / (maximo - minimo))
        for zona, x in tasas_por_100k.items()
    }


def _cargar_tasas_desde_jsonl(ruta: Path) -> dict[str, float]:
    tasas = {}
    with ruta.open(encoding="utf-8") as f:
        for linea in f:
            registro = json.loads(linea)
            zona = registro["corregimiento"]
            if zona in ZONAS_REALES and registro.get("tasa_por_100k") is not None:
                tasas[zona] = registro["tasa_por_100k"]
    faltantes = set(ZONAS_REALES) - tasas.keys()
    if faltantes:
        raise ValueError(
            f"Faltan tasa_por_100k para: {sorted(faltantes)} en {ruta}"
        )
    return tasas


def main() -> None:
    tasas = _cargar_tasas_desde_jsonl(RUTA_ENTRADA)
    scores = normalizar_seguridad(tasas)

    salida = {
        "feature": "1.4.1",
        "dimension": "seguridad",
        "peso_zone_health": 0.30,
        "metodo": "min-max invertido: 1 - ((x - min) / (max - min))",
        "fuente_tasas": str(RUTA_ENTRADA.relative_to(Path(__file__).resolve().parents[2])),
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
