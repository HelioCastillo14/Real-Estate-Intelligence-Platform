"""Identificación de comparables por KNN sobre atributos estructurados (Feature 3.1.1, M2).

Resuelve la invalidación de scope de la WBS original de 3.1.1 (`ST_Distance` de PostGIS): desde
Feature 1.2, `propiedades.geom` es sintético (`ST_GeneratePoints`, solo para visualización, nunca
insumo de modelo) porque inmopanama.com no expone coordenadas reales — ver `CLAUDE.md`,
"M2 comparables". El comparable real es `sklearn.neighbors.KNeighborsRegressor` sobre
`corregimiento` (one-hot) + `bedrooms` + `bathrooms` + `area_m2`, ya entrenado y cerrado en
Notebook 2 (Feature 6.2.4, `notebooks/02_m2_knn_semaforo_rf.ipynb`). Este módulo NO reentrena el
modelo — carga el pickle de producción y expone sus vecinos más cercanos. El cálculo del
semáforo (rango verde/amarillo/rojo sobre esos vecinos) es 3.1.2/3.1.3, no aquí.

**Alcance real del modelo, no solo un detalle de features:** el notebook restringió el pool de
entrenamiento a `tipo_inmueble == "Apartamentos"` (1,140 de 1,177 filas, ~97% del catálogo,
celda 7-8) — no es una feature one-hot, es un filtro de fila. El modelo entrenado por lo tanto
NO tiene ningún comparable de Casas/Edificios/Locales/Terrenos; pedirle comparables de esos
tipos no daría un resultado degradado, daría vecinos de un tipo de inmueble equivocado sin
ninguna señal de error. `buscar_comparables_knn()` valida esto explícitamente en vez de
devolver un resultado silenciosamente incorrecto.

**Zonas soportadas:** las 7 columnas one-hot del pickle (`ZONAS_SOPORTADAS`) — excluye Pedregal
y Parque Lefevre, fuera del pool de entrenamiento por volumen insuficiente para 5-fold CV
(Acta 1.2 §5.3, ya documentado en `CLAUDE.md`). Pedirle un comparable de esas dos zonas no es
un caso silenciosamente degradado tampoco: no existe columna dummy para ellas en el vector de
entrada del modelo, así que se valida y se rechaza explícitamente aquí en vez de dejar que
`pandas`/`sklearn` fallen más abajo con un error menos claro.

**Precios reales de los vecinos:** `KNeighborsRegressor` no expone una API pública para
recuperar el target (`price_usd`) de cada vecino individual — solo `predict()` (el promedio).
Los precios reales de los k vecinos, que es lo que esta tarea necesita exponer, se leen del
atributo interno `knn._y` (fijado por `fit()` con el mismo orden posicional que devuelve
`kneighbors()`). Es un atributo privado de sklearn, no público, pero es la única vía sin
reentrenar ni sin persistir el dataset de entrenamiento por separado del pickle — el pickle de
6.2.4 no guarda esos precios en ningún campo propio (ver hallazgo de umbral desactualizado más
abajo, este es un hallazgo adicional del mismo pickle).

**Hallazgo — el pickle trae el umbral de semáforo desactualizado (ya documentado en 3.1.3, no
un hallazgo nuevo de este módulo):** `knn_semaforo_precio_6_2_4.pkl["umbral_semaforo"]` es
`0.10` (celda 17, sección 4.1 del notebook, el criterio ±10% original). El notebook lo
recalibra en la sección 9.1 (celda 33) contra el residual real del modelo — el umbral final
cerrado es ±1.5×MAE, no ±10% — pero la celda de exportación (celda 28) corre ANTES de esa
recalibración y nunca se re-exportó después. Este módulo NO lee `umbral_semaforo` del pickle
por eso mismo (no calcula semáforo, ver arriba), pero cualquier consumidor de 3.1.2/3.1.3 que sí
lo necesite debe tomar `MULTIPLO_MAE = 1.5` de la sección 9.1 del notebook como valor de
producción, no el campo `umbral_semaforo` del pickle.

**Resto del pickle, verificado contra el notebook — sin más desalineaciones:** `columnas`
(orden de las 10 features, incluye las 7 dummies de zona), `k=5` y el modelo (`n_features_in_
== 10`, `n_neighbors == 5`) coinciden exactamente con las celdas 13/15/28 del notebook. El
escalador (`escalador_knn_6_2_4.pkl`) también coincide: mismas 3 columnas numéricas
(`bedrooms`, `bathrooms`, `area_m2`) que la celda 15. El único campo desalineado del pickle es
`umbral_semaforo`, no hay un segundo hallazgo de esta clase.

**Hallazgo de fuga de datos (batch 3.1.6) y su corrección — auto-comparación con el training
set.** El batch de producción de 3.1.6 valúa el catálogo completo (1,042 filas elegibles), del
cual 833 fueron parte del training set del KNN (`knn._y`). Sin corrección, esas 833 filas se
comparaban contra sí mismas como uno de sus propios 5 comparables (distancia 0, mismo
`price_usd`), inflando "amarillo" a 87.5% frente al 82.3% del paper — confirmado aislando el
subconjunto de 209 filas de test (nunca vistas por el KNN), que reproducía el paper exacto sin
ningún ajuste. Corrección: `buscar_comparables_knn()` acepta un `listing_id` opcional. Si se
provee y coincide con una fila del training set, se excluye esa posición del resultado y se
vuelve a consultar con `k+1` vecinos para no perder un comparable real. El mapeo posición-en-
`knn._y` → `listing_id` no existe en ningún pickle de 6.2.4 (`KNeighborsRegressor` no asocia
identificadores a sus datos de entrenamiento) — se generó y verificó aparte en
`pipeline/scripts/generar_mapeo_listing_id_knn_6_2_4.py`
(`knn_semaforo_precio_6_2_4_listing_ids_train.pkl`), reproduciendo la misma división train/test
del notebook (mismo `RANDOM_STATE=42`) y confirmando que `knn._y[posición]` coincide exactamente
con el `price_usd` real del `listing_id` en esa posición, para las 833 posiciones. Sin
`listing_id` (o con un `listing_id` que no está en el training set — ej. las 209 filas de test,
o una propiedad nueva), el comportamiento es idéntico al de antes de esta corrección: no hay
nada que excluir.
"""

