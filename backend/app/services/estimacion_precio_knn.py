"""Precio estimado y diferencia contra el precio real, a partir de comparables KNN (Feature 3.1.2, M2).

Consume el output de `buscar_comparables_knn()` (Feature 3.1.1, `comparables_knn.py`) — no
llama al modelo ni carga ningún pickle aquí, es lógica de dominio pura sobre la lista de
comparables ya resuelta. NO asigna semáforo (verde/amarillo/rojo) — eso es 3.1.3, que necesita
el MAE real del modelo (sección 9.1 del notebook) para calibrar el umbral, dato que esta función
no tiene ni debe tener.

**Método de cálculo, confirmado contra el notebook (`notebooks/02_m2_knn_semaforo_rf.ipynb`,
celda 15) y no asumido:** `KNeighborsRegressor(n_neighbors=K_VECINOS)` se instancia sin
`weights` — el default de sklearn es `weights="uniform"`, es decir `predict()` es el promedio
simple (no ponderado por distancia) de los `price_usd` de los k vecinos. Ningún punto del
notebook pondera manualmente por `distancia` en ninguna etapa (ni en el KNN de producción ni en
la comparación con RF) — la columna `distancia` que devuelve `buscar_comparables_knn()` no entra
en este cálculo, solo se usa aquí para reportarla junto a cada comparable si el caller la
necesita para otro propósito.

**Signo de la diferencia, mismo convenio que el notebook (celda 33, sección 9.1):**
`diferencia_absoluta = precio_real - precio_estimado` — positivo significa que la propiedad pagó
(o pide) más que el estimado, negativo que pagó menos. `semaforo_final()` de 3.1.3 usa
literalmente este residual con este mismo signo contra el MAE, no lo inviertas en la siguiente
tarea.

**`precio_real=None` es un caso soportado, no un caso de error:** una propiedad nueva sin precio
listado todavía (ej. previo a que el usuario/agente lo defina) es un uso real del semáforo —
"¿en qué rango debería listarse esto?" es tan válido como "¿este precio ya publicado es bueno?".
Cuando `precio_real` es `None`, la función devuelve `precio_estimado` igual, y
`diferencia_absoluta`/`diferencia_porcentual` en `None` en vez de forzar un valor falso.
"""

K_VECINOS_ESPERADO = 5


class EstimacionPrecioError(ValueError):
    """No hay comparables suficientes para estimar un precio (lista vacía)."""


def calcular_precio_estimado(
    comparables: list[dict],
    precio_real: float | None = None,
    k_esperado: int = K_VECINOS_ESPERADO,
) -> dict:
    """Precio estimado (promedio simple de `price_usd` de `comparables`) y diferencia contra
    `precio_real`, si se provee.

    `comparables`: output de `buscar_comparables_knn()` (3.1.1) — lista de
    `{"price_usd": float, "distancia": float}`. Lanza `EstimacionPrecioError` si está vacía (no
    hay forma de estimar sin comparables). Si tiene menos de `k_esperado` elementos (cobertura
    insuficiente — ej. una zona/tipo con pocos listados), NO falla: promedia lo que hay y lo
    marca explícitamente en `cobertura_insuficiente`/`n_comparables`, para que el caller decida
    si esa estimación es confiable con menos vecinos que los k=5 de diseño del modelo.

    Devuelve:
    - `precio_estimado`: promedio simple de los `price_usd` de `comparables`.
    - `n_comparables`, `k_esperado`, `cobertura_insuficiente`: contexto de cuántos vecinos
      sostienen la estimación.
    - `precio_real`: eco del input, para que el caller no tenga que cargarlo aparte.
    - `diferencia_absoluta` (`precio_real - precio_estimado`) y `diferencia_porcentual`
      (`diferencia_absoluta / precio_estimado`): `None` si `precio_real` es `None`.
    """
    if not comparables:
        raise EstimacionPrecioError(
            "No se puede estimar un precio sin comparables (lista vacía)."
        )

    n_comparables = len(comparables)
    precio_estimado = sum(c["price_usd"] for c in comparables) / n_comparables

    diferencia_absoluta = None
    diferencia_porcentual = None
    if precio_real is not None:
        diferencia_absoluta = precio_real - precio_estimado
        diferencia_porcentual = diferencia_absoluta / precio_estimado

    return {
        "precio_estimado": precio_estimado,
        "n_comparables": n_comparables,
        "k_esperado": k_esperado,
        "cobertura_insuficiente": n_comparables < k_esperado,
        "precio_real": precio_real,
        "diferencia_absoluta": diferencia_absoluta,
        "diferencia_porcentual": diferencia_porcentual,
    }
