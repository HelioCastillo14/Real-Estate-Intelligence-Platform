# Épica 2.0 — Módulo 1: Preference Matching Module
## Documentación de cierre

**Fecha de ejecución:** 2026-07-15
**Estado:** CERRADA — 31/31 SP completados (19 SP pendientes al inicio de la sesión, ejecutados en su totalidad)
**Precondición de entrada:** Feature 1.5 cerrada al 83% (5/6 tareas), con `propiedades` (1,177 filas reales), `corregimientos` (9 filas), `perfiles_lifestyle` y `conjunto_referencia_m1` ya cargados en Supabase.

---

## Resumen ejecutivo

Épica 2.0 implementa el backend de producción del Preference Matching Module (M1), portando a infraestructura real la lógica ya validada en notebooks (Feature 6.2.3) y en el contrato v0 de M3 (Feature 6.2.7). El resultado es un endpoint `POST /match/score` funcional, con búsqueda ANN sobre embeddings semánticos, filtrado estructurado, explicabilidad por dimensión, y pooling de conexiones — listo para ser consumido por la orquestación de M3 en Épica 4.

**Feature 2.3 (conjunto de referencia) no requirió trabajo en esta sesión** — ya estaba resuelta y migrada en el cierre de Feature 1.5.5 (2026-07-15, sesión previa).

---

## Feature 2.1 — Embeddings de propiedades (10 SP)

### 2.1.2 — `generar_embedding()`

**Ubicación:** `backend/app/services/embeddings.py`

Función reutilizable que llama a `gemini-embedding-001`, devuelve vectores de 3072 dimensiones. Cliente Gemini configurado con `http_options=types.HttpOptions(timeout=30_000)`, siguiendo la convención ya establecida en 6.2.6/6.2.7. Lee `GEMINI_API_KEY` desde entorno.

**Manejo de errores:** `EmbeddingError` explícito en los 4 casos posibles — API key ausente, fallo de API, respuesta sin embeddings, dimensión distinta de 3072. Sin fallos silenciosos.

**Verificación:**
- Prueba de reproducibilidad: 5 corridas sobre el mismo texto → 5 vectores idénticos (`==` exacto).
- Dimensión confirmada contra la API real: 3072, consistente con el hallazgo ya cerrado de 6.2.3.

**Riesgo documentado, sin incidencia:** el timeout de 30s deja un margen de 1.3s sobre la latencia máxima de Gemini ya observada en producción (28.7s, Feature 6.2.7). No causó fallos en esta sesión; queda como punto de vigilancia si el volumen de llamadas concurrentes aumenta.

### 2.1.3 — Batch de embeddings sobre el catálogo completo

**Decisión de scope (Anexo A del WBS):** calcular embeddings para las **1,177 filas completas** de `propiedades`, no limitarse a las 1,110 que `6.2.3` precalculó. El filtro de `zona_no_determinada`/`precio_no_evaluable` (67 filas excluidas en 6.2.3) es responsabilidad de la lógica de evaluación de M1 en tiempo de consulta — no debe heredarse a la existencia del embedding en la tabla maestra, porque M3 también consume esta columna sin esa restricción.

**Ejecución:**
- 1,110 vectores reutilizados directo de `embeddings_catalogo_6_2_3_raw.pkl`.
- 67 vectores nuevos calculados con `generar_embedding()`, mismo criterio `descripcion`/`title` de respaldo que 6.2.3.
- Resultado: 67/67 exitosas, 0 fallos.
- Consolidado en `pipeline/models/embeddings_catalogo_2_1_3_completo.pkl`.

**Carga a Supabase:** `pipeline/scripts/cargar_embeddings.py` — UPDATE por `listing_id` (no INSERT, la tabla ya existía con `embedding` en NULL), verificación de `rowcount == 1` por fila dentro de la transacción antes de comitear.

