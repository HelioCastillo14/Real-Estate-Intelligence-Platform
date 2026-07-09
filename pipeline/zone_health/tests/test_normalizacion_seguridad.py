#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para Feature 1.4.1 -- normalizacion de seguridad."""

import unittest

from pipeline.zone_health.normalizacion_seguridad import normalizar_seguridad

TASAS_REALES = {
    "Bella Vista": 14.83,
    "Betania": 4.74,
    "Parque Lefevre": 21.01,
    "Pedregal": 15.60,
    "San Francisco": 3.26,
}


class TestNormalizarSeguridad(unittest.TestCase):
    def setUp(self):
        self.scores = normalizar_seguridad(TASAS_REALES)

    def test_devuelve_las_5_zonas(self):
        self.assertEqual(set(self.scores.keys()), set(TASAS_REALES.keys()))

    def test_todos_los_scores_en_rango_0_1(self):
        for zona, score in self.scores.items():
            self.assertGreaterEqual(score, 0.0, msg=zona)
            self.assertLessEqual(score, 1.0, msg=zona)

    def test_san_francisco_tasa_mas_baja_obtiene_score_mas_alto(self):
        zona_mejor_score = max(self.scores, key=self.scores.get)
        self.assertEqual(zona_mejor_score, "San Francisco")
        self.assertEqual(self.scores["San Francisco"], 1.0)

    def test_parque_lefevre_tasa_mas_alta_obtiene_score_cero_exacto(self):
        zona_peor_score = min(self.scores, key=self.scores.get)
        self.assertEqual(zona_peor_score, "Parque Lefevre")
        self.assertEqual(self.scores["Parque Lefevre"], 0.0)


if __name__ == "__main__":
    unittest.main()
