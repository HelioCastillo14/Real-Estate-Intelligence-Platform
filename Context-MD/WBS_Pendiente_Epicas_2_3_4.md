# WBS Pendiente — Épicas 2.0, 3.0 y 4.0 (ajustado al avance real de Feature 6.2 + cierre de Feature 1.5)

**Fecha:** 2026-07-15 (actualizado — versión anterior del 2026-07-14 quedó desactualizada por el cierre de Feature 1.5 en sesión del mismo día)
**Fuente:** `Context-MD/REIP_WBS.xlsx` (original, intacto) + `Context-MD/Gobernanza_WBS_vs_Feature_6_2.md` (discrepancias resueltas) + cierres de notebooks 6.2.1–6.2.7 + `Feature_1_5b_Embedding_Dimension_Cierre.md` + **Actas de cierre de Feature 1.5.1/1.5.2/1.5.3/1.5.4/1.5.5 (2026-07-15)**.

**Cómo leer este documento:** cada tarea conserva su ID y SP originales del WBS. La columna **"Condición de Done — ajustada"** reemplaza la original cuando el trabajo de Feature 6.2 o Feature 1.5 ya resolvió parte de la incertidumbre. Las tareas ya completadas (2.2.3, 3.2.2, 3.4.1, 1.5b, y el batch de 3.4.3) no aparecen aquí — ver `Gobernanza_WBS_vs_Feature_6_2.md` para su cierre.

**Total pendiente: ~35 SP** de los 94 SP originales combinados de las 3 épicas. (Sin cambio en SP totales — el cierre de Feature 1.5 desbloquea tareas, no las completa.)

---

## ⚠️ Cambio de estado más importante desde la versión anterior

**Feature 1.5 (esquema de base de datos) quedó cerrada al 83% (5/6 tareas) el 2026-07-15**, con datos reales cargados en Supabase — no solo estructura. Esto cambia directamente 6 dependencias listadas en este documento:

| Tabla | Estado anterior | Estado actual |
|---|---|---|
| `propiedades` | No creada (bloqueaba 2.1.3, 3.1.1, 4.3.2) | ✓ Creada, **1,177 filas reales cargadas**, `embedding`/`geom` en NULL (pendiente Épica 2) |
| `corregimientos` | No creada | ✓ Creada, 9 filas (Zone Health cargado) |
| `amenidades` | No creada | ✓ Creada, 238 filas |
| `perfiles_lifestyle` / `conjunto_referencia_m1` | No creadas (bloqueaba Feature 2.3) | ✓ Creadas, 6 perfiles + 577 pares cargados |
| `valuacion_quality_scorer` / `valuacion_semaforo_knn` / `valuacion_segmento_kmeans` / `scores_compatibilidad` / `sesiones_consulta` | No creadas (bloqueaba 3.1.6, 3.2.5) | ✓ Creadas. Solo `valuacion_quality_scorer` tiene datos (1,168 filas) — las otras 4 están vacías, **listas para recibir INSERT en cuanto sus respectivos batches corran** |

**Sigue bloqueada:** `1.5.6` (spike de rendimiento HNSW) — depende de `2.1.3`, que es trabajo de esta misma Épica 2. Es la única tarea de Feature 1.5 que no se puede cerrar sin avanzar en las épicas de este documento.

---

## Épica 2.0 — Módulo 1: Preference Matching (19 SP pendientes de 31)

### Feature 2.1 — Embeddings de propiedades

