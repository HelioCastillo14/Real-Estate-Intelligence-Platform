# Feature 3.1 + 3.2 — Property Valuation Engine (M2)
## KNN Semáforo de Precio + Segmentación KMeans
### Documentación de cierre

**Fecha de ejecución:** 2026-07-15
**Estado:** Feature 3.1 CERRADA (14 SP) · Feature 3.2 CERRADA (8 SP)
**Precondición de entrada:** Épica 2.0 (Preference Matching) cerrada en la misma sesión. `propiedades` con embedding e índice HNSW completos. Modelos KNN/KMeans ya entrenados y validados en notebooks (Feature 6.2.4 / 6.2.5).

---

## Resumen ejecutivo

Feature 3.1 y 3.2 portan a producción los dos componentes de valuación de propiedades del Property Valuation Engine: el semáforo de precio (KNN + comparación contra umbral de MAE) y la segmentación de mercado (KMeans, 2 clusters). Ambos parten de modelos ya entrenados y cerrados en notebooks — el trabajo de esta sesión es servicio de producción, carga batch, y **dos hallazgos reales de integridad de datos** detectados y corregidos antes de tocar Supabase.

---

## Feature 3.1 — KNN Semáforo de Precio (14 SP)

### 3.1.1 — Comparables por atributos (corrección de scope ya cerrada)

**Ubicación:** `backend/app/services/comparables_knn.py` — `buscar_comparables_knn()`

Corrección heredada de Feature 1.2: el WBS original citaba `ST_Distance` (PostGIS) para comparables geoespaciales — invalidado porque inmopanama.com no expone coordenadas reales. La lógica real usa matching por atributos estructurados vía `sklearn.KNeighborsRegressor`.

**Features confirmadas contra el notebook (`02_m2_knn_semaforo_rf.ipynb`, celdas 12-15):** `corregimiento` (one-hot, prefijo `zona_`), `bedrooms`, `bathrooms`, `area_m2` — 3 numéricas escaladas con `StandardScaler`, one-hot sin escalar. k=5. Target: `price_usd`.

**Restricción estructural del modelo, documentada como limitación de scope:** el pool de entrenamiento está filtrado a `tipo_inmueble == "Apartamentos"` — el semáforo KNN **no cubre** Casas, Edificios, Locales ni Terrenos. Candidata explícita a mención en limitaciones del paper (Feature 6.1).

**Verificación de pickle:** confirmado byte a byte contra el notebook (columnas, k, n_features) — único desalineamiento real es el ya conocido umbral de semáforo (ver 3.1.3). Hallazgo colateral: `scikit-learn`/`numpy` no estaban en `backend/requirements.txt` — agregado con las mismas versiones del entorno de notebooks para evitar incompatibilidad de unpickling.

**Deuda técnica documentada:** la función lee `knn._y` (atributo interno no público de sklearn) para acceder a los precios reales de los vecinos — necesario porque `KNeighborsRegressor` no expone esto por API pública. Riesgo mitigado al fijar la versión exacta de sklearn.

### 3.1.2 — Estimación de precio

**Ubicación:** `backend/app/services/estimacion_precio_knn.py` — `calcular_precio_estimado()`

Confirmado contra notebook (celda 15): `weights="uniform"` (default de sklearn) → promedio simple de los k comparables, no ponderado por distancia.

**Manejo explícito de cobertura insuficiente:** si hay menos de k=5 comparables, la función promedia lo disponible y marca `cobertura_insuficiente=True` — no falla ni finge que hay 5. Lista vacía sí lanza error (no hay forma de promediar cero).

**Convención de signo heredada del notebook (celda 33):** `diferencia_absoluta = precio_real - precio_estimado`, positivo = pagó de más — anclado explícitamente para que 3.1.3 no invierta la semántica.

### 3.1.3 — Corrección obligatoria de umbral + asignación de semáforo

**Ubicación:** `backend/app/services/semaforo_precio_knn.py` — `calcular_semaforo()`

**Corrección crítica ejecutada:** el pickle de KNN (`knn_semaforo_precio_6_2_4.pkl`) tenía `umbral_semaforo=0.10` (±10%) serializado en una etapa intermedia del notebook — desactualizado frente al criterio real de producción, `±1.5×MAE`, fijado en una etapa posterior (celda 33) y nunca vuelto a persistir en el pickle. Si se hubiera usado el 0.10 sin corregir, la distribución de semáforo no habría coincidido con la ya publicada y aprobada en el paper.

