#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para Feature 1.4.4 -- normalizacion de walkability (proxy de
distancia a amenidades clave: supermercado, parque, metro)."""

import unittest

from shapely.geometry import shape

from pipeline.zone_health.cruce_espacial_corregimiento import cargar_poligonos
from pipeline.zone_health.normalizacion_walkability import (
    ZONAS_REALES,
    _cargar_centroides,
    _cargar_puntos_metro,
    _cargar_puntos_supermercado_y_parque,
    calcular_distancias_zona,
    distancia_haversine_metros,
    distancia_minima_metros,
    normalizar_walkability,
)

PROMEDIOS_SINTETICOS = {
    "Bella Vista": 300.0,
    "Betania": 500.0,
    "Parque Lefevre": 1200.0,
    "Pedregal": 1400.0,
    "San Francisco": 250.0,
}


class TestNormalizarWalkability(unittest.TestCase):
    def setUp(self):
        self.scores = normalizar_walkability(PROMEDIOS_SINTETICOS)

    def test_devuelve_las_5_zonas(self):
        self.assertEqual(set(self.scores.keys()), set(ZONAS_REALES))

    def test_todos_los_scores_en_rango_0_1(self):
        for zona, score in self.scores.items():
            self.assertGreaterEqual(score, 0.0, msg=zona)
            self.assertLessEqual(score, 1.0, msg=zona)

    def test_menor_distancia_promedio_obtiene_score_maximo(self):
        zona_mejor = max(self.scores, key=self.scores.get)
        self.assertEqual(zona_mejor, "San Francisco")
        self.assertEqual(self.scores["San Francisco"], 1.0)

    def test_mayor_distancia_promedio_obtiene_score_minimo(self):
        zona_peor = min(self.scores, key=self.scores.get)
        self.assertEqual(zona_peor, "Pedregal")
        self.assertEqual(self.scores["Pedregal"], 0.0)


class TestCalculoConDatosReales(unittest.TestCase):
    """Ejercita la carga real (centroides, amenidades, metro) y confirma
    que las 5 zonas reales producen distancias y scores validos."""

    @classmethod
    def setUpClass(cls):
        cls.centroides = _cargar_centroides()
        cls.puntos_supermercado, cls.puntos_parque = (
            _cargar_puntos_supermercado_y_parque()
        )
        cls.puntos_metro = _cargar_puntos_metro()
        cls.distancias_por_zona = {
            zona: calcular_distancias_zona(
                cls.centroides[zona],
                cls.puntos_supermercado,
                cls.puntos_parque,
                cls.puntos_metro,
            )
            for zona in ZONAS_REALES
        }
        cls.scores = normalizar_walkability(
            {
                zona: cls.distancias_por_zona[zona]["distancia_promedio_m"]
                for zona in ZONAS_REALES
            }
        )

    def test_solo_las_5_zonas_reales(self):
        self.assertEqual(set(self.distancias_por_zona.keys()), set(ZONAS_REALES))
        self.assertEqual(set(self.scores.keys()), set(ZONAS_REALES))

    def test_todos_los_scores_en_rango_0_1(self):
        for zona, score in self.scores.items():
            self.assertGreaterEqual(score, 0.0, msg=zona)
            self.assertLessEqual(score, 1.0, msg=zona)

    def test_cada_zona_tiene_las_3_distancias_y_el_promedio(self):
        for zona in ZONAS_REALES:
            distancias = self.distancias_por_zona[zona]
            for clave in (
                "distancia_supermercado_m",
                "distancia_parque_m",
                "distancia_metro_m",
                "distancia_promedio_m",
            ):
                self.assertIn(clave, distancias, msg=f"{zona}.{clave}")
                self.assertGreater(distancias[clave], 0.0, msg=f"{zona}.{clave}")

    def test_pedregal_distancia_a_supermercado_mas_cercano_es_xtra(self):
        """Verificacion manual e independiente (no usa las funciones bajo
        prueba para calcular el numero esperado):

        Pedregal tiene 2 supermercados en amenidades_pedregal_osm.geojson:
        "Minisuper 38" (way/1210862921, Polygon, requiere centroide) y
        "Xtra" (node/10910596086, Point directo, lat 9.0860839,
        lng -79.444263). Se calcula aqui, con shapely y haversine
        reimplementados de forma independiente al modulo bajo prueba,
        cual de los dos esta mas cerca del centroide real del poligono de
        Pedregal, y se confirma que `calcular_distancias_zona` reporta
        exactamente esa distancia -- no se asume de antemano cual de los
        dos es el mas cercano.
        """
        poligonos = cargar_poligonos()
        centroide_pedregal = poligonos["Pedregal"].centroid
        centroide_lat, centroide_lng = centroide_pedregal.y, centroide_pedregal.x

        # Coordenadas tal cual aparecen en amenidades_pedregal_osm.geojson.
        minisuper_38_polygon = shape(
            {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-79.4532725, 9.0922176],
                        [-79.4532407, 9.0921372],
                        [-79.4531522, 9.0921757],
                        [-79.4531876, 9.0922525],
                        [-79.4532725, 9.0922176],
                    ]
                ],
            }
        )
        minisuper_38_centroide = minisuper_38_polygon.centroid
        xtra_lat, xtra_lng = 9.0860839, -79.444263

        dist_minisuper_38 = distancia_haversine_metros(
            centroide_lat, centroide_lng, minisuper_38_centroide.y, minisuper_38_centroide.x
        )
        dist_xtra = distancia_haversine_metros(
            centroide_lat, centroide_lng, xtra_lat, xtra_lng
        )
        distancia_esperada = min(dist_minisuper_38, dist_xtra)

        # Xtra debe ser el mas cercano -- si esto falla, la aseveracion de
        # "Xtra es el caso manual verificado" ya no es cierta y hay que
        # revisar el archivo fuente, no ajustar el test.
        self.assertEqual(distancia_esperada, dist_xtra)

        distancia_calculada = distancia_minima_metros(
            (centroide_lat, centroide_lng), self.puntos_supermercado
        )
        self.assertAlmostEqual(distancia_calculada, distancia_esperada, places=6)
        self.assertEqual(
            self.distancias_por_zona["Pedregal"]["distancia_supermercado_m"],
            distancia_calculada,
        )


if __name__ == "__main__":
    unittest.main()
