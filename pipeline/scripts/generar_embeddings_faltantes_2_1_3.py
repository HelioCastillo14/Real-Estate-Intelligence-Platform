"""Genera los embeddings faltantes de Feature 2.1.3 y consolida los 1,177 vectores completos.

`pipeline/models/embeddings_catalogo_6_2_3_raw.pkl` (Feature 6.2.3) cubre 1,110 de las 1,177
filas de `pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv` — las 67 filas
faltantes son exactamente las excluidas por el filtro de validez de M1 (53 con
`corregimiento == "zona_no_determinada"`, 14 con `precio_no_evaluable == True`; confirmado
por diferencia de conjuntos, sin solapamiento inesperado). Esa exclusión es específica del
ground truth de M1 (Notebook 1, celda 5) y NO aplica a la tabla `propiedades`: M3 consume el
catálogo completo sin ese filtro, así que las 67 filas sí necesitan embedding en la tabla
maestra. Decisión de scope ya cerrada, no se reabre aquí.

Texto de entrada: mismo criterio que 6.2.3 — `descripcion` cuando `descripcion_fuente` es
`completa` o `preview`, `title` como respaldo cuando es `ninguna`.

Usa `generar_embedding()` de `backend/app/services/embeddings.py` (Feature 2.1.2, ya
verificada: `gemini-embedding-001`, 3072 dimensiones). Un fallo de la API en una fila
individual se registra (listing_id + motivo) y NO aborta el resto del batch.

Salida: `pipeline/models/embeddings_catalogo_2_1_3_completo.pkl` — 1,110 vectores reutilizados
de 6.2.3 + los nuevos calculados aquí (hasta 67, según cuántos tengan éxito), con una columna
`fuente` por fila para distinguir el origen. Los fallos, si los hay, quedan documentados en
`pipeline/models/embeddings_catalogo_2_1_3_fallos.json`.

NO conecta a Supabase — ver `pipeline/scripts/cargar_embeddings.py` para la carga.
"""

import json
import pickle
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from app.services.embeddings import DIMENSION_ESPERADA, EmbeddingError, generar_embedding

RUTA_CATALOGO = REPO_ROOT / "pipeline" / "data" / "processed" / "catalogo_residencial_limpio_6_2_1.csv"
RUTA_PKL_6_2_3 = REPO_ROOT / "pipeline" / "models" / "embeddings_catalogo_6_2_3_raw.pkl"
RUTA_SALIDA_PKL = REPO_ROOT / "pipeline" / "models" / "embeddings_catalogo_2_1_3_completo.pkl"
RUTA_SALIDA_FALLOS = REPO_ROOT / "pipeline" / "models" / "embeddings_catalogo_2_1_3_fallos.json"


def texto_de_entrada(fila: pd.Series) -> str:
    """Mismo criterio de 6.2.3: descripcion si descripcion_fuente en {completa, preview}, si no title."""
    if fila["descripcion_fuente"] in ("completa", "preview"):
        return fila["descripcion"]
    return fila["title"]


def identificar_faltantes(df_catalogo: pd.DataFrame, ids_existentes: set) -> pd.DataFrame:
    df_faltantes = df_catalogo[~df_catalogo["listing_id"].isin(ids_existentes)].copy()

    esperado_por_filtro = df_faltantes[
        (df_faltantes["corregimiento"] == "zona_no_determinada")
        | (df_faltantes["precio_no_evaluable"] == True)  # noqa: E712
    ]
    if len(esperado_por_filtro) != len(df_faltantes):
        inesperadas = df_faltantes[~df_faltantes.index.isin(esperado_por_filtro.index)]
        raise AssertionError(
            f"{len(inesperadas)} fila(s) faltante(s) no coinciden con el filtro esperado "
            f"(zona_no_determinada / precio_no_evaluable): "
            f"{inesperadas['listing_id'].tolist()}"
        )
    return df_faltantes


