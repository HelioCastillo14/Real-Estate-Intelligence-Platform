# Épica 3.0 — Property Valuation Engine (M2)
## Acta de cierre completa

**Fecha de cierre:** 2026-07-15
**Estado:** CERRADA — 5/5 Features completas (3.1, 3.2, 3.3, 3.4, 3.5)
**Alcance del módulo:** evaluación multidimensional de propiedades — no forecasting de inversión. Comprende semáforo de precio (KNN), comparación metodológica (Random Forest), segmentación de mercado (KMeans), calidad de listing (LLM Quality Scorer), y transparencia del modelo.

---

## Resumen ejecutivo

Épica 3.0 completa el segundo de los tres módulos interdependientes de REIP. A diferencia de Épica 2 (construida íntegramente en esta sesión), Épica 3 combina trabajo de sesiones previas ya cerrado (Features 3.3 y 3.4, resueltas en notebooks 6.2.4/6.2.6) con trabajo de producción ejecutado hoy (Features 3.1, 3.2 y 3.5 — portar modelos ya entrenados y validados a servicios de backend reales, con carga a Supabase).

El hallazgo más significativo de la épica es una **fuga de datos real detectada, aislada experimentalmente y corregida antes de tocar producción** (Feature 3.1.6) — evidencia directa de que el protocolo de verificación contra el paper (regla de oro del proyecto) funcionó exactamente como fue diseñado: detener la inserción ante una desviación no explicada, en vez de forzarla o ignorarla.

---

## Feature 3.1 — Semáforo de Precio KNN (14 SP) — CERRADA hoy

**Documentación detallada:** `Feature_3_1_3_2_Property_Valuation_Documentacion.md`

| Tarea | Resultado |
|---|---|
| 3.1.1 | Comparables por atributos (`corregimiento`, `bedrooms`, `bathrooms`, `area_m2`), k=5. Corrección de scope heredada de Feature 1.2 (no `ST_Distance`, sin coordenadas reales). Restricción estructural: solo `tipo_inmueble="Apartamentos"`. |
| 3.1.2 | Precio estimado = promedio simple (uniforme) de comparables, no ponderado. Manejo explícito de cobertura insuficiente (<5 comparables). |
| 3.1.3 | **Corrección crítica de umbral**: ±1.5×MAE ($281,315.21), nunca el 0.10 desactualizado del pickle. MAE re-derivado desde el pipeline real, no copiado del paper. |
| 3.1.4 | MAE por zona (nuevo, no existía en el notebook) — **hallazgo de heterogeneidad**: San Francisco +60.7% sobre el MAE global, Betania -72.4%. Documentado como limitación para el paper. |
| 3.1.5 | Orquestación end-to-end (`evaluar_precio_propiedad()`), con separación `registro_db`/`diagnostico` por gap de schema. |
| 3.1.6 | **Hallazgo de fuga de datos**: 833/1,042 propiedades elegibles eran su propio comparable (training set del KNN). Corregido excluyendo auto-match por `listing_id`. Distribución final: 85.2%/7.7%/7.1% (amarillo/verde/rojo), dentro de tolerancia frente al paper (82.3%/9.1%/8.6%). Carga real: 1,042/1,042, 0 fallos. |

**Acta específica del hallazgo:** `Context-MD/Hallazgo_Fuga_Datos_Batch_3_1_6_Cierre.md`

---

## Feature 3.2 — Segmentación de Mercado KMeans (9 SP) — CERRADA hoy

**Documentación detallada:** `Feature_3_1_3_2_Property_Valuation_Documentacion.md`

| Tarea | Resultado |
|---|---|
| 3.2.1–3.2.3 | Ya cerradas en sesión previa (Feature 6.2.5). k=2 óptimo (Silhouette=0.388) — **desviación formal ya documentada del WBS original (k=5)**, no reabierta. |
| 3.2.4 | Etiquetado cualitativo con **excepción documentada** de revisión de una sola persona (Besto + Claude), mismo precedente de Zone Health. Acta propia: `Feature_3_2_4_Etiquetado_Clusters_KMeans_Acta_Excepcion.md`. Cluster 0 = compacto/económico (n=662), cluster 1 = grande/premium (n=380). |
| 3.2.5 | Riesgo de fuga de datos **evaluado explícitamente y descartado** (mecanismo de centroides, no de vecinos individuales; sin partición train/test que proteger). Carga real: 1,042/1,042, reproducción exacta de `fit_predict()` original. |

---

## Feature 3.3 — Comparación Metodológica RF vs. KNN (5 SP) — Cerrada en sesión previa

No requirió trabajo en esta sesión. Cierre de referencia: `Feature_6_2_4_M2_KNN_RF_Cierre.md`.

**Resultado:** Random Forest supera a KNN en error absoluto (MAE $132,388 test vs. $149,270 — 20.4% mejor), pero **no se despliega en producción** — su función es evidencia metodológica comparativa para el paper (`.feature_importances_` como ranking de drivers de precio sin costo de SP adicional), no un servicio de valuación activo. El semáforo de producción sigue siendo KNN.

---

## Feature 3.4 — Quality Scorer LLM (10 SP) — Cerrada en sesión previa

