#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para Feature 1.4.6 -- composite ponderado del Zone Health Index,
con herencia."""

import math
import unittest

from pipeline.zone_health.composite_zone_health import (
    PESOS,
    ZONAS_HERENCIA,
    ZONAS_REALES,
    ZONA_SIN_SCORE,
    calcular_composite,
    construir_composite_zone_health,
)

DESGLOSES_REALES = {
    "Bella Vista": {
        "seguridad": 0.34816901408450707,
        "transporte": 1.0,
        "amenidades": 0.033175729809634506,
        "walkability": 1.0,
    },
    "Betania": {
        "seguridad": 0.9166197183098591,
        "transporte": 0.6968799466320995,
        "amenidades": 1.0,
        "walkability": 0.8812049608553879,
    },
    "Parque Lefevre": {
        "seguridad": 0.0,
        "transporte": 0.5226869132530912,
        "amenidades": 0.50000564213092,
        "walkability": 0.751992546594915,
    },
    "Pedregal": {
        "seguridad": 0.3047887323943662,
        "transporte": 0.0,
        "amenidades": 0.0,
        "walkability": 0.0,
    },
    "San Francisco": {
        "seguridad": 1.0,
        "transporte": 0.6768593855648877,
        "amenidades": 0.22565702614563465,
        "walkability": 0.788497572772022,
    },
}


class TestPesos(unittest.TestCase):
    def test_pesos_suman_exactamente_uno(self):
        self.assertTrue(math.isclose(sum(PESOS.values()), 1.0, rel_tol=1e-9, abs_tol=1e-9))


class TestCalcularComposite(unittest.TestCase):
    def test_betania_composite_regresion_exacta(self):
        composite = calcular_composite(DESGLOSES_REALES["Betania"])
        self.assertAlmostEqual(composite, 0.8783, places=3)

    def test_composites_de_las_5_zonas_reales_en_rango_0_1(self):
        for zona in ZONAS_REALES:
            composite = calcular_composite(DESGLOSES_REALES[zona])
            self.assertGreaterEqual(composite, 0.0, msg=zona)
            self.assertLessEqual(composite, 1.0, msg=zona)


class TestConstruirCompositeZoneHealth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zonas = construir_composite_zone_health(DESGLOSES_REALES)

    def test_las_9_zonas_del_scope_presentes(self):
        esperadas = set(ZONAS_REALES) | set(ZONAS_HERENCIA.keys()) | {ZONA_SIN_SCORE}
        self.assertEqual(set(self.zonas.keys()), esperadas)

    def test_zonas_heredadas_identicas_a_bella_vista_campo_por_campo(self):
        bella_vista = self.zonas["Bella Vista"]
        for zona_heredera, zona_origen in ZONAS_HERENCIA.items():
            with self.subTest(zona=zona_heredera):
                registro = self.zonas[zona_heredera]
                self.assertEqual(zona_origen, "Bella Vista")
                self.assertEqual(registro["composite"], bella_vista["composite"])
                self.assertEqual(registro["desglose"], bella_vista["desglose"])
                self.assertEqual(registro["hereda_de"], "Bella Vista")

    def test_costa_del_este_sin_composite_ni_desglose(self):
        registro = self.zonas[ZONA_SIN_SCORE]
        self.assertIsNone(registro["composite"])
        self.assertIsNone(registro["desglose"])
        self.assertEqual(registro["estado_zone_health"], "sin_score_datos_insuficientes")

    def test_pedregal_tiene_composite_y_no_visualizado_a_la_vez(self):
        registro = self.zonas["Pedregal"]
        self.assertIsNotNone(registro["composite"])
        self.assertIsNotNone(registro["desglose"])
        self.assertEqual(registro["estado_visualizacion"], "no_visualizado")
        self.assertAlmostEqual(registro["composite"], 0.1076, places=3)


if __name__ == "__main__":
    unittest.main()