**Umbral correcto, re-derivado (no copiado del string redondeado del paper):** se reprodujo el pipeline completo del notebook con `RANDOM_STATE=42` y se obtuvo `MAE_KNN_TEST=187543.4765550239` exacto → umbral `±$281,315.21` (1.5×MAE). El módulo no lee `umbral_semaforo` del pickle en ningún punto.

**Lógica de 3 categorías, confirmada contra celda 33:**
```
residual = precio_real - precio_estimado
residual > +1.5×MAE  → rojo (sobrevalorado)
residual < -1.5×MAE  → verde (buen precio)
en banda              → amarillo
```

**Decisión de diseño — caso `cobertura_insuficiente`:** se calcula el semáforo igual, marcado con `confianza_reducida=True` (opción "b" de 3 evaluadas). Justificado con el precedente correcto del proyecto: Pedregal (dato real pero débil, se calcula, decisión de presentación) — no Costa del Este (ausencia estructural de dato). La decisión de ocultar/advertir queda en la capa de presentación, no en la lógica de dominio.

### 3.1.4 — MAE por zona (5-fold CV) — hallazgo relevante para el paper

**Ubicación:** `pipeline/scripts/analisis_mae_por_zona_3_1_4.py` (script de diagnóstico, no servicio de producción — nada lo consume en tiempo real).

**Confirmado que es trabajo genuinamente nuevo** — el notebook solo reporta MAE global agregado, nunca desglosado por zona.

**Hallazgo — el error del modelo NO es homogéneo entre corregimientos:**

| Corregimiento | MAE | n | vs. MAE global CV ($165,707) |
|---|---|---|---|
| San Francisco | $266,275 | 365 | +60.7% |
| Costa del Este | $109,063 | 143 | -34.2% |
| Bella Vista | $84,931 | 132 | -48.7% |
| Marbella | $83,758 | 40 | -49.5% |
| Obarrio | $82,304 | 44 | -50.3% |
| El Cangrejo | $80,947 | 59 | -51.2% |
| Betania | $45,734 | 50 | -72.4% |

San Francisco (44% del dataset de train) concentra el error del modelo global, probablemente por su cola de precios de lujo. El umbral global de ±$281,315 resulta demasiado ancho para 6 de 7 zonas (sobre-etiqueta "amarillo" más de lo justificado) y potencialmente demasiado angosto para San Francisco (falsos verde/rojo).

**Decisión tomada:** queda documentado como limitación conocida para el paper (Feature 6.1) — no abre tarea de rediseño de umbral por zona en este sprint.

### 3.1.5 — Orquestación end-to-end

**Ubicación:** `backend/app/services/valuacion_knn.py` — `evaluar_precio_propiedad()`

Encadena `buscar_comparables_knn()` → `calcular_precio_estimado()` → `calcular_semaforo()`. Devuelve `{"registro_db": {...}, "diagnostico": {...}}` — separación necesaria porque el DDL aprobado de `valuacion_semaforo_knn` originalmente no reservaba columnas para `confianza_reducida`/`n_comparables` (corregido, ver migración `20260715040006` abajo).

Errores de zona/tipo rechazado (Pedregal, tipo="Casas") se propagan tal cual desde 3.1.1, sin envolver ni silenciar.

### 3.1.6 — Carga a producción + hallazgo de fuga de datos (data leakage)

**Migración previa aplicada:** `20260715040006` — agrega `confianza_reducida boolean not null default false` y `n_comparables smallint` a `valuacion_semaforo_knn`, decisión tomada explícitamente para no descartar el diagnóstico de confianza calculado en 3.1.5.

**Hallazgo crítico detectado por la regla de oro del proyecto (verificación contra el paper antes de insertar):**

Primer dry-run sobre las 1,042 propiedades elegibles arrojó 87.5% amarillo vs. 82.3% publicado en el paper — desviación de +5.2pp, por encima del umbral de tolerancia. **No se insertó.**