| ID | Tarea | SP | Condición de Done — ajustada | Depende de |
|---|---|---|---|---|
| 2.1.2 | Implementar función `generar_embedding(texto: str) → vector` reutilizable por M1 y M3 | 2 | Debe llamar a `gemini-embedding-001` (modelo y dimensión ya fijados y verificados contra la API real en 6.2.3) y devolver vectores de 3072-dim. Referencia de implementación disponible en `notebooks/01_m1_preference_matching.ipynb` (celda de verificación de modelo) — adaptar a módulo de producción compartido, mismo input debe producir mismo vector en 100% de pruebas de reproducibilidad. | 2.1.1 (cerrado) |
| 2.1.3 | Ejecutar batch de embeddings sobre todo el catálogo y almacenar en `propiedades.embedding` | 5 | **Decisión de scope tomada en sesión 2026-07-15, ver Anexo A — calcular embeddings para las 1,177 filas reales de `propiedades`, NO solo las 1,110 que `6.2.3` precalculó.** El pickle de 6.2.3 (`embeddings_catalogo_6_2_3_raw.pkl`) excluye 67 filas por un filtro de validez específico de M1 (53 `zona_no_determinada` + 14 `precio_no_evaluable`) — ese filtro es responsabilidad del scorer de M1 en tiempo de consulta, no debe heredarse a la existencia del embedding en la tabla maestra, porque M3 también consume esta columna sin esa restricción. Las 1,110 filas ya calculadas pueden reutilizarse directo (mismo modelo, sin necesidad de recalcular); solo hace falta calcular las 67 restantes y cargar el total. **Precondición de infraestructura ya resuelta**: `propiedades` existe con 1,177 filas reales (Feature 1.5.1, cerrada 2026-07-15) — ya no es bloqueante. Propiedades sin descripción (`descripcion_fuente="ninguna"`, 9 filas) usan `title` como texto de respaldo, consistente con 6.2.3 — no quedan con embedding NULL por defecto, ver Anexo A. | 2.1.2, ~~1.5.1 (no creada)~~ **1.5.1 — CERRADA 2026-07-15**, 1.2.7 (cerrado) |
| 2.1.4 | Crear índice HNSW sobre `propiedades.embedding` y verificar rendimiento de búsqueda ANN | 3 | Sin cambios — infraestructura pura de Supabase. Índice HNSW construido; búsqueda ANN de prueba responde en < 500ms. **Esta tarea es funcionalmente la misma que Feature 1.5.6** (spike de rendimiento, WBS de Feature 1.5) — al completar 2.1.4 se cierra también 1.5.6, no son dos entregables separados. | 2.1.3 |

### Feature 2.2 — Búsqueda vectorial y scorer

| ID | Tarea | SP | Condición de Done — ajustada | Depende de |
|---|---|---|---|---|
| 2.2.1 | Implementar función de búsqueda ANN (cosine similarity vía HNSW, top-k configurable, con filtros SQL opcionales) | 3 | La lógica de filtrado estructurado ya está validada end-to-end en el contrato v0 de 6.2.7 (`m1_buscar_matches()`) — corre sobre pandas, no SQL real. Falta traducir a SQL con `<=>` (cosine) + filtros combinados en la misma query. | 2.1.4 |
| 2.2.2 | Implementar extracción de atributos estructurados de perfil (precio máx, habitaciones, zonas preferidas, distancia a metro máx) | 2 | Sin cambios — extrae atributos de un **perfil de usuario persistente**, distinto de la extracción de **consulta conversacional puntual** (ya resuelta en 6.2.7 para M3). No reusar sin adaptar. | — |
| 2.2.4 | Implementar explainer: qué criterios cumplió/no cumplió cada propiedad | 2 | Sin cambios — M1 (6.2.3) no genera explicaciones en lenguaje natural, solo score numérico. Confirmado como gap real (mockup de frontend, bloque "¿Por qué X% de compatibilidad?"). **`scores_compatibilidad.explicacion` ya existe como columna nullable en Supabase (Feature 1.5.4, cerrada), lista para recibir este output en cuanto la lógica exista — no requiere migración adicional.** Output debe listar criterios con estado cumplido/no cumplido para al menos 4 dimensiones (precio, habitaciones, zona, transporte). | 2.2.3 (cerrado) |
| 2.2.5 | Endpoint FastAPI: `POST /match/score` (consumido internamente por M3) | 2 | Contrato de interfaz ya prototipado como `m1_buscar_matches()` en 6.2.7, "v0 — sujeto a revisión en Épica 4" — usar como referencia de diseño, no implementación final. | 2.2.3 (cerrado), 2.2.4, 1.1.3 (cerrado) |

### Feature 2.3 — Conjunto de referencia y validación OE-01

**Esta feature completa (8 SP) ya está resuelta en 6.2.3 Y migrada a Supabase.** ~~No queda SP pendiente de diseño — solo migrar el resultado a la tabla `conjunto_referencia_m1` cuando 1.5.5 esté implementada.~~ **`1.5.5` se cerró el 2026-07-15**: `perfiles_lifestyle` (6 filas) y `conjunto_referencia_m1` (577 pares perfil-propiedad, 378 `listing_id` distintos) están cargadas en Supabase, ver `Feature_1_5_5_ConjuntoReferenciaM1_Cierre.md`. El ground truth se congeló explícitamente (no recalcula dinámicamente) para preservar la validez del Precision@k ya aprobado (CP-2) — cualquier consumo futuro de esta tabla debe leerla tal cual está, no asumir que refleja el catálogo vigente si este cambia sustancialmente. **Esta feature está efectivamente cerrada, 0 SP pendiente.**

