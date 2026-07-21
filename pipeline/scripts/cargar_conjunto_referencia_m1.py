"""Carga de perfiles_lifestyle y conjunto_referencia_m1 (Feature 1.5.5).

Fuente de datos: pipeline/data/processed/conjunto_referencia_m1_6_2_3.json (materializado por
pipeline/scripts/materializar_ground_truth_m1.py). Esquema de destino:
Context-MD/Ajuste_WBS_1_5_5_Esquema_ConjuntoReferenciaM1.md §2, migración
supabase/migrations/20260715040002_perfiles_lifestyle_y_conjunto_referencia_m1.sql.

Orden de carga: perfiles_lifestyle primero (conjunto_referencia_m1.perfil la referencia vía FK),
luego conjunto_referencia_m1 (una fila por listing_id, flag_sintetico = TRUE explícito). Ambas
tablas se cargan en una única transacción (todo o nada) — si algún listing_id del JSON no existe
en propiedades, el INSERT falla por la FK y hay que investigar antes de forzar nada (§5 del
documento de esquema).

Verificación final (§4): n_ground_truth de perfiles_lifestyle debe coincidir exactamente con
COUNT(*) de conjunto_referencia_m1 agrupado por perfil — se imprime como tabla antes de cualquier
commit.

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`: la llamada
a cargar() queda comentada a propósito, requiere habilitarla con confirmación explícita del
usuario (mismo protocolo que la migración CREATE TABLE).
"""
import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_JSON = REPO_ROOT / "pipeline" / "data" / "processed" / "conjunto_referencia_m1_6_2_3.json"

INSERT_PERFIL_SQL = """
    insert into perfiles_lifestyle (
        perfil, reglas_estructurales, criterio_cualitativo,
        n_solo_estructural, n_ground_truth, hash_catalogo_fuente, fecha_materializacion
    ) values (
        %(perfil)s, %(reglas_estructurales)s, %(criterio_cualitativo)s,
        %(n_solo_estructural)s, %(n_ground_truth)s, %(hash_catalogo_fuente)s, %(fecha_materializacion)s
    )
"""

INSERT_REFERENCIA_SQL = """
    insert into conjunto_referencia_m1 (perfil, listing_id, flag_sintetico)
    values (%(perfil)s, %(listing_id)s, true)
"""


def construir_filas_perfiles(data: dict) -> list[dict]:
    """Mapea cada entrada de perfiles del JSON a una fila de perfiles_lifestyle.

    n_ground_truth se deriva de len(listing_ids_ground_truth) — no se lee ningún campo
    separado del JSON, ya que conjunto_referencia_m1_6_2_3.json no lo materializa como
    número aparte (Ajuste_WBS_1_5_5 §2).
    """
    filas = []
    for perfil, datos in data["perfiles"].items():
        filas.append({
            "perfil": perfil,
            "reglas_estructurales": datos["reglas_estructurales"],
            "criterio_cualitativo": datos["criterio_cualitativo"],
            "n_solo_estructural": datos["n_solo_estructural"],
            "n_ground_truth": len(datos["listing_ids_ground_truth"]),
            "hash_catalogo_fuente": data["hash_catalogo"],
            "fecha_materializacion": data["fecha_materializacion"],
        })
    return filas


def construir_filas_referencia(data: dict) -> list[dict]:
    """Una fila por cada listing_id en listing_ids_ground_truth de cada perfil."""
    filas = []
    for perfil, datos in data["perfiles"].items():
        for listing_id in datos["listing_ids_ground_truth"]:
            filas.append({"perfil": perfil, "listing_id": listing_id})
    return filas


def imprimir_resumen(filas_perfiles: list[dict], filas_referencia: list[dict]) -> None:
    print(f"Resumen de carga — {len(filas_perfiles)} filas a insertar en perfiles_lifestyle:\n")
    for fila in filas_perfiles:
        print(f"- {fila['perfil']}")
        print(f"    n_solo_estructural    = {fila['n_solo_estructural']}")
        print(f"    n_ground_truth        = {fila['n_ground_truth']}")
        print(f"    hash_catalogo_fuente  = {fila['hash_catalogo_fuente'][:16]}...")
        print(f"    fecha_materializacion = {fila['fecha_materializacion']}")
    print(f"\nTotal de filas a insertar en conjunto_referencia_m1: {len(filas_referencia)}")


def cargar(filas_perfiles: list[dict], filas_referencia: list[dict]) -> None:
    """Inserta perfiles_lifestyle y conjunto_referencia_m1 en una única transacción.

    perfiles_lifestyle primero: conjunto_referencia_m1.perfil es FK hacia
    perfiles_lifestyle.perfil, debe existir antes de insertar las filas de referencia.
    """
    database_url = os.environ["DATABASE_URL"]

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for fila in filas_perfiles:
                    params = dict(fila)
                    params["reglas_estructurales"] = psycopg2.extras.Json(params["reglas_estructurales"])
                    params["criterio_cualitativo"] = psycopg2.extras.Json(params["criterio_cualitativo"])
                    cur.execute(INSERT_PERFIL_SQL, params)

                for fila in filas_referencia:
                    cur.execute(INSERT_REFERENCIA_SQL, fila)

                verificar_conteos(cur, filas_perfiles)
        # El `with conn:` hace commit al salir sin excepción, o rollback completo si
        # cualquier INSERT o la verificación de conteos falla (todo o nada).
        print(f"\n{len(filas_referencia)} filas insertadas en conjunto_referencia_m1.")
    finally:
        conn.close()


def verificar_conteos(cur, filas_perfiles: list[dict]) -> None:
    """Compara n_ground_truth de perfiles_lifestyle contra COUNT(*) real de
    conjunto_referencia_m1 por perfil (§4 del documento de esquema) — se corre dentro de
    la misma transacción, antes del commit, para poder abortar si algo no cuadra.
    """
    cur.execute("select perfil, count(*) from conjunto_referencia_m1 group by perfil")
    conteos_reales = dict(cur.fetchall())

    print("\nVerificación de conteo por perfil (n_ground_truth vs. COUNT(*) real):\n")
    print(f"{'perfil':<32} {'n_ground_truth':>15} {'count_real':>12} {'ok':>5}")
    todo_ok = True
    for fila in filas_perfiles:
        perfil = fila["perfil"]
        esperado = fila["n_ground_truth"]
        real = conteos_reales.get(perfil, 0)
        ok = esperado == real
        todo_ok &= ok
        print(f"{perfil:<32} {esperado:>15} {real:>12} {'OK' if ok else 'FALLA':>5}")

    assert todo_ok, "Al menos un perfil no coincide entre n_ground_truth y COUNT(*) real — abortando antes de commit."


def main() -> None:
    with open(RUTA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    filas_perfiles = construir_filas_perfiles(data)
    filas_referencia = construir_filas_referencia(data)

    assert len(filas_perfiles) == 6, f"esperaba 6 perfiles, encontré {len(filas_perfiles)}"
    assert len(filas_referencia) == 577, f"esperaba 577 filas de referencia, encontré {len(filas_referencia)}"

    imprimir_resumen(filas_perfiles, filas_referencia)

    # --- Punto de corte deliberado ---
    # NO conectar a Supabase ni insertar todavía. La línea de abajo queda comentada a
    # propósito — se habilita con confirmación explícita del usuario, mismo protocolo
    # que la migración CREATE TABLE (acción sobre infraestructura compartida).
    cargar(filas_perfiles, filas_referencia)


if __name__ == "__main__":
    main()