**Causa raíz aislada experimentalmente, no hipotética:** de las 1,042 propiedades elegibles, 833 fueron parte del **training set** del KNN (Notebook 2). Al evaluarlas, cada una se encontraba a sí misma como uno de sus propios 5 comparables (distancia 0, mismo precio) — fuga de datos clásica (train-test contamination). Confirmado separando la distribución por subconjunto:

| | verde | amarillo | rojo |
|---|---|---|---|
| Solo test del KNN (n=209) | 9.1% (19) | 82.3% (172) | 8.6% (18) — **idéntico al paper** |
| Solo train del KNN (n=833) | 5.6% (47) | 88.8% (740) | 5.5% (46) — **sesgo concentrado aquí** |

**Corrección aplicada:** `buscar_comparables_knn()` (3.1.1) extendida para aceptar `listing_id` opcional; si la propiedad consultada aparece entre sus propios vecinos (mapeo posición-`listing_id` reconstruido y verificado contra `price_usd` real antes de usarse), se excluye y se re-consulta con k+1 para mantener 5 comparables reales. Verificado que la exclusión es por posición exacta, no por precio (probado con un caso real de empate de precio entre dos propiedades distintas).

**No-regresión verificada:** las 209 filas de test (nunca en el training set) devuelven resultado idéntico con y sin la corrección. Verificado también que la corrección no afecta ningún caller de Épica 2 (`comparables_knn.py` no comparte código con `busqueda_ann.py`, usado por `2.2.1`/`match.py`).

**Distribución final tras la corrección:**

| | Paper (n=209) | Antes (n=1042) | Después (n=1042) |
|---|---|---|---|
| Verde | 9.1% (19) | 6.3% (66) | 7.7% (80) |
| Amarillo | 82.3% (172) | 87.5% (912) | 85.2% (888) |
| Rojo | 8.6% (18) | 6.1% (64) | 7.1% (74) |

Delta máximo tras corrección: +2.9pp (amarillo) — dentro de tolerancia. La distancia remanente frente al paper es esperada y honesta: el batch combina train+test (833+209), y remover el auto-match no vuelve esas 833 filas verdaderamente out-of-sample, solo elimina el sesgo más grosero.

**Documentado en Acta separada:** `Context-MD/Hallazgo_Fuga_Datos_Batch_3_1_6_Cierre.md` — causa raíz, mecanismo de corrección, verificación de no-regresión, las 3 distribuciones. Material directamente citable en el paper (metodología/limitaciones) y en la defensa de tesis.

**Carga real ejecutada:** 1,042/1,042 filas, 0 fallos, 0 duplicados, `confianza_reducida=True` en 0 filas (el modelo siempre tuvo ≥5 vecinos disponibles). Distribución post-carga idéntica al dry-run corregido.

---

## Feature 3.2 — Segmentación KMeans (8 SP)

### 3.2.1 – 3.2.3 — Ya cerradas en sesión previa (Feature 6.2.5, notebook)

No requirieron trabajo en esta sesión. Resumen: features preparadas sin nulos (`price_usd`, `area_m2`, `precio_por_m2`, `bedrooms`, `bathrooms`, escaladas con `StandardScaler`); k óptimo=2 (método del codo + Silhouette=0.388), **desviación del WBS original (k=5) ya formalmente documentada** en `Feature_6_2_5_M2_KMeans_Cierre.md` y reflejada en `Gobernanza_WBS_vs_Feature_6_2.md`.

### 3.2.4 — Etiquetado cualitativo, con excepción documentada

**Acta separada:** `Feature_3_2_4_Etiquetado_Clusters_KMeans_Acta_Excepcion.md`

La condición de Done original exige revisión del etiquetado por ≥2 miembros del equipo — **sin tiempo disponible en esta sesión.** Se aplicó la misma excepción ya usada y aceptada en Feature 1.4 (Zone Health): revisión Besto + Claude únicamente, documentada explícitamente como desviación, no oculta ni presentada como cumplimiento completo del estándar.

**Etiquetado confirmado:**

| `cluster_id` | Etiqueta | n | Mediana precio | Mediana área |
|---|---|---|---|---|
| 0 | Compacto / económico | 662 | $270,000 | 92 m² |
| 1 | Grande / premium | 380 | $736,000 | 300 m² |

