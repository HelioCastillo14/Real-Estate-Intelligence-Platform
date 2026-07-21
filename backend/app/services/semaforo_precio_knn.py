"""Etiqueta de semáforo (verde/amarillo/rojo) a partir del residual de 3.1.2 (Feature 3.1.3, M2).

**Corrección obligatoria de esta tarea, ya documentada en 3.1.1/3.1.2, no opcional:**
`pipeline/models/knn_semaforo_precio_6_2_4.pkl["umbral_semaforo"]` es `0.10` (±10% del precio
predicho) — ese campo se serializó en la celda 28 del notebook (sección 4.1), ANTES de que la
celda 33 (sección 9.1) recalibrara el umbral contra el residual real. Ese 0.10 es un artifact
desactualizado: el paper ya publicado usa ±1.5×MAE, no ±10%. Este módulo NO lee
`umbral_semaforo` del pickle en ningún punto — `MULTIPLO_MAE` y `MAE_KNN_TEST` están fijados
aquí explícitamente, re-serializados desde el notebook, no leídos del pickle desactualizado.

**`MAE_KNN_TEST` — reproducido desde el dataset real, no copiado del string redondeado del
notebook.** La celda 30/33 del notebook imprime `$187,543` (formato `,.0f`, redondeado). Para no
propagar ese redondeo al umbral de producción, reproduje el pipeline completo (mismas celdas
2/4/8/13/15, mismo `RANDOM_STATE=42`) contra
`pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv` y obtuve el valor exacto de
`mean_absolute_error(y_test, pred_knn_test)`: `187543.4765550239` — coincide con el `$187,543`
impreso (celda 30) y con `$281,315` de `1.5×MAE` (celda 33), confirmando que la reproducción es
correcta y no una cifra distinta.

**Lógica de las 3 categorías, confirmada contra la celda 33 (sección 9.1) del notebook, no
asumida:**
```
residual = precio_real - precio_estimado   # mismo signo que diferencia_absoluta de 3.1.2
if residual > 1.5 * MAE:   "rojo"     # pagó de más -> sobrevalorado
if residual < -1.5 * MAE:  "verde"    # pagó de menos -> buen precio
else:                       "amarillo" # dentro de la banda de incertidumbre del modelo
```
**Lectura correcta de "amarillo" (celda 32, sección 9.1 del notebook — no es "precio justo"):**
significa que, dado el error típico del modelo (MAE ~$187,543), no hay evidencia estadística
suficiente para afirmar que la propiedad está sobre- o subvalorada. Con un MAE de ese tamaño, la
banda ±1.5×MAE (±$281,315) es ancha a propósito — el notebook reporta 82.3% amarillo / 9.1% verde
/ 8.6% rojo sobre el set de test (celda 33), y esta función debe reproducir esa misma
distribución dado el mismo residual, no una más ajustada.

**Decisión explícita — qué hace esta función cuando `cobertura_insuficiente=True` (3.1.2, menos
de k=5 comparables):** calcula el semáforo igual (opción b: flag de confianza reducida), no lo
sustituye por una categoría especial tipo "sin_evaluar" (opción c). Precedente del propio
proyecto (`CLAUDE.md`, decisión de Zone Health): el caso análogo es **Pedregal**, no Costa del
Este. Pedregal tiene datos reales pero un componente débil y "se calcula, no se muestra" — es
una decisión de la capa de presentación, no de la capa de cómputo. Costa del Este, en cambio, no
recibe ningún score compuesto porque le faltan estructuralmente 4 de 5 dimensiones (input
inexistente, no un input débil). Acá, `cobertura_insuficiente=True` significa "hay 1-4
comparables reales, no cero" — 3.1.2 ya rechaza la lista vacía con `EstimacionPrecioError`, así
que el caso de esta función nunca es "sin datos", siempre es "datos más delgados de lo ideal".
Eso es estructuralmente el caso de Pedregal (input débil), no el de Costa del Este (input
ausente) — de ahí que la función SIGA calculando la categoría, marcándola con
`confianza_reducida=True` para que la capa de presentación (API/frontend, no esta función) decida
si la oculta, la advierte, o la muestra igual — el mismo punto de decisión diferido que ya usa el
proyecto para Pedregal en Zone Health.
"""

MULTIPLO_MAE = 1.5
MAE_KNN_TEST = 187543.4765550239


class SemaforoPrecioError(ValueError):
    """No hay `diferencia_absoluta` (precio_real no fue provisto en 3.1.2) — no hay residual que evaluar."""


def calcular_semaforo_precio(estimacion: dict, multiplo_mae: float = MULTIPLO_MAE) -> dict:
    """Categoría de semáforo (verde/amarillo/rojo) a partir del output de `calcular_precio_estimado()` (3.1.2).

    Lanza `SemaforoPrecioError` si `estimacion["diferencia_absoluta"]` es `None` — sin
    `precio_real` no hay residual que comparar contra el umbral, y el semáforo pierde su
    definición (a diferencia de 3.1.2, donde `precio_real=None` es un caso válido para solo
    estimar valor).

    Devuelve el desglose completo, no solo el string, para que la asignación sea auditable:
    - `categoria`: "verde" | "amarillo" | "rojo".
    - `residual`, `mae_knn_test`, `multiplo_mae`, `umbral_usado` (`multiplo_mae * mae_knn_test`):
      los términos exactos de la comparación que produjo `categoria`.
    - `cobertura_insuficiente`, `confianza_reducida` (mismo valor, alias explícito): eco de
      3.1.2 — la categoría se calculó igual (ver docstring del módulo), pero con menos
      comparables que los k=5 de diseño del modelo.
    - `n_comparables`, `k_esperado`: eco de 3.1.2, para trazabilidad completa sin tener que
      volver a consultar el dict de entrada.
    """
    residual = estimacion["diferencia_absoluta"]
    if residual is None:
        raise SemaforoPrecioError(
            "No se puede calcular el semáforo sin precio_real "
            "(diferencia_absoluta es None en la estimación de 3.1.2)."
        )

    umbral_usado = multiplo_mae * MAE_KNN_TEST
    if residual > umbral_usado:
        categoria = "rojo"
    elif residual < -umbral_usado:
        categoria = "verde"
    else:
        categoria = "amarillo"

    cobertura_insuficiente = estimacion["cobertura_insuficiente"]

    return {
        "categoria": categoria,
        "residual": residual,
        "mae_knn_test": MAE_KNN_TEST,
        "multiplo_mae": multiplo_mae,
        "umbral_usado": umbral_usado,
        "cobertura_insuficiente": cobertura_insuficiente,
        "confianza_reducida": cobertura_insuficiente,
        "n_comparables": estimacion["n_comparables"],
        "k_esperado": estimacion["k_esperado"],
    }
