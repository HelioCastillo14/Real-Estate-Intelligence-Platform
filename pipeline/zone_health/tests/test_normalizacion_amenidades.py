#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para Feature 1.4.3 -- densidad de amenidades ponderada por categoria."""

import unittest

from pipeline.zone_health.normalizacion_amenidades import (
    CATEGORIAS,
    PESOS,
    ZONAS_REALES,
    _cargar_conteos_por_zona,
    calcular_conteo_ponderado,
    normalizar_amenidades,
)

# Caso de regresion verificado manualmente contra el archivo real de Pedregal
# (amenidades_pedregal_osm.geojson): colegio=4, parque=3, supermercado=2,
# clinica=2, farmacia=1, hospital=0 -> salud = clinica + hospital = 2.
CONTEO_PEDREGAL = {
    "colegio": 4,
    "parque": 3,
    "supermercado": 2,
    "farmacia": 1,
    "salud": 2,
}

CONTEO_PONDERADO_PEDREGAL_ESPERADO = 2.3527

CONTEOS_PONDERADOS_DE_PRUEBA = {
    "Bella Vista": 5.0,
    "Betania": 20.0,
    "Parque Lefevre": 11.0,
    "Pedregal": 2.3527,
    "San Francisco": 6.35,
}


class TestCalcularConteoPonderado(unittest.TestCase):
    def test_pedregal_coincide_con_caso_verificado_manualmente(self):
        conteo = calcular_conteo_ponderado(CONTEO_PEDREGAL)
        self.assertAlmostEqual(conteo, CONTEO_PONDERADO_PEDREGAL_ESPERADO, places=4)

    def test_zona_sin_amenidades_da_conteo_cero(self):
        conteo_vacio = {cat: 0 for cat in CATEGORIAS}
        self.assertEqual(calcular_conteo_ponderado(conteo_vacio), 0.0)

    def test_pesos_suman_aproximadamente_uno(self):
        # Los pesos son valores fijos ya decididos (no se recalculan aqui);
        # suman 0.9999, no 1.0 exacto, por redondeo en la fuente (Encuesta
        # SS2.3). places=3 tolera ese redondeo sin ocultar un error real.
        self.assertAlmostEqual(sum(PESOS.values()), 1.0, places=3)


class TestNormalizarAmenidades(unittest.TestCase):
    def setUp(self):
        self.scores = normalizar_amenidades(CONTEOS_PONDERADOS_DE_PRUEBA)

    def test_devuelve_las_5_zonas(self):
        self.assertEqual(set(self.scores.keys()), set(ZONAS_REALES))

    def test_todos_los_scores_en_rango_0_1(self):
        for zona, score in self.scores.items():
            self.assertGreaterEqual(score, 0.0, msg=zona)
            self.assertLessEqual(score, 1.0, msg=zona)

    def test_betania_mayor_conteo_ponderado_obtiene_score_maximo(self):
        zona_mejor_score = max(self.scores, key=self.scores.get)
        self.assertEqual(zona_mejor_score, "Betania")
        self.assertEqual(self.scores["Betania"], 1.0)

    def test_pedregal_menor_conteo_ponderado_obtiene_score_minimo(self):
        zona_peor_score = min(self.scores, key=self.scores.get)
        self.assertEqual(zona_peor_score, "Pedregal")
        self.assertEqual(self.scores["Pedregal"], 0.0)


class TestConteoDesdeArchivosReales(unittest.TestCase):
    """Ejercita _cargar_conteos_por_zona contra los archivos reales
    (Google Places + OSM, ya corregidos de los sesgos documentados en
    LOG_EXTRACCION.md), verificando el conteo crudo exacto por categoria
    antes de ponderar y normalizar.
    """

    @classmethod
    def setUpClass(cls):
        cls.conteos = _cargar_conteos_por_zona()

    def test_solo_las_5_zonas_reales(self):
        self.assertEqual(set(self.conteos.keys()), set(ZONAS_REALES))

    def test_cada_zona_tiene_las_5_categorias(self):
        for zona in ZONAS_REALES:
            self.assertEqual(set(self.conteos[zona].keys()), set(CATEGORIAS), msg=zona)

    def test_pedregal_coincide_con_caso_verificado_manualmente(self):
        self.assertEqual(self.conteos["Pedregal"], CONTEO_PEDREGAL)
        conteo_ponderado = calcular_conteo_ponderado(self.conteos["Pedregal"])
        self.assertAlmostEqual(conteo_ponderado, CONTEO_PONDERADO_PEDREGAL_ESPERADO, places=4)

    def test_bella_vista_hospital_ya_no_esta_en_cero(self):
        """Regresion del sesgo documentado en LOG_EXTRACCION.md 2026-07-09:
        Bella Vista tenia hospital=0 en la extraccion original de Google
        Places. Tras la correccion, salud (clinica+hospital) debe ser >= 2
        (1 clinica original + 1 hospital agregado)."""
        self.assertGreaterEqual(self.conteos["Bella Vista"]["salud"], 2)

    def test_betania_no_tiene_categorias_en_cero(self):
        """Regresion del hueco de cobertura espacial documentado en
        LOG_EXTRACCION.md 2026-07-09: el archivo OSM original de Betania
        tenia 3 de 5 categorias en cero por un bbox de consulta truncado.
        Tras re-extraer con el bbox completo del poligono real, ninguna
        categoria deberia quedar en cero."""
        for cat, conteo in self.conteos["Betania"].items():
            self.assertGreater(conteo, 0, msg=cat)

    def test_scores_del_archivo_real_coinciden_con_los_ya_aprobados(self):
        conteos_ponderados = {
            zona: calcular_conteo_ponderado(self.conteos[zona]) for zona in ZONAS_REALES
        }
        self.assertAlmostEqual(
            conteos_ponderados["Pedregal"], CONTEO_PONDERADO_PEDREGAL_ESPERADO, places=4
        )
        scores = normalizar_amenidades(conteos_ponderados)
        zona_mejor_score = max(scores, key=scores.get)
        zona_peor_score = min(scores, key=scores.get)
        self.assertEqual(scores[zona_mejor_score], 1.0)
        self.assertEqual(scores[zona_peor_score], 0.0)


if __name__ == "__main__":
    unittest.main()
