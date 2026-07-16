"""Carga de valuacion_semaforo_knn (Feature 3.1.6) — batch de producción del semáforo KNN.

Fuente de datos: tabla `propiedades` real (Supabase), no el CSV de `pipeline/data/processed/` —
a diferencia de los notebooks de 6.2.x, este batch valúa el catálogo tal como vive hoy en
producción. Encadena `evaluar_precio_propiedad()` (3.1.5, `backend/app/services/valuacion_knn.py`)
por fila, que a su vez encadena 3.1.1 → 3.1.2 → 3.1.3. Esquema de destino:
`supabase/migrations/20260715040004_scores_valuacion_compatibilidad_sesiones.sql` (5 columnas
originales) + `20260715040006_valuacion_semaforo_knn_agrega_confianza.sql` (2 columnas de
diagnóstico), ambas ya aplicadas y verificadas.

**Universo elegible — 3 filtros, no 2.** La especificación de esta tarea pide corregimiento con
columna dummy en el modelo (excluye Pedregal/Parque Lefevre) + `tipo_inmueble == "Apartamentos"`.
Verificado contra la tabla real: ese filtro de 2 condiciones deja pasar 48 filas de
`corregimiento = 'zona_no_determinada'` — no es Pedregal ni Parque Lefevre, así que "not in
(Pedregal, Parque Lefevre)" no las excluye, pero tampoco es una de las 7 zonas soportadas por el
KNN (`ZONAS_SOPORTADAS` de `comparables_knn.py`). Se filtra explícitamente por pertenencia a
`ZONAS_SOPORTADAS` (positivo), no por exclusión de las 2 zonas sin volumen (negativo) — evita
colar esa tercera categoría. Con ese filtro correcto: 1,076 filas. De esas, 34 tienen datos
rotos para el modelo (`area_m2 IS NULL`, `precio_no_evaluable = true`, o `price_usd IS NULL`) —
se excluyen del universo a intentar (no tiene sentido llamar al pipeline con un precio_real que
la tabla ya marca como no evaluable) y se cuentan aparte, no como fallos de cómputo. Universo
final a intentar: 1,042 filas — coincide exactamente con el tamaño del dataset filtrado del
Notebook 2 (Feature 6.2.4, confirmado también en `pipeline/scripts/analisis_mae_por_zona_3_1_4.py`)
porque son la misma población con las mismas reglas de filtrado, verificado, no una coincidencia
asumida.

**Fallos de cómputo capturados explícitamente, mismo patrón que 2.1.3
(`pipeline/scripts/generar_embeddings_faltantes_2_1_3.py`):** cualquier excepción de
`evaluar_precio_propiedad()` (`ComparablesKnnError`, `EstimacionPrecioError`,
`SemaforoPrecioError`, o cualquier otra) se captura por fila, se registra `listing_id` + tipo +
mensaje, y el batch continúa — nunca aborta por una sola fila.

**Verificación contra el paper ANTES de conectar a Supabase, mismo patrón que
`cargar_valuacion_quality_scorer.py`:** el paper reporta la distribución de categoría de semáforo
sobre el SET DE TEST del Notebook 2 (n=209, 20% de las 1,042 filas: 82.3% amarillo/172,
9.1% verde/19, 8.6% rojo/18) — no sobre las 1,042 filas completas. Este batch valúa las 1,042
(train + test), así que la comparación no es estrictamente población-a-población, es una
verificación de coherencia según lo pedido en la tarea, no una réplica exacta esperada.

**Hallazgo real, encontrado corriendo el batch, no hipotético — REGLA DE ORO DEL PROYECTO
ACTIVADA, ver el bloque `if __name__ == "__main__"` y el reporte de la sesión:** de las 1,042
filas, 833 fueron parte del SET DE ENTRENAMIENTO del KNN (`knn._y`, los mismos datos que
`buscar_comparables_knn()` consulta). Para esas 833 filas, la propiedad que se está valuando es
literalmente uno de sus propios 5 comparables (distancia 0, mismo `price_usd`) — el modelo nunca
excluye la fila de consulta de su propio set de vecinos porque `evaluar_precio_propiedad()` no
tiene forma de saber que la propiedad que le pasan ya está en el training set del pickle. Esto
sesga el residual hacia 0 para esas 833 filas (uno de 5 vecinos es un match perfecto), inflando
"amarillo" de forma artificial frente al 82.3% del paper, que sí midió sobre out-of-sample puro
(el 20% de test que el modelo nunca vio). No se corrige en este script — se documenta y se
reporta en el dry-run, la decisión de cómo tratarlo (excluir train del batch, aceptar el sesgo,
u otra opción) es del usuario, no de este script.

NO SE EJECUTA CONTRA SUPABASE AUTOMÁTICAMENTE — ver bloque `if __name__ == "__main__"`: la
llamada a `cargar()` queda comentada a propósito, requiere habilitarla con confirmación explícita
del usuario (mismo protocolo que el resto de scripts de carga del repo).
"""