**Bug encontrado y corregido en producción:** primer intento de carga falló (`InvalidTextRepresentation`) porque `vector_a_literal()` usaba `repr()` sobre `numpy.float64`, generando literales inválidos (`np.float64(...)`) para el cast `::vector`. La transacción única hizo rollback completo (0 filas afectadas) antes de que se detectara — comportamiento correcto del patrón de carga. Corregido a `float()` explícito, reintentado y verificado sobre muestra antes de la carga real.

**Resultado final verificado:**
```sql
SELECT COUNT(*) FROM propiedades WHERE embedding IS NULL;      -- 0
SELECT COUNT(*) FROM propiedades WHERE embedding IS NOT NULL;  -- 1177
```

### 2.1.4 — Índice HNSW (cierra también Feature 1.5.6)

**Bloqueo real encontrado:** pgvector rechaza índices HNSW sobre columnas `vector` con más de 2,000 dimensiones (`SQLSTATE 54000`). `propiedades.embedding` es `vector(3072)` — límite duro del motor, no de configuración (`m`/`ef_construction` no lo resuelven).

**Solución aplicada:** índice de expresión sobre `halfvec(3072)` (media precisión, 16-bit por dimensión), cuyo límite de HNSW es 4,000 dimensiones. La columna original `propiedades.embedding` **no se modificó** — sigue siendo `vector(3072)` full precision. El cast a `halfvec` ocurre solo dentro de la definición del índice; las consultas deben castear explícitamente ambos lados del operador `<=>`.

```sql
create index if not exists idx_propiedades_embedding_hnsw
    on propiedades using hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)
    with (m = 16, ef_construction = 64);
```

**Trade-off aceptado, documentado, no medido cuantitativamente:** pérdida de precisión de 32-bit a 16-bit dentro del índice (no en el dato almacenado). Impacto en recall estimado como marginal, no evaluado con benchmark en este repo. Decisión reversible.

**Métrica:** cosine (`vector_cosine_ops`/`halfvec_cosine_ops`), confirmado contra `similitud_coseno_matriz()` en Notebook 1 (6.2.3, celda 24) y contra comentario preexistente en la migración de 1.5.1. Sin uso de L2 o producto interno en ningún punto del proyecto.

**Verificación de rendimiento:**
- El planner usa el índice **por defecto**, sin forzar `enable_seqscan = off`.
- Tiempo de ejecución en Postgres (`EXPLAIN ANALYZE`): 1.7–2.1 ms.
- Latencia medida desde cliente (5 corridas): 112.69–122.05 ms, promedio **117.06 ms**.
- Objetivo `<500ms`: **cumple**, con margen amplio.
- Brecha entre 1.7ms (motor) y 117ms (cliente) diagnosticada como latencia de red Panamá↔us-east-1, consistente en las 5 corridas — no atribuible al índice.

**Efecto colateral:** esta tarea cierra también `1.5.6` (spike de rendimiento HNSW, Feature 1.5) — mismo entregable, sin trabajo separado. Pendiente de reflejar en `REIP_WBS.md`/Excel.

---

## Feature 2.2 — Búsqueda vectorial y scorer (9 SP)

### 2.2.1 — Búsqueda ANN con filtros estructurados

**Ubicación:** `backend/app/services/busqueda_ann.py` — `buscar_propiedades_ann()`

Firma con filtros opcionales (zona, tipo_inmueble, precio_min/max, habitaciones_min, baños_min) combinados en el mismo `WHERE` que el `ORDER BY` del operador `<=>`, con cast a `halfvec(3072)`. SQL 100% parametrizado.

**Hallazgo documentado, no "arreglado" fuera de scope:** con filtros de alta selectividad (ej. `zona='Bella Vista'`, ~85% de filas descartadas), el planner descarta el índice HNSW y usa Seq Scan + Sort — comportamiento esperado de pgvector (no empuja filtros dentro del recorrido del grafo HNSW) y coherente con el volumen actual del catálogo (1,177 filas, donde un Seq Scan completo es más barato que atravesar HNSW y post-filtrar). Sin filtros selectivos, el índice sí se usa (2.41ms). Con filtros, Seq Scan responde en 52–117ms — igual por debajo del objetivo de 500ms. **No se forzó el índice artificialmente.** Recomendado como nota de limitación para el paper (Feature 6.1), no como tarea de ingeniería adicional.

