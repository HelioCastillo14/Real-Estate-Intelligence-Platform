#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests de regresion para el cruce espacial (Feature 1.4, Acta 1.3 §6.3).

Fija las 4 asignaciones conocidas de metro_estaciones_final_30.jsonl contra
coordenadas hardcodeadas, para que una futura corrida del cruce no dependa
de releer el archivo real (que puede cambiar) sino de la geometria fija de
los 5 poligonos administrativos.
"""

import unittest

from pipeline.zone_health.cruce_espacial_corregimiento import (
    asignar_corregimiento,
    cargar_poligonos,
)

CASOS_DENTRO_DE_SCOPE = [
    ("Iglesia Del Carmen", 8.982407, -79.527049, "Bella Vista"),
    ("Vía Argentina", 8.989345, -79.52235, "Bella Vista"),
    ("Pedregal-Las Acacias", 9.059848, -79.429287, "Pedregal"),
    ("Don Bosco", 9.063089, -79.420385, "Pedregal"),
]

# Estacion Albrook (terminal de transporte, Curundu) -- fuera de las 5 zonas reales.
CASO_FUERA_DE_SCOPE = ("Albrook", 8.973523, -79.54949)


class TestCruceEspacialCorregimiento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.poligonos = cargar_poligonos()

    def test_las_5_zonas_reales_cargan(self):
        self.assertEqual(
            set(self.poligonos.keys()),
            {"Bella Vista", "Betania", "Parque Lefevre", "Pedregal", "San Francisco"},
        )

    def test_asignaciones_conocidas_dentro_de_scope(self):
        for nombre, lat, lng, corregimiento_esperado in CASOS_DENTRO_DE_SCOPE:
            with self.subTest(estacion=nombre):
                resultado = asignar_corregimiento(lat, lng, self.poligonos)
                self.assertEqual(resultado, corregimiento_esperado)

    def test_punto_fuera_de_scope_devuelve_none(self):
        _, lat, lng = CASO_FUERA_DE_SCOPE
        resultado = asignar_corregimiento(lat, lng, self.poligonos)
        self.assertIsNone(resultado)


if __name__ == "__main__":
    unittest.main()
