"""Carga de valuacion_segmento_kmeans (Feature 3.2.5) — batch de producción del segmento KMeans.

Fuente de datos: tabla `propiedades` real (Supabase), mismo criterio que 3.1.6. Modelo ya
entrenado y cerrado (Notebook 3, Feature 6.2.5, `notebooks/03_m2_kmeans_segmentacion.ipynb`):
`pipeline/models/kmeans_segmentacion_6_2_5.pkl` + `escalador_kmeans_6_2_5.pkl`. Este script NO
reentrena — usa `modelo.predict()`, nunca `fit_predict()`.

**Features reales, confirmadas contra el notebook (celda 8), NO las mismas del KNN de 3.1.1 —
verificado, no asumido por similitud de nombre:**
`FEATURES_CLUSTERING = ["price_usd", "area_m2", "precio_por_m2", "bedrooms", "bathrooms"]`, las
5 escaladas con `StandardScaler` (a diferencia del KNN de 6.2.4, que solo escalaba 3 de sus 10
columnas — acá se escalan las 5, ninguna es one-hot). `corregimiento` NO es feature de
clustering (celda 7: el objetivo es segmentar por tipo de propiedad en el mercado, no
redescubrir la partición geográfica). `precio_por_m2 = price_usd / area_m2` es derivada, se
calcula aquí igual que en la celda 4 del notebook — no viene precalculada en `propiedades`.

**Universo elegible — mismo filtro que 6.2.4/3.1.6, confirmado contra la celda 1/4 del notebook
("mismo criterio que 6.2.4"), no un criterio distinto para KMeans:** corregimiento en las 7 zonas
soportadas (excluye Pedregal/Parque Lefevre, Acta 1.2 §5.3) + `tipo_inmueble == "Apartamentos"` +
`area_m2`/`price_usd` no nulos + `precio_no_evaluable = false`. Reusa `ZONAS_SOPORTADAS` de
`comparables_knn.py` (3.1.1) en vez de redeclarar la misma lista de 7 zonas — es literalmente el
mismo conjunto, no una coincidencia a mantener sincronizada a mano en dos archivos.

**¿Aplica el riesgo de fuga de datos de 3.1.6 (KNN)? NO — evaluado explícitamente, no asumido
por analogía.** La fuga de 3.1.6 ocurría porque `KNeighborsRegressor.kneighbors()` busca los k
vecinos más cercanos DENTRO de los datos de entrenamiento almacenados — si la propia fila de
consulta era uno de esos datos, se encontraba a sí misma (distancia 0). `KMeans.predict()` NO
busca vecinos entre puntos de entrenamiento almacenados: calcula la distancia de la fila de
consulta contra los `k=2` CENTROIDES ya fijados por `fit()` (el promedio de cada cluster, no un
punto de dato individual) y asigna el más cercano — un cálculo de distancia a un punto agregado,
no a otro dato crudo. Ninguna fila puede "encontrarse a sí misma" en un centroide salvo el caso
degenerado de un cluster de un solo miembro (no aplica acá: 662 y 380 miembros). Además, a
diferencia de 6.2.4 (que sí dividió train/test 80/20 para medir generalización supervisada),
6.2.5 nunca dividió el dataset — `fit_predict()` (celda 14) ya corrió sobre las 1,042 filas
completas y esos 662/380 SON la asignación de producción ya publicada, no una medición de
generalización sobre datos no vistos. Evaluar aquí exactamente esa misma población con
`predict()` (en vez de `fit_predict()`) es la forma correcta de reproducir esos mismos labels
sin reentrenar — no hay una partición de test cuyo resultado "puro" debamos proteger de sesgo,
porque nunca existió tal partición para este modelo. Conclusión: sin corrección de fuga
necesaria para este batch.

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`: la
llamada a `cargar()` queda comentada a propósito, requiere habilitarla con confirmación explícita
del usuario (mismo protocolo que el resto de scripts de carga del repo).
"""

import os
import pickle
import sys
from collections import Counter
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
RUTA_MODELOS = REPO_ROOT / "pipeline" / "models"
RUTA_KMEANS = RUTA_MODELOS / "kmeans_segmentacion_6_2_5.pkl"
RUTA_ESCALADOR = RUTA_MODELOS / "escalador_kmeans_6_2_5.pkl"

sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.services.comparables_knn import ZONAS_SOPORTADAS  # noqa: E402

REFERENCIA_NOTEBOOK = {0: 662, 1: 380}  # celda 14, sobre las mismas 1,042 filas de entrenamiento
TIPO_INMUEBLE_SOPORTADO = "Apartamentos"

SELECT_ELEGIBLES_SQL = """
    select listing_id, price_usd, area_m2, bedrooms, bathrooms
    from propiedades
    where corregimiento = ANY(%(zonas)s)
      and tipo_inmueble = %(tipo)s
      and area_m2 is not null
      and area_m2 > 0
      and precio_no_evaluable = false
      and price_usd is not null
"""