**Hallazgo escalado a 2.2.5:** la función original abría una conexión nueva por llamada (`psycopg2.connect()`), agregando ~1,000ms de overhead — resuelto en 2.2.5 (ver abajo).

### 2.2.2 — Extracción de atributos de perfil persistente

**Ubicación:** `backend/app/services/perfil_usuario.py` — `estructurar_perfil_usuario()`

Distinta de la extracción de consulta conversacional puntual de M3 (6.2.7) — no reusada sin adaptar, por diseño. Input estructurado (formulario), no lenguaje natural, confirmado contra la forma real de `perfiles_lifestyle.reglas_estructurales` en Supabase.

**Validación:** zonas en `zonas_preferidas` deben existir en las 9 filas reales de `corregimientos` — falla explícita (`ValueError`) si no, sin asumir la más parecida. Mismo criterio para `precio_maximo` negativo.

**Decisión de scope, ejecutada en esta sesión:** el parámetro `distancia_metro_maxima_m` fue **retirado** de la firma tras confirmar que no existe ninguna columna de distancia real en `propiedades` ni `corregimientos` (solo un score compuesto de transporte 0-1). Se dejó un comentario de una línea marcando la ausencia como pendiente, ligado a la futura disponibilidad de datos de MiBus GTFS — decisión tomada para no exponer un parámetro que no puede aplicarse a ningún dato real.

### 2.2.4 — Explainer de compatibilidad

**Ubicación:** `backend/app/services/explicador_compatibilidad.py` — `explicar_compatibilidad()`

Evalúa 4 dimensiones mínimas (precio, habitaciones, zona, transporte) comparando el perfil estructurado contra los atributos reales de una propiedad. Output en `list[dict]`, compatible directo con `scores_compatibilidad.explicacion` (columna ya existente, Feature 1.5.4) y con consumo de frontend sin transformación adicional.

**Regla aplicada sin excepción:** un criterio ausente en el perfil se marca explícitamente como `cumplido: null` ("no evaluada"), nunca como cumplido por default.

**Dimensión "transporte" — resuelta sin dato de distancia:** ya que `distancia_metro_maxima_m` no existe, la función recibe `transporte_minimo` como parámetro aparte, evaluado contra el score compuesto de `corregimientos.desglose_dimensiones->>'transporte'` (0-1). Se documentó `UMBRAL_TRANSPORTE_SUGERIDO = 0.5` como sugerencia no calibrada contra datos reales de satisfacción de usuario — mismo estándar de honestidad ya aplicado al umbral 0.65 de 6.2.7.

**Caso especial verificado:** Costa del Este devuelve "no evaluada" con motivo distinto (`transporte_score is None`, "cobertura de datos insuficiente") — distingue correctamente entre ausencia de criterio del usuario y ausencia de dato del sistema (decisión ya cerrada de Feature 1.4).

### 2.2.5 — Endpoint `POST /match/score`

**Ubicación:** `backend/app/routers/match.py`

Ensambla `buscar_propiedades_ann()` + `explicar_compatibilidad()` por candidato, expuesto como endpoint FastAPI con modelos Pydantic (`MatchScoreRequest`/`MatchScoreResponse`).

**Decisión de diseño documentada:** el embedding de consulta se recibe ya calculado, no se genera dentro del endpoint. Desacopla la disponibilidad/latencia de Gemini de este endpoint — quien arma la consulta (M3, Épica 4) debe llamar a `generar_embedding()` por su cuenta antes. Consecuencia directa: el endpoint no depende de `GEMINI_API_KEY`.

**Connection pooling — resuelve el hallazgo pendiente de 2.2.1:**
- `psycopg2.pool.SimpleConnectionPool`, inicializado una vez en el lifespan de `main.py` (startup/shutdown), no por request.
- Elegido sobre `asyncpg` por consistencia con el resto del backend (100% psycopg2 síncrono).
- Elegido `SimpleConnectionPool` sobre `ThreadedConnectionPool` porque los endpoints sync de FastAPI ya corren en el threadpool de Starlette, que resuelve la concurrencia sin locking adicional.