---

## Épica 3.0 — Módulo 2: Property Valuation Engine (~15 SP pendientes de 41)

### Feature 3.1 — Semáforo de precio (KNN)

| ID | Tarea | SP | Condición de Done — ajustada | Depende de |
|---|---|---|---|---|
| 3.1.1 | Implementar consulta de comparables por corregimiento y tipo de inmueble | 3 | Comparable = corregimiento + tipo_inmueble, vía `KNeighborsRegressor`, decisión ya validada en 6.2.4. Falta implementar como query de producción sobre Supabase. **`propiedades` ya existe con datos reales — precondición resuelta.** | ~~1.5.1~~ **1.5.1 — CERRADA**, 1.2.7 (cerrado) |
| 3.1.2 | Implementar KNN para predicción de precio/m² | 3 | Modelo ya entrenado: `knn_semaforo_precio_6_2_4.pkl` + `escalador_knn_6_2_4.pkl`. Features: `bedrooms`, `bathrooms`, `area_m2`, `corregimiento` (one-hot, 7 zonas — Pedregal y Parque Lefevre excluidos por volumen). Falta cargar el artifact al backend. | 3.1.1 |
| 3.1.3 | Lógica de etiqueta semáforo con umbral configurable | 2 | Recalibrado en 6.2.4 a ±1.5×MAE. **⚠️ Hallazgo de sesión 2026-07-15, ver Anexo B: el `.pkl` (`knn_semaforo_precio_6_2_4.pkl`) tiene `umbral_semaforo=0.1` (±10%) desactualizado — la recalibración a ±1.5×MAE nunca se volvió a serializar en el pickle, solo existe como código en la sección 9 del notebook.** El paper ya reporta el valor correcto (±1.5×MAE, ±$281,315) porque se escribió leyendo el notebook, no el pickle — **pero cualquier implementación de esta tarea que cargue directamente el `.pkl` sin corregirlo va a aplicar el umbral viejo por error.** Corregir el pickle (persistir `mae_knn_test` y `multiplo_mae=1.5` explícitamente) es prerequisito real de esta tarea, no opcional. | 3.1.2 |
| 3.1.4 | Validar con 5-fold CV; calcular MAE promedio ± desviación estándar **por zona** | 3 | MAE agregado ya calculado: KNN $165,707 (CV) / $187,543 (test). Falta el desglose por zona — gap real, no solo portar a producción. | 3.1.2 |
| 3.1.5 | Endpoint FastAPI: `GET /valuation/semaforo/{propiedad_id}` | 1 | Lógica completa ya prototipada como `m2_enriquecer_semaforo()` en 6.2.7, incluyendo caso de cobertura insuficiente. | 3.1.3, 1.1.3 (cerrado) |
| 3.1.6 | Almacenar resultados del semáforo en `scores_valuacion` (pre-computado) | 2 | Mismo patrón que Quality Scorer (`escalar_quality_scorer_6_2_6.py`) — batch único. **La tabla destino ya existe**: `valuacion_semaforo_knn` (Feature 1.5.4, cerrada), con columnas `precio_predicho`, `categoria_semaforo`, `mae_referencia`, `multiplo_mae` — diseñada para preservar el umbral usado por fila, no depender de un valor de configuración externo. **No ejecutar este batch hasta resolver 3.1.3 (pickle desactualizado) — cargar con el umbral viejo contaminaría la tabla con datos que no coinciden con el paper.** | 3.1.3, ~~1.5.4~~ **tabla destino lista (Feature 1.5.4, cerrada)** |

### Feature 3.2 — Segmento de mercado (KMeans)