import pickle
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUTA_MODELOS = REPO_ROOT / "pipeline" / "models"
RUTA_KNN = RUTA_MODELOS / "knn_semaforo_precio_6_2_4.pkl"
RUTA_ESCALADOR = RUTA_MODELOS / "escalador_knn_6_2_4.pkl"
RUTA_LISTING_IDS_TRAIN = RUTA_MODELOS / "knn_semaforo_precio_6_2_4_listing_ids_train.pkl"

TIPO_INMUEBLE_SOPORTADO = "Apartamentos"

ZONAS_SOPORTADAS = frozenset({
    "Bella Vista", "Betania", "Costa del Este", "El Cangrejo",
    "Marbella", "Obarrio", "San Francisco",
})


class ComparablesKnnError(ValueError):
    """El input no es evaluable por el modelo KNN de producción (zona o tipo fuera de su pool de entrenamiento)."""


@lru_cache(maxsize=1)
def _cargar_artifacts() -> dict:
    with open(RUTA_KNN, "rb") as f:
        knn_artifact = pickle.load(f)
    with open(RUTA_ESCALADOR, "rb") as f:
        escalador_artifact = pickle.load(f)
    with open(RUTA_LISTING_IDS_TRAIN, "rb") as f:
        listing_ids_train = pickle.load(f)
    return {
        "modelo": knn_artifact["modelo"],
        "columnas": knn_artifact["columnas"],
        "k_default": knn_artifact["k"],
        "escalador": escalador_artifact["escalador"],
        "columnas_numericas": escalador_artifact["columnas_numericas"],
        "posicion_por_listing_id": {lid: pos for pos, lid in enumerate(listing_ids_train)},
    }


