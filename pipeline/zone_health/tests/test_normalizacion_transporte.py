#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para Feature 1.4.2 -- normalizacion de densidad de transporte."""

import unittest

from pipeline.zone_health.normalizacion_transporte import (
    RUTA_GTFS,
    RUTA_METRO,
    RUTA_SUPERFICIE,
    ZONAS_REALES,
    _cargar_superficies_desde_jsonl,
    _contar_puntos_transporte,
    normalizar_transporte,
)

CONTEOS_ESPERADOS = {
    "Bella Vista": 46,
    "Betania": 62,
    "San Francisco": 49,
    "Parque Lefevre": 44,
    "Pedregal": 50,
}

SUPERFICIES_REALES = {
    "Bella Vista": 4.581,
    "Betania": 8.235,
    "Parque Lefevre": 7.231,
    "Pedregal": 28.535,
    "San Francisco": 6.655,
}

DENSIDADES_REALES = {
    zona: CONTEOS_ESPERADOS[zona] / SUPERFICIES_REALES[zona]
    for zona in ZONAS_REALES
}

ZONAS_HERENCIA_O_EXCLUSION = ["El Cangrejo", "Marbella", "Obarrio", "Costa del Este"]


class TestNormalizarTransporte(unittest.TestCase):
    def setUp(self):
        self.scores = normalizar_transporte(DENSIDADES_REALES)

    def test_devuelve_las_5_zonas(self):
        self.assertEqual(set(self.scores.keys()), set(ZONAS_REALES))

    def test_todos_los_scores_en_rango_0_1(self):
        for zona, score in self.scores.items():
            self.assertGreaterEqual(score, 0.0, msg=zona)
            self.assertLessEqual(score, 1.0, msg=zona)

    def test_bella_vista_mayor_densidad_obtiene_score_maximo(self):
        zona_mejor_score = max(self.scores, key=self.scores.get)
        self.assertEqual(zona_mejor_score, "Bella Vista")
        self.assertEqual(self.scores["Bella Vista"], 1.0)

    def test_pedregal_menor_densidad_obtiene_score_minimo(self):
        zona_peor_score = min(self.scores, key=self.scores.get)
        self.assertEqual(zona_peor_score, "Pedregal")
        self.assertEqual(self.scores["Pedregal"], 0.0)


class TestConteoDesdeArchivosReales(unittest.TestCase):
    """Ejercita _contar_puntos_transporte contra los archivos reales de
    metro (30 filas) y GTFS (1,150 filas), verificando el conteo total
    exacto por zona antes de normalizar.
    """

    @classmethod
    def setUpClass(cls):
        cls.conteos = _contar_puntos_transporte(RUTA_METRO, RUTA_GTFS)
        cls.superficies = _cargar_superficies_desde_jsonl(RUTA_SUPERFICIE)

    def test_conteo_total_por_zona_coincide_con_valores_exactos(self):
        for zona, conteo_esperado in CONTEOS_ESPERADOS.items():
            self.assertEqual(self.conteos[zona], conteo_esperado, msg=zona)

    def test_zonas_de_herencia_o_exclusion_no_entran_al_conteo(self):
        for zona in ZONAS_HERENCIA_O_EXCLUSION:
            self.assertNotIn(zona, self.conteos, msg=f"{zona} no deberia tener conteo cargado")

    def test_solo_las_5_zonas_reales_en_el_conteo(self):
        self.assertEqual(set(self.conteos.keys()), set(ZONAS_REALES))

    def test_scores_del_archivo_real_coinciden_con_los_ya_aprobados(self):
        densidades = {
            zona: self.conteos[zona] / self.superficies[zona] for zona in ZONAS_REALES
        }
        scores = normalizar_transporte(densidades)
        esperados = {
            "Bella Vista": 1.0,
            "Betania": 0.6968799466320995,
            "San Francisco": 0.6768593855648877,
            "Parque Lefevre": 0.5226869132530912,
            "Pedregal": 0.0,
        }
        for zona, valor_esperado in esperados.items():
            self.assertAlmostEqual(scores[zona], valor_esperado, msg=zona)


if __name__ == "__main__":
    unittest.main()
