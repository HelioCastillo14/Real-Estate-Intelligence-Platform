"""Orquestación end-to-end de la valuación KNN (Feature 3.1.5, M2): atributos crudos -> registro
listo para `valuacion_semaforo_knn`.

Encadena `buscar_comparables_knn()` (3.1.1, `comparables_knn.py`) ->
`calcular_precio_estimado()` (3.1.2, `estimacion_precio_knn.py`) -> `calcular_semaforo_precio()`
(3.1.3, `semaforo_precio_knn.py`). No llama a ninguna de las tres de nuevo por su cuenta ni
reimplementa su lógica — combina sus outputs. No conecta a Supabase: 3.1.6 es quien llama esta
función en batch y hace el `INSERT`.

**Módulo nuevo, no una función agregada a 3.1.1/2/3 — decisión explícita.** Cada uno de esos
tres módulos tiene una responsabilidad propia y aislada (comparables / estimación / semáforo),
igual que M1 en `notebooks/05_m3_nlp_orchestration.ipynb` separa `m1_buscar_matches()` de
`m2_enriquecer_semaforo()` de `orquestar_m3()` — la orquestación es su propia capa, no vive
dentro de ninguno de los pasos que orquesta. Agregarla a uno de los tres módulos existentes
crearía una dependencia circular de facto (ese módulo importando a los otros dos) sin necesidad.

**Referencia de diseño revisada, NO copiada literal — dos diferencias deliberadas frente a
`m2_enriquecer_semaforo()` (Notebook 5, Feature 6.2.7, celda 8):**

1. **Ese prototipo usa `knn_artifact["umbral_semaforo"]` (el 0.10 desactualizado del pickle,
   celda 28 de 6.2.4) contra un residual porcentual** — es el mismo hallazgo de umbral
   desactualizado ya corregido en 3.1.1-3.1.3, sin corregir todavía en el contrato v0 de M3 (es
   un prototipo "v0 — sujeto a revisión en Épica 4", no el pipeline de producción de 3.1.6). Esta
   orquestación usa `calcular_semaforo_precio()` (3.1.3), que fija `MAE_KNN_TEST` y
   `MULTIPLO_MAE=1.5` explícitamente y nunca lee ese campo del pickle — no se hereda el error.

2. **`cobertura_insuficiente` significa algo distinto en cada contrato — no es el mismo concepto
   con el mismo nombre.** En `m2_enriquecer_semaforo()`, `cobertura_insuficiente=True` es un
   chequeo ESTRUCTURAL previo al modelo (zona sin columna dummy, o `tipo_inmueble` != Apartamento)
   — cero comparables posibles, ni se intenta correr el modelo. En esta cadena (3.1.1-3.1.3), ese
   mismo caso estructural ya se resuelve como una excepción (`ComparablesKnnError`, lanzada por
   `buscar_comparables_knn()`) — nunca llega a devolver un dict con un flag, se propaga como
   error real (ver más abajo). El `cobertura_insuficiente`/`confianza_reducida` que SÍ produce
   esta cadena (3.1.2/3.1.3) es un caso distinto y más suave: la zona/tipo SÍ es válida y el
   modelo SÍ corrió, pero devolvió menos de k=5 comparables (ej. combinación
   zona+bedrooms+bathrooms+area_m2 poco común). Tratar ambos casos bajo el mismo nombre habría
   sido perder la distinción real entre "no se puede evaluar en absoluto" y "se evaluó, con menos
   evidencia de la ideal" — mismo tipo de distinción que ya usa el proyecto entre Costa del Este
   (sin score, input ausente) y Pedregal (se calcula, input débil) en Zone Health.

**Propagación de errores (especificación 4 de esta tarea):** `evaluar_precio_propiedad()` NO
envuelve la llamada a `buscar_comparables_knn()` en un `try/except` — si la zona no tiene columna
dummy o el tipo no es "Apartamentos", `ComparablesKnnError` sube tal cual hasta el caller (3.1.6),
con su mensaje ya descriptivo (ver `comparables_knn.py`). Ensamblar un dict de error a mano aquí
sería duplicar información que la excepción ya trae, y arriesgaría que 3.1.6 la trate como un
resultado válido en vez de un caso a loguear y saltar.

**Schema real de `valuacion_semaforo_knn`, verificado contra
`supabase/migrations/20260715040004_scores_valuacion_compatibilidad_sesiones.sql` (no ejecutada
contra Supabase todavía, pero es el DDL aprobado — Ajuste_WBS_1_5_4_Esquema_Scores.md):**
```
listing_id           bigint primary key references propiedades(listing_id)
precio_predicho       numeric not null
categoria_semaforo    text not null check (in ('verde', 'amarillo', 'rojo'))
mae_referencia        numeric not null
multiplo_mae          numeric not null default 1.5
fecha_carga           timestamp not null default now()   -- no lo genera esta función, tiene DB default
```
**Hallazgo — la tabla NO tiene columna para `confianza_reducida` ni `n_comparables`.** El
comentario de la migración (línea 50-53) explica por qué `mae_referencia`/`multiplo_mae` se
guardan por fila (auditabilidad si el umbral se recalibra), pero no dice nada de cobertura
reducida — no es una omisión de esta tarea, es el schema tal como está aprobado. Por eso
`evaluar_precio_propiedad()` devuelve dos sub-dicts separados en vez de uno solo:
`registro_db` (mapea 1:1 a las 5 columnas insertables, sin transformación adicional para 3.1.6)
y `diagnostico` (todo lo que NO tiene columna: `confianza_reducida`, `n_comparables`,
`k_esperado`, `umbral_usado`, `diferencia_absoluta`, `diferencia_porcentual`). Ninguno de los dos
se descarta en silencio — es 3.1.6 quien decide si usa `diagnostico` para loguear/filtrar filas
de confianza reducida antes del `INSERT`, no esta función.

**`precio_real` es obligatorio aquí, a diferencia de `calcular_precio_estimado()` (3.1.2), donde
es opcional.** `categoria_semaforo` es `not null` en la tabla — no hay forma de producir un
registro insertable sin un residual que evaluar, y `calcular_semaforo_precio()` (3.1.3) ya lanza
`SemaforoPrecioError` si falta. El caso de 3.1.2 ("propiedad nueva sin precio, solo quiero un
estimado") sigue siendo válido y soportado, pero no encaja en `valuacion_semaforo_knn` — esa
tabla es para *evaluar* precios ya publicados del catálogo, no para cotizar propiedades nuevas.
Quien necesite ese caso debe llamar `calcular_precio_estimado()` directo, no esta orquestación.
"""