No requirió trabajo en esta sesión. Cierre de referencia: `Feature_6_2_6_M2_QualityScorer_Cierre.md` (experimentación, n=150) + batch de producción sobre catálogo completo (script `pipeline/scripts/escalar_quality_scorer_6_2_6.py`, ya cargado en `valuacion_quality_scorer`, 1,168 filas, Feature 1.5.4).

**4 dimensiones evaluadas** (decisión explícita del usuario sobre las 4 originales del WBS, sin equivalencia 1:1, documentada en `Gobernanza_WBS_vs_Feature_6_2.md`): completitud informativa, calidad de presentación/redacción, diferenciadores/amenidades, transparencia de precio. Verificado contra Cuadro IX/X del paper — coincidencia exacta.

---

## Feature 3.5 — Endpoint de Transparencia del Modelo (3 SP) — CERRADA hoy

| Tarea | Resultado |
|---|---|
| 3.5.1 | Export de 209 pares predicho/real del **conjunto de test puro** del KNN (verificado por doble aborto de construcción: sin intersección con train, coincidencia exacta con el mapeo ya generado en 3.1.6). **Hallazgo de denominador**: el MAE porcentual (33.4%) usa la media de precio del catálogo completo (1,042 filas), no la media de las 209 filas de test (que da 32.3%, un número distinto y no publicado) — documentado explícitamente para prevenir confusión futura. |
| 3.5.2 | Endpoint `GET /valuation/transparencia`, servido desde CSV cacheado en memoria (no tabla nueva — dataset fijo salvo reentrenamiento). Verificación de integridad en tiempo de arranque: recalcula el MAE desde el CSV cargado y lo compara contra la constante ya validada antes de servir cualquier respuesta — falla explícito (500) si no coincide, nunca sirve un número no verificado. Response incluye aclaración textual de la población de cada MAE, para que el consumidor (frontend o lector del paper) no confunda los dos denominadores. |

---

## Hallazgos transversales de la épica — candidatos a la Sección de limitaciones del paper (Feature 6.1)

1. **El semáforo KNN solo cubre `tipo_inmueble="Apartamentos"`** — el motor de valuación no es universal sobre el catálogo, es universal dentro del subconjunto de apartamentos. Limitación estructural del modelo entrenado, no de la implementación.
2. **El error del modelo (MAE) es heterogéneo entre corregimientos** — San Francisco concentra el error global (+60.7%), posiblemente por su cola de precios de lujo; Betania tiene un error real ~4× menor que el umbral global aplicado. El umbral único de ±$281,315 sobre-etiqueta "amarillo" en zonas de bajo error y podría sub-detectar desviaciones reales en San Francisco.
3. **Fuga de datos detectada y corregida en el batch de producción de KNN** — evidencia citable directamente como ejemplo de rigor metodológico: detección experimental aislada (comparación train vs. test), corrección quirúrgica (exclusión de auto-comparable), verificación de no-regresión.
4. **Etiquetado de clusters KMeans con revisión de una sola persona**, no las ≥2 exigidas por la condición de Done original — excepción documentada, reabrible antes de la defensa si hay tiempo del equipo completo.
5. **RF supera a KNN en error absoluto pero no se despliega** — decisión de producto documentada, no un descarte accidental; el valor de RF en el proyecto es interpretativo (feature importances), no predictivo en producción.

---

## Decisiones técnicas cerradas de toda la épica — no reabrir sin nueva evidencia

1. Semáforo: KNN en producción, umbral ±1.5×MAE dinámico, nunca el 0.10 del pickle.
2. KMeans: k=2 (no k=5 del WBS original), sin persistir etiqueta textual junto al entero.
3. RF: evidencia comparativa de tesis, no servicio de producción.
4. Quality Scorer: 4 dimensiones ya cerradas de 6.2.6 (no las 4 originales del WBS).
5. Todo comparable de KNN debe excluir auto-match por `listing_id` cuando la propiedad evaluada pudo ser parte del training set.
6. El MAE porcentual "oficial" del proyecto (33.4%) siempre usa la media del catálogo completo (1,042 filas) como denominador — nunca la media de un subconjunto.

---

## Estado de infraestructura al cierre de Épica 3.0

| Componente | Estado |
|---|---|
| `evaluar_precio_propiedad()` (KNN + semáforo) | Producción, con exclusión de fuga de datos |
| `valuacion_semaforo_knn` | 1,042/1,042 filas |
| `valuacion_segmento_kmeans` | 1,042/1,042 filas |
| `valuacion_quality_scorer` | 1,168 filas (sesión previa) |
| `GET /valuation/transparencia` | Producción, verificación de integridad en arranque |
| Modelo RF | Serializado, evidencia de tesis, no expuesto en API |
| `analisis_mae_por_zona_3_1_4.py` | Artifact de diagnóstico, evidencia para el paper |

**Épica 3.0 lista para ser consumida por Épica 4 (`4.3.1`, orquestación M3) — junto con Épica 2.0, que ya provee `POST /match/score`.**

---

## Pendientes de gobernanza que sobreviven al cierre de la épica (no bloquean código)

1. Registrar en `REIP_WBS.md`/Excel el cierre formal de las 5 features de Épica 3, con fecha 2026-07-15.
2. Incorporar los 5 hallazgos transversales listados arriba a la Sección de limitaciones del paper (Feature 6.1).
3. Decidir si se convoca revisión formal de ≥2 personas para el etiquetado de KMeans antes de la defensa, o si la excepción documentada queda como definitiva.