Costa del Este y San Francisco sesgan hacia premium — consistente con el hallazgo de MAE alto de San Francisco en 3.1.4.

**Decisión de esquema respetada:** la etiqueta textual no se persiste en `valuacion_segmento_kmeans.cluster_id` (solo el entero crudo) — si se formaliza, debe vivir en tabla de metadata separada, para no congelar una interpretación que un recálculo futuro podría invalidar.

### 3.2.5 — Carga a producción

**Features confirmadas contra notebook (celda 8), distintas de las del KNN:** `price_usd`, `area_m2`, `precio_por_m2` (derivada, calculada en el script), `bedrooms`, `bathrooms` — las 5 escaladas. `corregimiento` no es feature del KMeans (el objetivo es segmentar por tipo de propiedad, no redescubrir geografía).

**Evaluación explícita de riesgo de fuga de datos — no aplica, razonado, no asumido por analogía con 3.1.6:** `KMeans.predict()` mide distancia contra 2 centroides fijos (promedios agregados), no contra puntos de dato individuales — no existe mecanismo de "auto-encuentro". Adicionalmente, `6.2.5` nunca dividió train/test (`fit_predict()` corrió sobre las 1,042 filas completas como asignación de producción), así que no hay partición "pura" que proteger.

**Carga real:** 1,042/1,042 filas, 0 fallos, 0 duplicados. Distribución: cluster 0 = 662 (63.5%), cluster 1 = 380 (36.5%) — reproducción exacta de `fit_predict()` original (delta 0.0pp), esperada porque el universo elegible es la misma población que entrenó el modelo.

---

## Decisiones técnicas cerradas — no reabrir sin nueva evidencia

1. **Semáforo KNN cubre solo `tipo_inmueble="Apartamentos"`** — limitación estructural del modelo, no de la implementación de esta sesión.
2. **Umbral de semáforo: ±1.5×MAE ($281,315.21), nunca el 0.10 del pickle.**
3. **MAE del modelo es heterogéneo por zona** — evidencia cuantitativa disponible (tabla en 3.1.4), sin acción de rediseño en este sprint.
4. **Fuga de datos en KNN corregida mediante exclusión de auto-comparable por `listing_id`** — necesaria siempre que se evalúe una propiedad que pudo formar parte del training set.
5. **KMeans no tiene el mismo riesgo de fuga** — mecanismo distinto (centroides vs. vecinos), evaluado explícitamente.
6. **KMeans: k=2, no k=5** — decisión ya cerrada desde 6.2.5, con desviación formal del WBS documentada.
7. **Etiquetas textuales de cluster nunca se persisten junto al entero** — separación deliberada por reversibilidad.

---

## Pendientes de gobernanza / documentación (no bloquean código)

1. **Limitación de scope del semáforo (solo Apartamentos)** — candidata a Sección de limitaciones, Feature 6.1.
2. **MAE heterogéneo por zona** — candidata a la misma sección, con la tabla completa de 3.1.4.
3. **Hallazgo de fuga de datos** — ya documentado en Acta propia, candidato a citarse directo en metodología del paper como evidencia de rigor (detección + corrección + verificación).
4. **Etiquetado de clusters con excepción de revisión de 1 sola persona** — igual que Zone Health, disponible para reapertura formal por el equipo completo si hay tiempo antes de la defensa.

---

## Estado de infraestructura al cierre de Feature 3.1 + 3.2

| Componente | Estado |
|---|---|
| `buscar_comparables_knn()` | Producción, con exclusión de auto-comparable |
| `calcular_precio_estimado()` | Producción, cobertura insuficiente manejada |
| `calcular_semaforo()` | Producción, umbral correcto (±$281,315.21) |
| `evaluar_precio_propiedad()` | Orquestador end-to-end, producción |
| `valuacion_semaforo_knn` | 1,042/1,042 filas cargadas, distribución verificada |
| `valuacion_segmento_kmeans` | 1,042/1,042 filas cargadas, distribución exacta a notebook |
| `analisis_mae_por_zona_3_1_4.py` | Artifact de diagnóstico, evidencia para el paper |

**Feature 3.1 y 3.2 listas. Pendiente en Épica 3: `3.5.1`/`3.5.2` para cierre completo.**