def calcular_embeddings_faltantes(df_faltantes: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Devuelve (exitos, fallos). Un fallo de API en una fila no detiene las demás."""
    exitos = []
    fallos = []
    total = len(df_faltantes)
    for i, (_, fila) in enumerate(df_faltantes.iterrows(), start=1):
        listing_id = int(fila["listing_id"])
        texto = texto_de_entrada(fila)
        print(f"[{i}/{total}] listing_id={listing_id} ... ", end="", flush=True)
        try:
            vector = generar_embedding(texto)
        except EmbeddingError as exc:
            print(f"FALLÓ: {exc}")
            fallos.append({"listing_id": listing_id, "motivo": str(exc)})
            continue
        print("OK")
        exitos.append({"listing_id": listing_id, "vector": vector})
    return exitos, fallos


def consolidar(pkl_6_2_3: dict, exitos: list[dict]) -> dict:
    ids = list(pkl_6_2_3["id"]) + [e["listing_id"] for e in exitos]
    vectores = list(pkl_6_2_3["vector"]) + [e["vector"] for e in exitos]
    fuentes = ["reutilizado_6_2_3"] * len(pkl_6_2_3["id"]) + ["nuevo_2_1_3"] * len(exitos)
    return {"id": ids, "vector": vectores, "fuente": fuentes}


def imprimir_resumen(consolidado: dict, fallos: list[dict], total_catalogo: int) -> None:
    n_total = len(consolidado["id"])
    n_reutilizados = consolidado["fuente"].count("reutilizado_6_2_3")
    n_nuevos = consolidado["fuente"].count("nuevo_2_1_3")

    print("\n=== RESUMEN ===")
    print(f"Total de filas en catálogo fuente: {total_catalogo}")
    print(f"Vectores consolidados: {n_total} (reutilizados: {n_reutilizados}, nuevos: {n_nuevos})")
    print(f"Fallos de cálculo: {len(fallos)}")
    for f in fallos:
        print(f"  - listing_id={f['listing_id']}: {f['motivo']}")

    dimensiones = {len(v) for v in consolidado["vector"]}
    print(f"Dimensiones observadas en el consolidado: {dimensiones}")
    if dimensiones != {DIMENSION_ESPERADA}:
        print(f"  ADVERTENCIA: se esperaba únicamente {{{DIMENSION_ESPERADA}}}")

    if n_total + len(fallos) != total_catalogo:
        print(
            f"  ADVERTENCIA: {n_total} consolidados + {len(fallos)} fallos = "
            f"{n_total + len(fallos)}, no coincide con {total_catalogo} filas del catálogo."
        )


def main() -> None:
    df_catalogo = pd.read_csv(RUTA_CATALOGO)
    assert len(df_catalogo) == 1177, f"esperaba 1,177 filas en el catálogo, encontré {len(df_catalogo)}"

    with open(RUTA_PKL_6_2_3, "rb") as f:
        pkl_6_2_3 = pickle.load(f)
    assert len(pkl_6_2_3["id"]) == 1110, f"esperaba 1,110 vectores en 6.2.3, encontré {len(pkl_6_2_3['id'])}"

    ids_existentes = set(pkl_6_2_3["id"])
    df_faltantes = identificar_faltantes(df_catalogo, ids_existentes)
    assert len(df_faltantes) == 67, f"esperaba 67 filas faltantes, encontré {len(df_faltantes)}"
    print(f"{len(df_faltantes)} filas faltantes identificadas (fuera del filtro de validez de M1, dentro del scope de M3).\n")

    exitos, fallos = calcular_embeddings_faltantes(df_faltantes)

    consolidado = consolidar(pkl_6_2_3, exitos)
    imprimir_resumen(consolidado, fallos, len(df_catalogo))

    with open(RUTA_SALIDA_PKL, "wb") as f:
        pickle.dump(consolidado, f)
    print(f"\nConsolidado guardado en: {RUTA_SALIDA_PKL}")

    with open(RUTA_SALIDA_FALLOS, "w", encoding="utf-8") as f:
        json.dump(fallos, f, ensure_ascii=False, indent=2)
    print(f"Fallos guardados en: {RUTA_SALIDA_FALLOS} ({len(fallos)} registro(s))")


if __name__ == "__main__":
    main()
