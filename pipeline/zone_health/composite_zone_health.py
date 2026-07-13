#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
composite_zone_health.py
==========================
Feature 1.4.6 -- Formula ponderada final del Zone Health Composite Index,
con herencia. Ultima tarea de computo de Feature 1.4 antes de la revision
cualitativa (1.4.7).

INSUMOS (los 4 outputs de 1.4.1-1.4.4, ya generados y aprobados -- este
modulo NO recalcula ninguna dimension, solo las combina):
  `pipeline/data/processed/zone_health_seguridad_1_4_1.json`
  `pipeline/data/processed/zone_health_transporte_1_4_2.json`
  `pipeline/data/processed/zone_health_amenidades_1_4_3.json`
  `pipeline/data/processed/zone_health_walkability_1_4_4.json`

PESOS (4 dimensiones -- socioeconomico eliminado en Feature 1.4.5,
redistribucion documentada en el Acta de 1.4; deben sumar exactamente 1.0,
verificado con test explicito):
  seguridad:    0.352941176
  transporte:   0.235294118
  amenidades:   0.235294118
  walkability:  0.176470588

FORMULA (5 zonas reales):
  composite_zona = sum(peso_dimension * score_dimension) para las 4
  dimensiones. NO se renormaliza el resultado -- ya cae en [0,1] porque
  los 4 componentes estan en [0,1] y los pesos suman 1.0.

HERENCIA (El Cangrejo, Marbella, Obarrio -- decision ya cerrada, CLAUDE.md):
  reciben una COPIA LITERAL del composite y del desglose de las 4
  dimensiones de Bella Vista. No es un promedio ni un ajuste -- mismo
  valor, campo por campo. Se marca con `hereda_de: "Bella Vista"`.

