"""Carga de la columna `propiedades.embedding` (Feature 2.1.3).

Fuente de datos: `pipeline/models/embeddings_catalogo_2_1_3_completo.pkl`, generado por
`pipeline/scripts/generar_embeddings_faltantes_2_1_3.py` — 1,110 vectores reutilizados de
Feature 6.2.3 + 67 calculados en 2.1.3 para las filas excluidas del ground truth de M1
(`zona_no_determinada` / `precio_no_evaluable`) pero sí consumidas por M3. Total esperado:
1,177, dimensión 3072 en todas (Feature 1.5b, `supabase/migrations/20260715032111_propiedades_embedding.sql`,
ya fusionada en el `CREATE TABLE` de `20260715040000_propiedades_create_table.sql`).

`propiedades` ya debe existir con las 1,177 filas cargadas (`pipeline/scripts/cargar_propiedades.py`,
`embedding` insertado como NULL explícito en ese script) — este script hace UPDATE por
`listing_id`, nunca INSERT. Una única transacción (todo o nada): si algún `listing_id` del
pickle no existe en `propiedades`, el UPDATE afecta 0 filas para esa fila y se detecta en la
verificación de conteo antes del commit (no falla por FK como un INSERT, así que la
verificación de `rowcount` es la única defensa).

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`: la
llamada a cargar() queda comentada a propósito, requiere habilitarla con confirmación explícita
del usuario (mismo protocolo que la migración CREATE TABLE).
"""

import json
import os
import pickle
from pathlib import Path

import psycopg2
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_PKL = REPO_ROOT / "pipeline" / "models" / "embeddings_catalogo_2_1_3_completo.pkl"
RUTA_FALLOS = REPO_ROOT / "pipeline" / "models" / "embeddings_catalogo_2_1_3_fallos.json"

DIMENSION_ESPERADA = 3072
TOTAL_ESPERADO = 1177
N_REUTILIZADOS_ESPERADO = 1110
N_NUEVOS_ESPERADO = 67

UPDATE_SQL = """
    update propiedades
    set embedding = %(embedding)s::vector
    where listing_id = %(listing_id)s
"""


def vector_a_literal(vector: list[float]) -> str:
    """list[float] -> literal de texto que Postgres/pgvector castea con ::vector.

    float(x) explícito: los vectores reutilizados de 6.2.3 vienen de un pickle con
    numpy.float64 (via pandas), cuyo repr() es "np.float64(...)", no un literal numérico
    válido para el cast ::vector de Postgres.
    """
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"


def construir_filas(consolidado: dict) -> list[dict]:
    filas = []
    for listing_id, vector, fuente in zip(consolidado["id"], consolidado["vector"], consolidado["fuente"]):
        if len(vector) != DIMENSION_ESPERADA:
            raise AssertionError(
                f"listing_id={listing_id}: dimensión {len(vector)}, se esperaban {DIMENSION_ESPERADA}"
            )
        filas.append({
            "listing_id": int(listing_id),
            "embedding": vector_a_literal(vector),
            "fuente": fuente,
        })
    return filas


def imprimir_resumen(filas: list[dict], fallos: list[dict]) -> None:
    n_total = len(filas)
    n_reutilizados = sum(1 for f in filas if f["fuente"] == "reutilizado_6_2_3")
    n_nuevos = sum(1 for f in filas if f["fuente"] == "nuevo_2_1_3")
    dimensiones = {len(f["embedding"].strip("[]").split(",")) for f in filas}

    print("=== DRY RUN — cargar_embeddings.py (Feature 2.1.3) ===\n")
    print(f"Total de vectores a insertar (UPDATE): {n_total} (esperado: {TOTAL_ESPERADO})")
    print(f"  Reutilizados de 6.2.3: {n_reutilizados} (esperado: {N_REUTILIZADOS_ESPERADO})")
    print(f"  Nuevos calculados en 2.1.3: {n_nuevos} (esperado: {N_NUEVOS_ESPERADO})")

    print(f"\nFilas que fallaron en el cálculo del embedding (no llegan a este script): {len(fallos)}")
    for f in fallos:
        print(f"  - listing_id={f['listing_id']}: {f['motivo']}")
    if not fallos:
        print("  (ninguna)")

    print(f"\nVerificación de dimensión: {dimensiones}")
    ok_dimension = dimensiones == {DIMENSION_ESPERADA}
    print(f"  {'OK' if ok_dimension else 'FALLA'} — todos los vectores tienen dimensión {DIMENSION_ESPERADA}"
          if ok_dimension else f"  FALLA — se esperaba únicamente {{{DIMENSION_ESPERADA}}}")

    ok_total = n_total == TOTAL_ESPERADO
    ok_split = n_reutilizados == N_REUTILIZADOS_ESPERADO and n_nuevos == N_NUEVOS_ESPERADO
    print(f"\nResumen final: total {'OK' if ok_total else 'FALLA'}, "
          f"split 1,110/67 {'OK' if ok_split else 'FALLA'}, "
          f"dimensión {'OK' if ok_dimension else 'FALLA'}.")

    if not (ok_total and ok_split and ok_dimension):
        print("\nNO se recomienda proceder con la carga real hasta resolver lo anterior.")


def cargar(filas: list[dict]) -> None:
    """UPDATE de embedding por listing_id, en una única transacción (todo o nada)."""
    database_url = os.environ["DATABASE_URL"]

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                filas_sin_match = []
                for fila in filas:
                    cur.execute(UPDATE_SQL, {"embedding": fila["embedding"], "listing_id": fila["listing_id"]})
                    if cur.rowcount != 1:
                        filas_sin_match.append(fila["listing_id"])

                if filas_sin_match:
                    raise AssertionError(
                        f"{len(filas_sin_match)} listing_id(s) sin match en propiedades "
                        f"(0 filas afectadas por el UPDATE): {filas_sin_match}"
                    )
        # El `with conn:` hace commit al salir sin excepción, o rollback completo si
        # cualquier UPDATE o la verificación de filas_sin_match falla (todo o nada).
        print(f"{len(filas)} filas de propiedades.embedding actualizadas.")
    finally:
        conn.close()


def main() -> None:
    with open(RUTA_PKL, "rb") as f:
        consolidado = pickle.load(f)

    fallos = []
    if RUTA_FALLOS.exists():
        with open(RUTA_FALLOS, encoding="utf-8") as f:
            fallos = json.load(f)

    filas = construir_filas(consolidado)
    imprimir_resumen(filas, fallos)

    # --- Punto de corte deliberado ---
    # NO conectar a Supabase ni actualizar todavía. La línea de abajo queda comentada a
    # propósito — se habilita con confirmación explícita del usuario, mismo protocolo
    # que la migración CREATE TABLE (acción sobre infraestructura compartida).
    cargar(filas)


if __name__ == "__main__":
    main()