def buscar_comparables_knn(
    corregimiento: str,
    bedrooms: float,
    bathrooms: float,
    area_m2: float,
    tipo_inmueble: str = TIPO_INMUEBLE_SOPORTADO,
    k: int | None = None,
    listing_id: int | None = None,
) -> list[dict]:
    """Los k comparables más cercanos (KNN de producción, 6.2.4) a la propiedad dada.

    Devuelve una lista de `k` dicts `{"price_usd": float, "distancia": float}`, ordenados por
    distancia ascendente (vecino más parecido primero) — precios reales del set de entrenamiento,
    sin promediar ni clasificar en semáforo (eso es 3.1.2/3.1.3).

    `listing_id`: opcional — el `listing_id` de la propiedad que se está evaluando. Si coincide
    con una fila del training set del KNN, esa fila se excluye de sus propios comparables (ver
    docstring del módulo, hallazgo de fuga de datos de 3.1.6) y se completa el resultado con un
    6to vecino real en su lugar. Si es `None`, o no coincide con ninguna fila de entrenamiento
    (ej. una de las 209 filas de test, o una propiedad nueva), el comportamiento es exactamente
    el mismo que sin esta corrección.

    Lanza `ComparablesKnnError` si `tipo_inmueble` no es "Apartamentos" o `corregimiento` no está
    en `ZONAS_SOPORTADAS` — el modelo no tiene ningún comparable entrenado para esos casos (ver
    docstring del módulo), no es un resultado que deba degradarse en silencio.
    """
    if tipo_inmueble != TIPO_INMUEBLE_SOPORTADO:
        raise ComparablesKnnError(
            f"El KNN de producción (6.2.4) solo se entrenó sobre tipo_inmueble="
            f"'{TIPO_INMUEBLE_SOPORTADO}' — no hay comparables entrenados para '{tipo_inmueble}'."
        )
    if corregimiento not in ZONAS_SOPORTADAS:
        raise ComparablesKnnError(
            f"'{corregimiento}' no está en el pool de entrenamiento del KNN (Acta 1.2 §5.3 — "
            f"Pedregal/Parque Lefevre excluidos por volumen). Zonas soportadas: "
            f"{sorted(ZONAS_SOPORTADAS)}."
        )

    artifacts = _cargar_artifacts()
    modelo = artifacts["modelo"]
    columnas = artifacts["columnas"]
    escalador = artifacts["escalador"]
    columnas_numericas = artifacts["columnas_numericas"]
    k_vecinos = k if k is not None else artifacts["k_default"]

    posicion_propia = artifacts["posicion_por_listing_id"].get(listing_id) if listing_id is not None else None

    valores_numericos = {"bedrooms": bedrooms, "bathrooms": bathrooms, "area_m2": area_m2}
    fila = {col: 0.0 for col in columnas}
    for col in columnas_numericas:
        fila[col] = valores_numericos[col]
    zona_col = f"zona_{corregimiento}"
    fila[zona_col] = 1.0

    vector_bruto = [fila[col] for col in columnas]
    vector_escalado = list(vector_bruto)
    valores_escalados = escalador.transform([[fila[col] for col in columnas_numericas]])[0]
    for col, valor in zip(columnas_numericas, valores_escalados):
        vector_escalado[columnas.index(col)] = valor

    n_neighbors_consulta = k_vecinos + 1 if posicion_propia is not None else k_vecinos
    distancias, indices = modelo.kneighbors([vector_escalado], n_neighbors=n_neighbors_consulta)

    resultado = [
        {"price_usd": float(modelo._y[idx]), "distancia": float(dist), "_posicion": int(idx)}
        for dist, idx in zip(distancias[0], indices[0])
    ]
    if posicion_propia is not None:
        resultado = [r for r in resultado if r["_posicion"] != posicion_propia][:k_vecinos]

    return [{"price_usd": r["price_usd"], "distancia": r["distancia"]} for r in resultado]
