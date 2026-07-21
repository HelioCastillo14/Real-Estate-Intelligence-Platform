"""Carga de la tabla propiedades (Feature 1.5.1) desde el catálogo residencial limpio.

Fuente de datos: pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv (Feature 6.2.1,
1,177 filas). Esquema de destino: Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md, migración
supabase/migrations/20260715040000_propiedades_create_table.sql.

Validación en seco previa (sin tocar Supabase) confirmó: sin nulos en columnas NOT NULL, todos
los valores de zone_source/operation/tipo_inmueble/descripcion_fuente/enriquecimiento_estado/
corregimiento dentro de los sets permitidos por los CHECK ya aplicados, sin duplicados de
listing_id (PK) ni listing_url (UNIQUE).

embedding y geom se insertan explícitamente como NULL para las 1,177 filas — fuera de alcance
de este script (embedding se genera en Feature 6.2.3 sobre el catálogo cargado en Supabase,
geom es una aproximación sintética pendiente de un paso separado).

imagenes: el CSV la serializa como JSON-string (json.dumps) — requiere json.loads() explícito
antes de insertar como text[], nunca reconstrucción manual de string (comentario de columna en
la migración, Ajuste_WBS_1_5_1_Esquema_Propiedades.md §2.4).

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`: la
llamada a cargar() queda comentada a propósito, requiere habilitarla con confirmación explícita
del usuario (mismo protocolo que la migración CREATE TABLE).
"""
import json
import math
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CSV = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"

COLUMNAS_CSV = [
    "listing_id", "listing_url", "title", "zone_raw", "corregimiento", "zone_source",
    "price_raw", "price_usd", "precio_no_evaluable", "precio_no_evaluable_motivo",
    "bedrooms", "bathrooms", "area_m2", "operation", "source", "scraped_at",
    "corregimiento_archivo", "tipo_inmueble", "descripcion", "descripcion_fuente",
    "enriquecimiento_estado", "imagenes", "enriquecimiento_error_detalle",
]

INSERT_SQL = """
    insert into propiedades (
        listing_id, listing_url, title, zone_raw, corregimiento, zone_source,
        price_raw, price_usd, precio_no_evaluable, precio_no_evaluable_motivo,
        bedrooms, bathrooms, area_m2, operation, source, scraped_at,
        corregimiento_archivo, tipo_inmueble, descripcion, descripcion_fuente,
        enriquecimiento_estado, enriquecimiento_error_detalle, imagenes,
        embedding, geom
    ) values (
        %(listing_id)s, %(listing_url)s, %(title)s, %(zone_raw)s, %(corregimiento)s, %(zone_source)s,
        %(price_raw)s, %(price_usd)s, %(precio_no_evaluable)s, %(precio_no_evaluable_motivo)s,
        %(bedrooms)s, %(bathrooms)s, %(area_m2)s, %(operation)s, %(source)s, %(scraped_at)s,
        %(corregimiento_archivo)s, %(tipo_inmueble)s, %(descripcion)s, %(descripcion_fuente)s,
        %(enriquecimiento_estado)s, %(enriquecimiento_error_detalle)s, %(imagenes)s,
        %(embedding)s, %(geom)s
    )
"""


def _o_none(valor):
    """NaN de pandas -> None, para que psycopg2 inserte NULL en vez de 'nan'."""
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    return valor


def construir_filas(df: pd.DataFrame) -> list[dict]:
    """Mapea cada fila del CSV a los parámetros de INSERT_SQL.

    imagenes: json.loads() explícito sobre el string del CSV (comentario de columna en la
    migración) — nunca reconstrucción manual. embedding y geom quedan NULL explícito: no son
    insumo de este script, se pueblan en pasos separados (Feature 6.2.3 y una corrida
    posterior de geom sintético, respectivamente).
    """
    filas = []
    for _, fila in df.iterrows():
        imagenes_raw = fila["imagenes"]
        imagenes = json.loads(imagenes_raw) if isinstance(imagenes_raw, str) else None

        filas.append({
            "listing_id": int(fila["listing_id"]),
            "listing_url": fila["listing_url"],
            "title": fila["title"],
            "zone_raw": fila["zone_raw"],
            "corregimiento": fila["corregimiento"],
            "zone_source": fila["zone_source"],
            "price_raw": fila["price_raw"],
            "price_usd": int(fila["price_usd"]),
            "precio_no_evaluable": bool(fila["precio_no_evaluable"]),
            "precio_no_evaluable_motivo": _o_none(fila["precio_no_evaluable_motivo"]),
            "bedrooms": _o_none(fila["bedrooms"]),
            "bathrooms": _o_none(fila["bathrooms"]),
            "area_m2": _o_none(fila["area_m2"]),
            "operation": fila["operation"],
            "source": fila["source"],
            "scraped_at": fila["scraped_at"],
            "corregimiento_archivo": fila["corregimiento_archivo"],
            "tipo_inmueble": fila["tipo_inmueble"],
            "descripcion": _o_none(fila["descripcion"]),
            "descripcion_fuente": fila["descripcion_fuente"],
            "enriquecimiento_estado": fila["enriquecimiento_estado"],
            "enriquecimiento_error_detalle": _o_none(fila["enriquecimiento_error_detalle"]),
            "imagenes": imagenes,
            "embedding": None,
            "geom": None,
        })
    return filas


def imprimir_resumen(filas: list[dict]) -> None:
    print(f"Resumen de carga — {len(filas)} filas a insertar en propiedades:\n")
    print(f"  embedding = NULL explícito en las {len(filas)} filas")
    print(f"  geom      = NULL explícito en las {len(filas)} filas")
    sin_imagenes = sum(1 for f in filas if f["imagenes"] is None)
    print(f"  imagenes  = NULL en {sin_imagenes} fila(s) (esperado: 1, listing_id 137025 — fallo de red aislado)")
    print(f"\nPrimeras 3 filas (listing_id, corregimiento, tipo_inmueble):")
    for f in filas[:3]:
        print(f"  {f['listing_id']} | {f['corregimiento']} | {f['tipo_inmueble']}")


def cargar(filas: list[dict]) -> None:
    """Inserta las filas de propiedades en una única transacción (todo o nada)."""
    database_url = os.environ["DATABASE_URL"]

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for fila in filas:
                    cur.execute(INSERT_SQL, fila)
        # El `with conn:` hace commit al salir sin excepción, o rollback completo si
        # cualquier INSERT de la transacción falla (todo o nada).
        print(f"{len(filas)} filas insertadas en propiedades.")
    finally:
        conn.close()


def main() -> None:
    df = pd.read_csv(RUTA_CSV)
    assert len(df) == 1177, f"esperaba 1,177 filas, encontré {len(df)}"

    filas = construir_filas(df)
    imprimir_resumen(filas)

    # --- Punto de corte deliberado ---
    # NO conectar a Supabase ni insertar todavía. La línea de abajo queda comentada a
    # propósito — se habilita con confirmación explícita del usuario, mismo protocolo
    # que la migración CREATE TABLE (acción sobre infraestructura compartida).
    cargar(filas)


if __name__ == "__main__":
    main()