| ID | Tarea | SP | Condición de Done — ajustada | Depende de |
|---|---|---|---|---|
| 3.2.4 | Revisar y etiquetar cualitativamente los clusters con nombres descriptivos | 2 | 2 clusters (k=2, Silhouette=0.388). Segmentos nombrados informalmente: "compacto/económico" vs. "grande/premium". **Pendiente de confirmar**: revisión por ≥2 integrantes del equipo, o excepción formal documentada (mismo estándar que Zone Health). **Nota de sesión 2026-07-15: esta etiqueta NO debe persistirse como string en `valuacion_segmento_kmeans.cluster_id`** — esa columna guarda el entero crudo (0/1) por diseño, ver `Ajuste_WBS_1_5_4_Esquema_Scores.md` §3; la interpretación textual, si se formaliza, debe vivir en una tabla de metadata separada para no congelar una etiqueta que podría invalidarse si KMeans se recalcula. | 3.2.3 (cerrado) |
| 3.2.5 | Almacenar asignación de cluster en `scores_valuacion` | 1 | Mismo patrón de batch único que 3.1.6. Modelo ya entrenado (`kmeans_segmentacion_6_2_5.pkl`, `escalador_kmeans_6_2_5.pkl`). **Tabla destino ya existe**: `valuacion_segmento_kmeans` (Feature 1.5.4, cerrada) — sin bloqueante de esquema, solo falta correr el batch y cargar. | 3.2.4, ~~1.5.4~~ **tabla destino lista** |

### Feature 3.5 — Endpoint de transparencia del modelo

| ID | Tarea | SP | Condición de Done — ajustada | Depende de |
|---|---|---|---|---|
| 3.5.1 | Generar dataset de pares predicho/real sobre el conjunto de test del semáforo KNN | 2 | Pares ya existen dentro de la evaluación de 6.2.4 — falta exportar a CSV/tabla limpia, confirmando que el MAE recalculado coincide con el ya reportado (33.4%/26.6%). | 3.1.4 |
| 3.5.2 | Endpoint FastAPI: `GET /valuation/transparencia` | 1 | Sin cambios. | 3.5.1, 1.1.3 (cerrado) |

*(Feature 3.3 — RF vs. KNN — completa, `Feature_6_2_4_M2_KNN_RF_Cierre.md`. Feature 3.4 — Quality Scorer — completa, batch de producción cargado en `valuacion_quality_scorer` (1,168 filas, Feature 1.5.4, cerrada 2026-07-15) — verificado contra Cuadro IX/X del paper sin discrepancia.)*

---

## Épica 4.0 — Módulo 3: NLP Orchestration Layer (10 SP pendientes de 22)

*(Features 4.1 y 4.2 completas — ver `Feature_6_2_7_M3_Orchestration_Cierre.md`. Solo Feature 4.3, implementación de backend, queda pendiente.)*

### Feature 4.3 — Endpoint de orquestación

| ID | Tarea | SP | Condición de Done — ajustada | Depende de |
|---|---|---|---|---|
| 4.3.1 | Endpoint `POST /search/nlp` que orquesta el pipeline completo: NLP → M1 → M2 → ensamblado | 5 | Diseño completo ya validado (`orquestar_m3()`, 6.2.7), verificado en las 4 combinaciones posibles. Falta envolver en endpoint FastAPI real con queries reales a Supabase. **`sesiones_consulta` ya existe como tabla destino** (Feature 1.5.4, cerrada) — schema `jsonb` para el contrato de extracción completo, columna `confianza` separada para análisis de calibración. | 4.1.2 (cerrado), 2.2.5, 3.1.5, 4.2.1 (cerrado) |
| 4.3.2 | Endpoint `POST /search/filtros` (búsqueda estructurada sin NLP) | 3 | Sin cambios — sin relación con 6.2.7. | 1.1.3 (cerrado), ~~1.5.1~~ **1.5.1 — CERRADA** |
| 4.3.3 | Medir y documentar tiempo de respuesta end-to-end del endpoint NLP (objetivo ≤5s, SRS-024) | 2 | Riesgo detectado — latencias individuales de Gemini hasta 28.7s registradas en 6.2.7. Corrida de 27 consultas nuevas midiendo distribución real en curso al 2026-07-14 — revisar su resultado antes de comprometerse al objetivo ≤5s. | 4.3.1 |

---

## Resumen de bloqueos activos que afectan a estas 3 épicas (actualizado 2026-07-15)