**Medición cuantitativa del impacto:**

| | Antes (reconexión por llamada) | Después (con pool) |
|---|---|---|
| Promedio | 1,146.39 ms | 357.91 ms |
| Reducción | — | ~69% |

Remanente de ~320–330ms tras el pooling atribuido a latencia de red real hacia Supabase (consistente con los ~115ms de round-trip medidos en 2.1.4) más overhead de serialización Pydantic de vectores de 3072 dimensiones. No optimizado — fuera del alcance de esta tarea, y sin impacto material dado que quedará subsumido en la latencia de Gemini (hasta 28.7s) una vez orquestado por M3.

**Manejo de errores — ninguno cae a 500 genérico:**
- Zona inválida → `422` con lista de zonas válidas.
- Embedding con dimensión incorrecta → `422` con mensaje explícito antes de tocar la base de datos.

---

## Feature 2.3 — Conjunto de referencia y validación OE-01 (8 SP)

**Sin trabajo en esta sesión.** Resuelta y migrada en el cierre de Feature 1.5.5 (2026-07-15, sesión previa): `perfiles_lifestyle` (6 filas) y `conjunto_referencia_m1` (577 pares perfil-propiedad, 378 `listing_id` distintos) cargados en Supabase. Ground truth congelado explícitamente, no recalcula dinámicamente, preservando la validez del Precision@k ya aprobado (CP-2).

---

## Decisiones técnicas cerradas — no reabrir sin nueva evidencia

1. **Embedding:** `gemini-embedding-001`, 3072 dimensiones, verificado contra API real dos veces (6.2.3 y 2.1.2).
2. **Todas las 1,177 filas de `propiedades` tienen embedding** — incluidas las 67 excluidas del ground truth de M1 por zona/precio no evaluable, porque M3 las consume sin esa restricción.
3. **Índice HNSW sobre `halfvec(3072)`, no sobre `vector(3072)`** — límite duro del motor, columna original intacta.
4. **Métrica de similitud: cosine**, en todo el proyecto, sin excepción.
5. **`distancia_metro_maxima_m` no existe como criterio de perfil** hasta que haya una fuente de datos real (MiBus GTFS).
6. **El endpoint `/match/score` no calcula embeddings** — los recibe ya calculados, por diseño de desacoplamiento de Gemini.
7. **`scores_compatibilidad.explicacion`** recibe el output de `explicar_compatibilidad()` sin transformación adicional.

---

## Pendientes de gobernanza/documentación (no bloquean código)

1. **Registrar en `REIP_WBS.md`/Excel el cierre de `1.5.6`** como efecto colateral de `2.1.4`, con referencia a esta Acta.
2. **Limitación de HNSW bajo filtros selectivos con el volumen actual del catálogo** — candidata a nota de limitaciones en el paper (Feature 6.1), no a tarea de ingeniería.
3. **Umbral `UMBRAL_TRANSPORTE_SUGERIDO = 0.5`** — no calibrado contra datos reales, candidato a mención en limitaciones del paper junto al umbral 0.65 de 6.2.7.

---

## Estado de infraestructura al cierre de Épica 2.0

| Componente | Estado |
|---|---|
| `propiedades.embedding` | 1,177/1,177 filas pobladas |
| `idx_propiedades_embedding_hnsw` | Aplicado, verificado, <500ms |
| `generar_embedding()` | Producción, reproducibilidad 100% |
| `buscar_propiedades_ann()` | Producción, con pool vía router |
| `estructurar_perfil_usuario()` | Producción, validación estricta |
| `explicar_compatibilidad()` | Producción, 4 dimensiones mínimas |
| `POST /match/score` | Funcional, pool activo, errores explícitos |
| `perfiles_lifestyle` / `conjunto_referencia_m1` | Cargados desde sesión previa (1.5.5) |

**Épica 2.0 lista para ser consumida por Épica 4 (`4.3.1`, orquestación M3).**
