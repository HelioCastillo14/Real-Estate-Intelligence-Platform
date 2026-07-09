#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para Feature 1.4.1 -- normalizacion de seguridad."""

import unittest

from pipeline.zone_health.normalizacion_seguridad import (
    RUTA_ENTRADA,
    _cargar_tasas_desde_jsonl,
    normalizar_seguridad,
)

TASAS_REALES = {
    "Bella Vista": 14.83,
    "Betania": 4.74,
    "Parque Lefevre": 21.01,
    "Pedregal": 15.60,
    "San Francisco": 3.26,
}

ZONAS_HERENCIA_O_EXCLUSION = ["El Cangrejo", "Marbella", "Obarrio", "Costa del Este"]


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


class TestCargaDesdeArchivoReal(unittest.TestCase):
    """Ejercita _cargar_tasas_desde_jsonl contra el archivo real de 9 filas
    (external/seguridad/seguridad_homicidios_2023.jsonl), donde 4 zonas traen
    tasa_por_100k: null. El codigo viejo nunca se probo contra nulls reales
    porque el archivo que leia antes no los tenia.
    """

    @classmethod
    def setUpClass(cls):
        cls.tasas = _cargar_tasas_desde_jsonl(RUTA_ENTRADA)
        cls.scores = normalizar_seguridad(cls.tasas)

    def test_zonas_de_herencia_o_exclusion_no_entran_al_calculo(self):
        for zona in ZONAS_HERENCIA_O_EXCLUSION:
            self.assertNotIn(zona, self.tasas, msg=f"{zona} no deberia tener tasa_por_100k cargada")
            self.assertNotIn(zona, self.scores, msg=f"{zona} no deberia aparecer en scores")

    def test_solo_las_5_zonas_reales_en_el_output(self):
        self.assertEqual(set(self.scores.keys()), set(TASAS_REALES.keys()))

    def test_scores_del_archivo_real_coinciden_con_los_ya_aprobados(self):
        esperados = {
            "San Francisco": 1.0,
            "Betania": 0.9166197183098591,
            "Bella Vista": 0.34816901408450707,
            "Pedregal": 0.3047887323943662,
            "Parque Lefevre": 0.0,
        }
        for zona, valor_esperado in esperados.items():
            self.assertEqual(self.scores[zona], valor_esperado, msg=zona)


if __name__ == "__main__":
    unittest.main()