1. ~~`1.5.1` (tabla `propiedades` completa) sigue "no iniciada" — bloquea 2.1.3~~ **RESUELTO — Feature 1.5.1 cerrada 2026-07-15, 1,177 filas reales cargadas.** El bloqueante real remanente de `2.1.3` es únicamente `2.1.2` (función `generar_embedding()` de producción, no construida todavía).
2. **`3.1.3` / `3.1.6` — NUEVO bloqueante identificado en sesión 2026-07-15**: el `.pkl` de KNN tiene el umbral del semáforo desactualizado (±10% en vez de ±1.5×MAE). Debe corregirse (re-serializar con `mae_knn_test` y `multiplo_mae` explícitos) antes de ejecutar el batch de `3.1.6` — ver Anexo B. Sin efecto sobre el paper, que ya usa el valor correcto.
3. **`3.2.4`** — pendiente de confirmar si el etiquetado de los 2 segmentos cumple el requisito de revisión por ≥2 personas del equipo.
4. **`4.3.3`** — resultado de la medición de latencia en curso; puede requerir ajustar el objetivo SRS-024 antes de continuar con 4.3.1/4.3.2.
5. **`1.5.6`** (spike HNSW, Feature 1.5) — bloqueada por `2.1.3`/`2.1.4` de este documento. Se cierra automáticamente al completar `2.1.4` — no requiere trabajo separado.

---

## Anexo A — Decisión de scope: embeddings para 1,177 filas, no 1,110

**Contexto:** `6.2.3` calculó embeddings solo para 1,110 de las 1,177 filas del catálogo, aplicando un filtro de validez específico para el ground truth de M1 (excluye `corregimiento == "zona_no_determinada"`, 53 filas, y `precio_no_evaluable == True`, 14 filas — total 67).

**Decisión tomada en sesión 2026-07-15:** `2.1.3` debe calcular embeddings para las **1,177 filas completas**, no limitarse al subconjunto de 1,110.

**Justificación:**
- El filtro de `6.2.3` es responsabilidad de la lógica de evaluación de M1 (una fila con zona no resuelta no puede evaluarse contra un perfil que filtra por zona) — no es una propiedad inherente de esas 67 filas que las haga indignas de tener representación semántica.
- `propiedades.embedding` es una columna de la tabla maestra del catálogo, consumida también por M3 (orquestación), que no tiene ninguna razón para excluir esas 67 propiedades de la búsqueda semántica.
- Ya existe precedente de inclusión: las 9 filas con `descripcion_fuente="ninguna"` sí se incluyeron en los 1,110, usando `title` como texto de respaldo — estableciendo que "dato imperfecto" no es motivo de exclusión del embedding.
- Costo de calcular las 67 adicionales: bajo (llamadas extra a la API). Costo de no calcularlas: esas propiedades quedan permanentemente sin búsqueda semántica en M3 sin justificación sólida.

**Lo que NO cambia:** el filtro de `zona_no_determinada`/`precio_no_evaluable` se sigue aplicando dentro de la lógica de M1 en tiempo de consulta/evaluación — no se elimina, solo no se hornea en la existencia del embedding.

**Implementación práctica:** las 1,110 filas ya calculadas en `embeddings_catalogo_6_2_3_raw.pkl` pueden reutilizarse directo (mismo modelo `gemini-embedding-001`, mismo texto de entrada esperado) — solo hace falta calcular las 67 restantes con `generar_embedding()` (2.1.2) y cargar el total de 1,177 vectores.

## Anexo B — Hallazgo: pickle de KNN con umbral de semáforo desactualizado

**Contexto:** `knn_semaforo_precio_6_2_4.pkl` fue serializado con `umbral_semaforo: 0.1` (±10%, el criterio original) en la sección 8 del notebook `02_m2_knn_semaforo_rf.ipynb`. La recalibración a `±1.5×MAE` (criterio de producción real) ocurre después, en la sección 9, y el pickle nunca se volvió a guardar con ese valor actualizado.

**Verificado sin impacto en el paper:** la Sección IV-A3 del paper reporta el umbral correcto (±1.5×MAE, ±$281,315 = 1.5 × $187,543 MAE de test) — coincide exactamente con la lógica real de producción del notebook, confirmando que el paper se escribió contra el código correcto, no contra el metadata desactualizado del pickle.

**Riesgo real para Épica 3:** cualquier implementación de `3.1.3`/`3.1.6` que cargue `umbral_semaforo` directamente del `.pkl` sin cruzarlo contra el notebook va a aplicar el criterio viejo (±10%) por error, produciendo una distribución de semáforo que **no coincidiría** con la ya reportada y aprobada (82.3% amarillo / 9.1% verde / 8.6% rojo).

**Acción requerida antes de `3.1.6`:** re-serializar el `.pkl` persistiendo explícitamente `mae_knn_test` ($187,543) y `multiplo_mae` (1.5), no solo el `umbral_semaforo` obsoleto — ejecutar la sección 9 del notebook y actualizar el artifact guardado.
