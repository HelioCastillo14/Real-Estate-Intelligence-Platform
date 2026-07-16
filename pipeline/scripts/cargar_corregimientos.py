"""Carga de la tabla corregimientos (Feature 1.5.2) desde el Zone Health Composite Index.

Fuente de datos: pipeline/data/processed/zone_health_composite_1_4_6.json (Feature 1.4.6,
cerrada 2026-07-09). Esquema de destino: Context-MD/Ajuste_WBS_1_5_2_Esquema_Corregimientos.md §3,
migración supabase/migrations/20260715040001_corregimientos_create_table.sql.

Fuera de alcance de este script (§3, §6 del documento de esquema):
- geom: se puebla en un paso separado desde los shapefiles de Feature 1.3.1 (STRI/HDX).
- Resolución de qué polígono mostrar para una zona heredada en el mapa (Épica 5).

Este script imprime el resumen de las 9 filas para revisión manual y luego inserta en
Supabase vía psycopg2 (DATABASE_URL, nunca hardcodeado). psycopg2 en vez de supabase-py:
el siguiente paso de esta feature carga geom desde shapefiles procesados (Feature 1.3.1),
más directo con SQL crudo (ST_GeomFromText) que serializado vía la capa REST.

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`:
la llamada a insertar_corregimientos() queda comentada a propósito, requiere habilitarla
con confirmación explícita del usuario (mismo protocolo que la migración CREATE TABLE).
"""
import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_JSON = REPO_ROOT / "pipeline" / "data" / "processed" / "zone_health_composite_1_4_6.json"

INSERT_SQL = """
    insert into corregimientos (
        nombre, es_oficial, geom, hereda_de, zone_health_score,
        desglose_dimensiones, estado_zone_health, no_visualizado, motivo_visualizacion
    ) values (
        %(nombre)s, %(es_oficial)s, %(geom)s, %(hereda_de)s, %(zone_health_score)s,
        %(desglose_dimensiones)s, %(estado_zone_health)s, %(no_visualizado)s, %(motivo_visualizacion)s
    )
"""

# Ajuste_WBS_1_5_2_Esquema_Corregimientos.md §3: es_oficial distingue los 5 corregimientos
# administrativos reales (con geom propio) de las 4 zonas de scope sin geom propio.
ZONAS_OFICIALES = {"San Francisco", "Bella Vista", "Parque Lefevre", "Betania", "Pedregal"}


def construir_filas(zonas: dict) -> list[dict]:
    """Mapea cada entrada de zonas del JSON a una fila de corregimientos.

    Claves ausentes en el JSON (hereda_de, estado_visualizacion, motivo_visualizacion,
    motivo_estado) se tratan como NULL vía .get(clave, None) — el JSON las omite en vez
    de incluirlas con valor null cuando no aplican (Ajuste_WBS_1_5_2 §4bis).
    """
    filas = []
    for nombre, datos in zonas.items():
        estado_visualizacion = datos.get("estado_visualizacion", None)
        fila = {
            "nombre": nombre,
            "es_oficial": nombre in ZONAS_OFICIALES,
            "geom": None,  # poblado en paso separado desde shapefiles Feature 1.3.1
            "hereda_de": datos.get("hereda_de", None),
            "zone_health_score": datos.get("composite", None),
            "desglose_dimensiones": datos.get("desglose", None),
            "estado_zone_health": datos["estado_zone_health"],
            "no_visualizado": estado_visualizacion == "no_visualizado",
            "motivo_visualizacion": datos.get("motivo_visualizacion", None),
        }
        filas.append(fila)
    return filas


def imprimir_resumen(filas: list[dict]) -> None:
    print(f"Resumen de carga — {len(filas)} filas a insertar en corregimientos:\n")
    for fila in filas:
        print(f"- {fila['nombre']}")
        print(f"    es_oficial            = {fila['es_oficial']}")
        print(f"    hereda_de             = {fila['hereda_de']}")
        print(f"    zone_health_score     = {fila['zone_health_score']}")
        print(f"    desglose_dimensiones  = {fila['desglose_dimensiones']}")
        print(f"    estado_zone_health    = {fila['estado_zone_health']}")
        print(f"    no_visualizado        = {fila['no_visualizado']}")
        print(f"    motivo_visualizacion  = {fila['motivo_visualizacion']}")
        print(f"    geom                  = NULL (fuera de alcance de este script)")
        print()


def insertar_corregimientos(filas: list[dict]) -> None:
    """Inserta las 9 filas en una única transacción (todo o nada).

    hereda_de es una self-referencing FK (corregimientos.nombre) — las filas sin padre
    (hereda_de = None) se insertan primero para que la fila padre ya exista cuando se
    inserte la fila hija (El Cangrejo/Marbella/Obarrio -> Bella Vista), sin depender del
    orden en que el JSON de origen liste las zonas.
    """
    database_url = os.environ["DATABASE_URL"]
    filas_ordenadas = sorted(filas, key=lambda f: f["hereda_de"] is not None)

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for fila in filas_ordenadas:
                    params = dict(fila)
                    params["desglose_dimensiones"] = (
                        psycopg2.extras.Json(params["desglose_dimensiones"])
                        if params["desglose_dimensiones"] is not None
                        else None
                    )
                    cur.execute(INSERT_SQL, params)
        # El `with conn:` hace commit al salir sin excepción, o rollback completo si
        # cualquier INSERT de la transacción falla (todo o nada).
        print(f"{len(filas_ordenadas)} filas insertadas en corregimientos.")
    finally:
        conn.close()


def main() -> None:
    with open(RUTA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    filas = construir_filas(data["zonas"])
    assert len(filas) == 9, f"esperaba 9 zonas, encontré {len(filas)}"

    imprimir_resumen(filas)

    # --- Punto de corte deliberado ---
    # NO conectar a Supabase ni insertar todavía. La línea de abajo queda comentada a
    # propósito — se habilita con confirmación explícita del usuario, mismo protocolo
    # que la migración CREATE TABLE (acción sobre infraestructura compartida).
    print("Carga NO ejecutada contra Supabase — revisar el resumen arriba antes de habilitar la inserción.")
    insertar_corregimientos(filas)


if __name__ == "__main__":
    main()