import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.comparables_knn import ZONAS_SOPORTADAS, ComparablesKnnError  # noqa: E402
from app.services.estimacion_precio_knn import EstimacionPrecioError  # noqa: E402
from app.services.semaforo_precio_knn import SemaforoPrecioError  # noqa: E402
from app.services.valuacion_knn import evaluar_precio_propiedad  # noqa: E402

REFERENCIA_PAPER = {"verde": (19, 0.091), "amarillo": (172, 0.823), "rojo": (18, 0.086)}
N_TEST_PAPER = 209
TOLERANCIA_PCT_PUNTOS = 5.0  # puntos porcentuales — umbral de "desviación notable", no del paper

SELECT_ELEGIBLES_SQL = """
    select listing_id, corregimiento, tipo_inmueble, bedrooms, bathrooms, area_m2, price_usd
    from propiedades
    where corregimiento = ANY(%(zonas)s)
      and tipo_inmueble = 'Apartamentos'
      and area_m2 is not null
      and precio_no_evaluable = false
      and price_usd is not null
"""

INSERT_SQL = """
    insert into valuacion_semaforo_knn (
        listing_id, precio_predicho, categoria_semaforo, mae_referencia, multiplo_mae,
        confianza_reducida, n_comparables
    ) values (
        %(listing_id)s, %(precio_predicho)s, %(categoria_semaforo)s, %(mae_referencia)s,
        %(multiplo_mae)s, %(confianza_reducida)s, %(n_comparables)s
    )
"""


def obtener_elegibles(conn) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SELECT_ELEGIBLES_SQL, {"zonas": list(ZONAS_SOPORTADAS)})
        return [dict(fila) for fila in cur.fetchall()]


def calcular_filas(elegibles: list[dict]) -> tuple[list[dict], list[dict]]:
    """Corre evaluar_precio_propiedad() sobre cada propiedad elegible.

    Devuelve `(filas_ok, fallos)` — `filas_ok` son dicts listos para `INSERT_SQL`, `fallos` son
    `{"listing_id":..., "tipo_error":..., "motivo":...}`. Nunca lanza por una fila individual.
    """
    filas_ok = []
    fallos = []
    for prop in elegibles:
        try:
            resultado = evaluar_precio_propiedad(
                listing_id=prop["listing_id"],
                corregimiento=prop["corregimiento"],
                bedrooms=float(prop["bedrooms"]),
                bathrooms=float(prop["bathrooms"]),
                area_m2=float(prop["area_m2"]),
                precio_real=float(prop["price_usd"]),
                tipo_inmueble=prop["tipo_inmueble"],
            )
        except (ComparablesKnnError, EstimacionPrecioError, SemaforoPrecioError) as exc:
            fallos.append({
                "listing_id": prop["listing_id"], "tipo_error": type(exc).__name__, "motivo": str(exc),
            })
            continue
        except Exception as exc:  # noqa: BLE001 — batch no debe abortar por una fila, se registra igual
            fallos.append({
                "listing_id": prop["listing_id"], "tipo_error": f"{type(exc).__name__} (inesperado)",
                "motivo": str(exc),
            })
            continue

        registro = resultado["registro_db"]
        diagnostico = resultado["diagnostico"]
        filas_ok.append({
            **registro,
            "confianza_reducida": diagnostico["confianza_reducida"],
            "n_comparables": diagnostico["n_comparables"],
            "corregimiento": prop["corregimiento"],  # solo para el reporte del dry-run, no es columna de INSERT_SQL
        })
    return filas_ok, fallos


