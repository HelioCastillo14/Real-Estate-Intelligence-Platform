"""Carga de valuacion_quality_scorer (Feature 1.5.4).

Fuente de datos: pipeline/models/quality_scores_produccion_final.csv (fallback a .pkl si el
CSV no existe). Esquema de destino: Context-MD/Ajuste_WBS_1_5_4_Esquema_Scores.md §3, migración
supabase/migrations/20260715040004_scores_valuacion_compatibilidad_sesiones.sql.

Alcance: SOLO valuacion_quality_scorer. Las otras 4 tablas de 1.5.4
(valuacion_semaforo_knn, valuacion_segmento_kmeans, sesiones_consulta, scores_compatibilidad)
quedan vacías — sus batches/scripts de producción no existen todavía (§1, §8 del documento de
esquema). Este script no escribe ninguna lógica de carga para ellas.

Verificación contra el paper (Cuadro IX), ANTES de conectar a Supabase: media y desviación
estándar de las 4 dimensiones deben coincidir con los valores ya publicados dentro de ±0.01.
Si alguna difiere en más de eso, el script se detiene sin conectar ni insertar — el paper ya es
versión final (§6 del documento de esquema), ninguna discrepancia se resuelve alterando el
número publicado sin decisión explícita del equipo.

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`: la
llamada a cargar() queda comentada a propósito, requiere habilitarla con confirmación explícita
del usuario (mismo protocolo que la migración CREATE TABLE).
"""
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_CSV = REPO_ROOT / "pipeline" / "models" / "quality_scores_produccion_final.csv"
RUTA_PKL = REPO_ROOT / "pipeline" / "models" / "quality_scores_produccion_final.pkl"

N_ESPERADO = 1168

# Cuadro IX del paper (ya publicado, versión final) — media ± desviación estándar por dimensión.
# Fuente de verdad para la verificación, no recalculado aquí a partir de otro documento.
REFERENCIA_PAPER = {
    "completitud_informativa": (4.66, 0.67),
    "calidad_presentacion": (4.73, 0.61),
    "diferenciadores_amenidades": (4.51, 0.84),
    "transparencia_precio": (3.68, 1.81),
}
TOLERANCIA = 0.01

INSERT_SQL = """
    insert into valuacion_quality_scorer (
        listing_id, modelo, completitud_informativa, calidad_presentacion,
        diferenciadores_amenidades, transparencia_precio
    ) values (
        %(listing_id)s, %(modelo)s, %(completitud_informativa)s, %(calidad_presentacion)s,
        %(diferenciadores_amenidades)s, %(transparencia_precio)s
    )
"""


def cargar_dataframe() -> pd.DataFrame:
    """Lee el CSV de producción (o el .pkl si el CSV no existe)."""
    if RUTA_CSV.exists():
        return pd.read_csv(RUTA_CSV)
    if RUTA_PKL.exists():
        return pd.read_pickle(RUTA_PKL)
    raise FileNotFoundError(
        f"No se encontró ni {RUTA_CSV.name} ni {RUTA_PKL.name} en {RUTA_CSV.parent}"
    )


def verificar_contra_paper(df: pd.DataFrame) -> bool:
    """Compara media/desviación estándar de las 4 dimensiones contra el Cuadro IX del paper.

    Devuelve True solo si las 4 dimensiones coinciden dentro de TOLERANCIA (0.01). No se
    detiene aquí en caso de discrepancia — solo reporta e informa al llamador, que decide
    si continúa hacia la conexión a Supabase.
    """
    print("Verificación contra Cuadro IX del paper (media ± desviación estándar):\n")
    print(f"{'dimension':<30} {'media_real':>10} {'std_real':>10} {'media_paper':>12} {'std_paper':>10} {'ok':>5}")

    todo_ok = True
    for dimension, (media_paper, std_paper) in REFERENCIA_PAPER.items():
        media_real = df[dimension].mean()
        std_real = df[dimension].std()

        diff_media = abs(media_real - media_paper)
        diff_std = abs(std_real - std_paper)
        ok = diff_media <= TOLERANCIA and diff_std <= TOLERANCIA
        todo_ok &= ok

        print(
            f"{dimension:<30} {media_real:>10.2f} {std_real:>10.2f} "
            f"{media_paper:>12.2f} {std_paper:>10.2f} {'OK' if ok else 'FALLA':>5}"
        )

    return todo_ok


def imprimir_resumen(df: pd.DataFrame) -> None:
    print(f"Resumen de carga — {len(df)} filas a insertar en valuacion_quality_scorer\n")
    print("Conteo por modelo:")
    print(df["modelo"].value_counts().to_string())
    print()


def cargar(df: pd.DataFrame) -> None:
    """Inserta valuacion_quality_scorer en una única transacción (todo o nada)."""
    database_url = os.environ["DATABASE_URL"]

    columnas = [
        "listing_id", "modelo", "completitud_informativa", "calidad_presentacion",
        "diferenciadores_amenidades", "transparencia_precio",
    ]
    filas = df[columnas].to_dict(orient="records")

    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for fila in filas:
                    cur.execute(INSERT_SQL, fila)

                cur.execute("select count(*) from valuacion_quality_scorer")
                (conteo_real,) = cur.fetchone()
                assert conteo_real == N_ESPERADO, (
                    f"esperaba {N_ESPERADO} filas en valuacion_quality_scorer tras la carga, "
                    f"encontré {conteo_real} — abortando antes de commit."
                )
        # El `with conn:` hace commit al salir sin excepción, o rollback completo si
        # cualquier INSERT o la verificación de conteo falla (todo o nada).
        print(f"\n{conteo_real} filas insertadas en valuacion_quality_scorer.")
    finally:
        conn.close()


def main() -> None:
    df = cargar_dataframe()

    assert len(df) == N_ESPERADO, f"esperaba {N_ESPERADO} filas en el archivo fuente, encontré {len(df)}"

    imprimir_resumen(df)

    coincide_con_paper = verificar_contra_paper(df)
    if not coincide_con_paper:
        print(
            "\nAl menos una dimensión difiere del Cuadro IX del paper en más de "
            f"{TOLERANCIA} — deteniendo ANTES de conectar a Supabase. El paper ya es versión "
            "final (Ajuste_WBS_1_5_4_Esquema_Scores.md §6); esta discrepancia debe resolverse "
            "por decisión explícita del equipo, no insertando datos que no coinciden con lo "
            "publicado."
        )
        return

    print("\nLas 4 dimensiones coinciden con el Cuadro IX del paper dentro de la tolerancia.")

    # --- Punto de corte deliberado ---
    # Habilitado con confirmación explícita del usuario (mismo protocolo que la
    # migración CREATE TABLE, ya aplicada contra Supabase).
    cargar(df)


if __name__ == "__main__":
    main()