from app.services.comparables_knn import buscar_comparables_knn
from app.services.estimacion_precio_knn import calcular_precio_estimado
from app.services.semaforo_precio_knn import calcular_semaforo_precio


def evaluar_precio_propiedad(
    listing_id: int,
    corregimiento: str,
    bedrooms: float,
    bathrooms: float,
    area_m2: float,
    precio_real: float,
    tipo_inmueble: str = "Apartamentos",
    k: int | None = None,
) -> dict:
    """Cadena completa 3.1.1 -> 3.1.2 -> 3.1.3 para una propiedad con precio conocido.

    Lanza `ComparablesKnnError` (3.1.1) si `corregimiento`/`tipo_inmueble` están fuera del pool
    de entrenamiento del KNN — se propaga sin envolver, ver docstring del módulo.

    Devuelve `{"registro_db": {...}, "diagnostico": {...}}`:
    - `registro_db`: mapea 1:1 a las columnas insertables de `valuacion_semaforo_knn`
      (`listing_id`, `precio_predicho`, `categoria_semaforo`, `mae_referencia`, `multiplo_mae`)
      — `fecha_carga` no se genera aquí, tiene default de la base de datos.
    - `diagnostico`: campos sin columna en la tabla (`confianza_reducida`, `n_comparables`,
      `k_esperado`, `umbral_usado`, `diferencia_absoluta`, `diferencia_porcentual`) — insumo
      para que 3.1.6 decida cómo tratar filas de cobertura reducida, no se descarta en silencio.
    """
    comparables = buscar_comparables_knn(
        corregimiento=corregimiento,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        area_m2=area_m2,
        tipo_inmueble=tipo_inmueble,
        k=k,
        listing_id=listing_id,
    )
    estimacion = calcular_precio_estimado(comparables, precio_real=precio_real)
    semaforo = calcular_semaforo_precio(estimacion)

    return {
        "registro_db": {
            "listing_id": listing_id,
            "precio_predicho": estimacion["precio_estimado"],
            "categoria_semaforo": semaforo["categoria"],
            "mae_referencia": semaforo["mae_knn_test"],
            "multiplo_mae": semaforo["multiplo_mae"],
        },
        "diagnostico": {
            "confianza_reducida": semaforo["confianza_reducida"],
            "n_comparables": semaforo["n_comparables"],
            "k_esperado": semaforo["k_esperado"],
            "umbral_usado": semaforo["umbral_usado"],
            "diferencia_absoluta": estimacion["diferencia_absoluta"],
            "diferencia_porcentual": estimacion["diferencia_porcentual"],
        },
    }