def reportar_dry_run(filas_ok: list[dict], fallos: list[dict]) -> None:
    total = len(filas_ok)
    conteo = Counter(f["categoria_semaforo"] for f in filas_ok)
    print(f"Total de filas a insertar: {total}")
    print(f"Total de fallos de cómputo: {len(fallos)}")
    print()

    print("Distribución de categoria_semaforo:")
    for cat in ("verde", "amarillo", "rojo"):
        n = conteo.get(cat, 0)
        pct = (n / total * 100) if total else 0.0
        print(f"  {cat:10s} n={n:4d}  ({pct:5.1f}%)")
    print()

    print(f"Referencia del paper (set de TEST del Notebook 2, n={N_TEST_PAPER} — no la misma "
          f"población que este batch, ver docstring del módulo):")
    desviacion_notable = False
    for cat in ("verde", "amarillo", "rojo"):
        n_paper, pct_paper = REFERENCIA_PAPER[cat]
        n_batch = conteo.get(cat, 0)
        pct_batch = (n_batch / total * 100) if total else 0.0
        delta = pct_batch - pct_paper * 100
        marca = ""
        if abs(delta) > TOLERANCIA_PCT_PUNTOS:
            desviacion_notable = True
            marca = "  <-- DESVIACIÓN > 5 puntos porcentuales"
        print(f"  {cat:10s} paper={pct_paper*100:5.1f}% (n={n_paper})  batch={pct_batch:5.1f}% (n={n_batch})  "
              f"delta={delta:+5.1f}pp{marca}")
    print()

    reducida = [f for f in filas_ok if f["confianza_reducida"]]
    pct_reducida = (len(reducida) / total * 100) if total else 0.0
    print(f"Filas con confianza_reducida=True: {len(reducida)} de {total} ({pct_reducida:.1f}%)")
    if reducida:
        por_zona = Counter(f["corregimiento"] for f in reducida)
        print("  por corregimiento:")
        for zona, n in por_zona.most_common():
            print(f"    {zona:16s} {n}")
    print()

    if fallos:
        print(f"Fallos de cómputo ({len(fallos)}):")
        for f in fallos[:50]:
            print(f"  listing_id={f['listing_id']}  {f['tipo_error']}: {f['motivo']}")
        if len(fallos) > 50:
            print(f"  ... y {len(fallos) - 50} más")
    else:
        print("Sin fallos de cómputo.")
    print()

    if desviacion_notable:
        print("REGLA DE ORO: la distribución se desvía más de 5 puntos porcentuales del paper en "
              "al menos una categoría. NO se procede a insertar sin decisión explícita del "
              "usuario — ver el hallazgo de sesgo por auto-comparable (train set) en el docstring "
              "del módulo antes de decidir.")


def cargar(filas: list[dict]) -> None:
    """INSERT real, transacción única. NO se llama automáticamente — ver bloque __main__."""
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, INSERT_SQL, filas)
        conn.commit()
        print(f"Insertadas {len(filas)} filas en valuacion_semaforo_knn.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        elegibles = obtener_elegibles(conn)
    finally:
        conn.close()

    print(f"Propiedades elegibles (zona soportada + Apartamentos + datos completos): {len(elegibles)}")
    print()

    filas_ok, fallos = calcular_filas(elegibles)
    reportar_dry_run(filas_ok, fallos)

    # cargar(filas_ok)