COSTA DEL ESTE (decision #2, CLAUDE.md / Acta 1.4): sin composite, sin
desglose (`null` en ambos). 4 de 5 dimensiones no tienen insumo propio
(dependian de Juan Diaz, nunca extraido por estar fuera del scope de las
9 zonas). `estado_zone_health: "sin_score_datos_insuficientes"`.

PEDREGAL (decision #1, CLAUDE.md / Acta 1.3.7 SS6): SI se calcula el
composite y entra con su desglose completo -- la exclusion es solo de la
VISUALIZACION activa (amenidades debiles, 12 POIs vs. 32-52 promedio en
el resto de zonas), no del computo del indice. Se marca con
`estado_visualizacion: "no_visualizado"`, que coexiste con un composite
numerico real -- es una bandera para Feature 5.x, no una exclusion.
"""

import json
import math
from pathlib import Path

ZONAS_REALES = [
    "Bella Vista",
    "Betania",
    "Parque Lefevre",
    "Pedregal",
    "San Francisco",
]

DIMENSIONES = ["seguridad", "transporte", "amenidades", "walkability"]

PESOS = {
    "seguridad": 0.352941176,
    "transporte": 0.235294118,
    "amenidades": 0.235294118,
    "walkability": 0.176470588,
}

ZONAS_HERENCIA = {
    "El Cangrejo": "Bella Vista",
    "Marbella": "Bella Vista",
    "Obarrio": "Bella Vista",
}

ZONA_SIN_SCORE = "Costa del Este"
MOTIVO_SIN_SCORE = (
    "4 de 5 dimensiones sin insumo propio (dependian de Juan Diaz, nunca "
    "extraido por estar fuera del scope de las 9 zonas) -- CLAUDE.md, "
    "decision #2 / Acta de Feature 1.4"
)

ZONA_NO_VISUALIZADA = "Pedregal"
MOTIVO_NO_VISUALIZADO = (
    "amenidades debiles (12 POIs vs. 32-52 promedio del resto de zonas) "
    "-- Acta 1.3.7 SS6; se calcula, no se muestra en la visualizacion "
    "activa (pendiente validacion con consejo academico)"
)

RUTA_PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

RUTA_ENTRADA_DIMENSION = {
    "seguridad": RUTA_PROCESSED / "zone_health_seguridad_1_4_1.json",
    "transporte": RUTA_PROCESSED / "zone_health_transporte_1_4_2.json",
    "amenidades": RUTA_PROCESSED / "zone_health_amenidades_1_4_3.json",
    "walkability": RUTA_PROCESSED / "zone_health_walkability_1_4_4.json",
}

RUTA_SALIDA = RUTA_PROCESSED / "zone_health_composite_1_4_6.json"


def calcular_composite(desglose: dict[str, float]) -> float:
    """Composite ponderado de una zona a partir de sus 4 scores de dimension.

    Formula: composite = sum(PESOS[dim] * desglose[dim]) para dim en
    DIMENSIONES. Sin renormalizar -- valido en [0,1] porque cada
    score de dimension ya esta en [0,1] y sum(PESOS.values()) == 1.0.

    Args:
        desglose: dict con las 4 claves de DIMENSIONES -> score en [0,1].

    Returns:
        composite_zona (float, en [0,1]).
    """
    return sum(PESOS[dim] * desglose[dim] for dim in DIMENSIONES)


def _cargar_desgloses_zonas_reales() -> dict[str, dict[str, float]]:
    """Lee los 4 JSON de dimension ya aprobados y arma, por zona real,
    el desglose {seguridad, transporte, amenidades, walkability} -> score.
    """
    scores_por_dimension = {}
    for dimension, ruta in RUTA_ENTRADA_DIMENSION.items():
        with ruta.open(encoding="utf-8") as f:
            contenido = json.load(f)
        scores_por_dimension[dimension] = contenido["scores"]

    desgloses = {}
    for zona in ZONAS_REALES:
        desgloses[zona] = {
            dimension: scores_por_dimension[dimension][zona]
            for dimension in DIMENSIONES
        }
    return desgloses


def construir_composite_zone_health(
    desgloses_zonas_reales: dict[str, dict[str, float]],
) -> dict[str, dict]:
    """Arma el registro de las 9 zonas del scope: 5 reales calculadas, 3
    heredadas de Bella Vista (copia literal), 1 sin score (Costa del Este).

    Args:
        desgloses_zonas_reales: dict zona_real -> desglose de las 4
            dimensiones (score en [0,1] cada una). Debe contener
            exactamente las 5 zonas de ZONAS_REALES.

    Returns:
        dict zona -> registro con nombre, composite, desglose,
        estado_zone_health, y (segun corresponda) hereda_de /
        estado_visualizacion.
    """
    zonas = {}

    for zona in ZONAS_REALES:
        desglose = desgloses_zonas_reales[zona]
        registro = {
            "nombre": zona,
            "composite": calcular_composite(desglose),
            "desglose": dict(desglose),
            "estado_zone_health": "calculado",
        }
        if zona == ZONA_NO_VISUALIZADA:
            registro["estado_visualizacion"] = "no_visualizado"
            registro["motivo_visualizacion"] = MOTIVO_NO_VISUALIZADO
        zonas[zona] = registro

    desglose_bella_vista = zonas["Bella Vista"]["desglose"]
    composite_bella_vista = zonas["Bella Vista"]["composite"]
    for zona_heredera, zona_origen in ZONAS_HERENCIA.items():
        zonas[zona_heredera] = {
            "nombre": zona_heredera,
            "composite": composite_bella_vista,
            "desglose": dict(desglose_bella_vista),
            "estado_zone_health": "calculado",
            "hereda_de": zona_origen,
        }

    zonas[ZONA_SIN_SCORE] = {
        "nombre": ZONA_SIN_SCORE,
        "composite": None,
        "desglose": None,
        "estado_zone_health": "sin_score_datos_insuficientes",
        "motivo_estado": MOTIVO_SIN_SCORE,
    }

    return zonas


def main() -> None:
    suma_pesos = sum(PESOS.values())
    if not math.isclose(suma_pesos, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError(f"Los pesos deben sumar 1.0, suman {suma_pesos}")

    desgloses_zonas_reales = _cargar_desgloses_zonas_reales()
    zonas = construir_composite_zone_health(desgloses_zonas_reales)

    salida = {
        "feature": "1.4.6",
        "dimension": "composite",
        "pesos": PESOS,
        "metodo": "composite_zona = sum(peso_dimension * score_dimension), sin renormalizar",
        "zonas": zonas,
    }

    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA_SALIDA.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"Escrito: {RUTA_SALIDA}")
    for zona, registro in zonas.items():
        composite = registro["composite"]
        if composite is None:
            print(f"  {zona}: {registro['estado_zone_health']}")
        else:
            print(f"  {zona}: composite={composite:.4f} estado={registro['estado_zone_health']}")


if __name__ == "__main__":
    main()
