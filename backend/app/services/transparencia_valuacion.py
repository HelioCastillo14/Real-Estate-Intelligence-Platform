"""Carga y resumen del conjunto de transparencia del semáforo KNN (Feature 3.5.1/3.5.2, M2).

**Fuente: CSV estático (`pipeline/data/processed/conjunto_test_semaforo_knn_3_5_1.csv`), no una
tabla de Supabase — decisión explícita, no el patrón por defecto del resto del backend.** El
resto de servicios de producción (`comparables_knn.py`, `busqueda_ann.py`) sí consultan Supabase
porque operan sobre el catálogo vivo, que cambia con cada scraping. Este artifact es distinto:
son las 209 predicciones del conjunto de TEST del KNN de 6.2.4 — fijas por definición, ya que
cambiarían únicamente si el modelo se reentrena (evento raro, versionado por notebook, no por
tráfico). Cargarlas a una tabla nueva de Supabase agregaría una migración, un batch de carga y
una dependencia de red por request para servir 209 filas que no cambian entre requests — sin
ningún beneficio real sobre leer el CSV una vez y cachearlo en memoria (`lru_cache`, mismo
mecanismo que `comparables_knn._cargar_artifacts()`). Si el modelo se reentrena, se regenera el
CSV (`pipeline/scripts/exportar_conjunto_test_semaforo_knn_3_5_1.py`) y se reinicia el proceso
del backend — no hace falta una migración de schema para eso.

**`mae_absoluto` se recalcula de las 209 filas cargadas, no se toma de una constante congelada
— pero SÍ se verifica contra la constante ya verificada en 3.1.3/3.5.1 antes de servir nada.**
Si el CSV se corrompiera o se regenerara mal, sirviendo el número recalculado en silencio se
propagaría el error al frontend/paper sin ninguna señal. `_cargar_pares()` lanza
`TransparenciaValuacionError` si el recálculo no coincide con `MAE_TEST_REFERENCIA` dentro de
tolerancia de punto flotante — nunca sirve un MAE no verificado.

**Dos poblaciones distintas para el denominador del MAE, mismo hallazgo de 3.5.1 — el response
lo declara explícitamente para que el frontend no lo malinterprete:** `mae_absoluto` es sobre las
209 filas de test (out-of-sample real). `mae_porcentual` divide ese mismo MAE entre
`PRECIO_PROMEDIO_CATALOGO_COMPLETO` — la media de precio del catálogo COMPLETO de 1,042 filas
elegibles (Notebook 2, celda 26), no la media de estas 209 filas de test. Es la misma
metodología que produjo el 33.4% ya publicado (`Feature_6_2_4_M2_KNN_RF_Cierre.md`) — dividir
por la media de las 209 filas de test da un número distinto (~32.3%), documentado como hallazgo
de 3.5.1 para que no se repita la confusión.
"""

import csv
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUTA_CSV = REPO_ROOT / "pipeline" / "data" / "processed" / "conjunto_test_semaforo_knn_3_5_1.csv"

# Verificados en 3.1.3 (reproducción exacta contra el catálogo real) y 3.5.1 (recalculados desde
# este mismo CSV, coincidencia exacta confirmada) — no recalculados aquí desde el catálogo
# completo, este servicio no tiene acceso a pandas/sklearn ni al CSV fuente de 1,042 filas.
MAE_TEST_REFERENCIA = 187543.4765550239
PRECIO_PROMEDIO_CATALOGO_COMPLETO = 561494.7715930903
N_CATALOGO_COMPLETO = 1042
TOLERANCIA_MAE = 1e-3


class TransparenciaValuacionError(RuntimeError):
    """El CSV fuente de 3.5.1 no existe, está vacío, o su MAE no coincide con el ya verificado."""


@lru_cache(maxsize=1)
def _cargar_pares() -> list[dict]:
    if not RUTA_CSV.exists():
        raise TransparenciaValuacionError(
            f"No existe {RUTA_CSV} — correr "
            f"pipeline/scripts/exportar_conjunto_test_semaforo_knn_3_5_1.py (3.5.1) antes de "
            f"levantar este endpoint."
        )
    with open(RUTA_CSV, newline="") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise TransparenciaValuacionError(
            f"{RUTA_CSV} existe pero tiene 0 filas — no se expone una lista vacía en silencio, "
            f"eso se leería como 'el modelo no tiene desviaciones', que sería falso."
        )

    pares = []
    suma_abs = 0.0
    for fila in filas:
        precio_real = float(fila["precio_real"])
        precio_predicho = float(fila["precio_predicho"])
        diferencia_absoluta = precio_real - precio_predicho
        suma_abs += abs(diferencia_absoluta)
        pares.append({
            "propiedad_id": int(fila["propiedad_id"]),
            "precio_real": precio_real,
            "precio_predicho": precio_predicho,
            "diferencia_absoluta": diferencia_absoluta,
            "zona": fila["zona"],
        })

    mae_recalculado = suma_abs / len(pares)
    if abs(mae_recalculado - MAE_TEST_REFERENCIA) > TOLERANCIA_MAE:
        raise TransparenciaValuacionError(
            f"El MAE recalculado desde {RUTA_CSV.name} (${mae_recalculado:,.4f}) no coincide con "
            f"el ya verificado en 3.1.3/3.5.1 (${MAE_TEST_REFERENCIA:,.4f}) — el CSV pudo haberse "
            f"regenerado con otro modelo/split sin actualizar esta constante, o corromperse. No "
            f"se sirve un MAE no verificado."
        )

    return pares


def obtener_transparencia_valuacion() -> dict:
    """Los 209 pares predicho/real del conjunto de test + resumen agregado, listos para el router.

    Lanza `TransparenciaValuacionError` si el CSV fuente falta, está vacío, o falla la
    verificación de integridad del MAE — el router lo traduce a un 500 explícito.
    """
    pares = _cargar_pares()
    n = len(pares)
    mae_absoluto = sum(abs(p["diferencia_absoluta"]) for p in pares) / n
    mae_porcentual = mae_absoluto / PRECIO_PROMEDIO_CATALOGO_COMPLETO * 100

    return {
        "resumen": {
            "n_muestras": n,
            "mae_absoluto": mae_absoluto,
            "mae_porcentual": mae_porcentual,
            "poblacion_mae_absoluto": (
                f"Conjunto de TEST del KNN de producción ({n} filas, nunca vistas por el modelo "
                f"durante el entrenamiento — Notebook 2, Feature 6.2.4)."
            ),
            "poblacion_mae_porcentual": (
                f"mae_absoluto dividido entre la media de precio del CATÁLOGO COMPLETO elegible "
                f"({N_CATALOGO_COMPLETO} filas: train + test), NO la media de estas {n} filas de "
                f"test — mismo denominador que el 33.4% ya publicado en el paper. Dividir en "
                f"cambio por la media de las {n} filas de test da un número distinto (~32.3%), "
                f"documentado en 3.5.1 para evitar esa confusión."
            ),
        },
        "pares": pares,
    }