INSERT_SQL = """
    insert into valuacion_segmento_kmeans (listing_id, cluster_id)
    values (%(listing_id)s, %(cluster_id)s)
"""


def cargar_modelo() -> dict:
    with open(RUTA_KMEANS, "rb") as f:
        kmeans_artifact = pickle.load(f)
    with open(RUTA_ESCALADOR, "rb") as f:
        escalador_artifact = pickle.load(f)
    assert kmeans_artifact["features"] == escalador_artifact["features"], (
        "El orden de features del modelo y del escalador no coincide — no se puede armar el "
        "vector de entrada de forma confiable."
    )
    return {
        "modelo": kmeans_artifact["modelo"],
        "features": kmeans_artifact["features"],
        "escalador": escalador_artifact["escalador"],
    }


def obtener_elegibles(conn) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SELECT_ELEGIBLES_SQL, {"zonas": list(ZONAS_SOPORTADAS), "tipo": TIPO_INMUEBLE_SOPORTADO})
        return [dict(fila) for fila in cur.fetchall()]


def calcular_filas(elegibles: list[dict], modelo_artifacts: dict) -> tuple[list[dict], list[dict]]:
    """Corre `modelo.predict()` (NO `fit_predict()`) sobre cada propiedad elegible.

    Devuelve `(filas_ok, fallos)` — `filas_ok` son dicts listos para `INSERT_SQL`, `fallos` son
    `{"listing_id":..., "motivo":...}`. Nunca lanza por una fila individual.
    """
    modelo = modelo_artifacts["modelo"]
    features = modelo_artifacts["features"]
    escalador = modelo_artifacts["escalador"]

    filas_ok = []
    fallos = []
    for prop in elegibles:
        try:
            precio_por_m2 = float(prop["price_usd"]) / float(prop["area_m2"])
            valores = {
                "price_usd": float(prop["price_usd"]),
                "area_m2": float(prop["area_m2"]),
                "precio_por_m2": precio_por_m2,
                "bedrooms": float(prop["bedrooms"]),
                "bathrooms": float(prop["bathrooms"]),
            }
            vector = [[valores[f] for f in features]]
            vector_esc = escalador.transform(vector)
            cluster_id = int(modelo.predict(vector_esc)[0])
        except Exception as exc:  # noqa: BLE001 — batch no debe abortar por una fila
            fallos.append({"listing_id": prop["listing_id"], "motivo": f"{type(exc).__name__}: {exc}"})
            continue

        filas_ok.append({"listing_id": prop["listing_id"], "cluster_id": cluster_id})
    return filas_ok, fallos


def reportar_dry_run(filas_ok: list[dict], fallos: list[dict]) -> None:
    total = len(filas_ok)
    conteo = Counter(f["cluster_id"] for f in filas_ok)
    print(f"Total de filas a insertar: {total}")
    print(f"Total de fallos de cómputo: {len(fallos)}")
    print()

    print("Distribución de cluster_id:")
    for cid in (0, 1):
        n = conteo.get(cid, 0)
        pct = (n / total * 100) if total else 0.0
        print(f"  cluster {cid}   n={n:4d}  ({pct:5.1f}%)")
    print()

    print("Referencia del notebook (fit_predict() sobre las mismas 1,042 filas de entrenamiento "
          "— misma población en este caso, no train/test como en 6.2.4):")
    for cid in (0, 1):
        n_ref = REFERENCIA_NOTEBOOK[cid]
        n_batch = conteo.get(cid, 0)
        pct_ref = n_ref / sum(REFERENCIA_NOTEBOOK.values()) * 100
        pct_batch = (n_batch / total * 100) if total else 0.0
        delta = pct_batch - pct_ref
        print(f"  cluster {cid}   notebook={pct_ref:5.1f}% (n={n_ref})   batch={pct_batch:5.1f}% (n={n_batch})   delta={delta:+5.1f}pp")
    print()

    if fallos:
        print(f"Fallos de cómputo ({len(fallos)}):")
        for f in fallos[:50]:
            print(f"  listing_id={f['listing_id']}  {f['motivo']}")
        if len(fallos) > 50:
            print(f"  ... y {len(fallos) - 50} más")
    else:
        print("Sin fallos de cómputo.")


def cargar(filas: list[dict]) -> None:
    """INSERT real, transacción única. NO se llama automáticamente — ver bloque __main__."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, INSERT_SQL, filas)
        conn.commit()
        print(f"Insertadas {len(filas)} filas en valuacion_segmento_kmeans.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    modelo_artifacts = cargar_modelo()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        elegibles = obtener_elegibles(conn)
    finally:
        conn.close()

    print(f"Propiedades elegibles (zona soportada + Apartamentos + datos completos): {len(elegibles)}")
    print()

    filas_ok, fallos = calcular_filas(elegibles, modelo_artifacts)
    reportar_dry_run(filas_ok, fallos)

    # cargar(filas_ok)
