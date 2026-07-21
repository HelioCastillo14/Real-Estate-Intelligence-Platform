# Feature 1.5.4 — Tablas `valuacion_*`, `scores_compatibilidad`, `sesiones_consulta` — Acta de Cierre

**Fecha de ejecución:** 2026-07-15
**Fuente del esquema:** `Ajuste_WBS_1_5_4_Esquema_Scores.md`
**Fuente de los datos:** `pipeline/models/quality_scores_produccion_final.csv` (única fuente con datos reales cargables en esta sesión)

---

## 1. Contexto — tres fuentes en tres estados de madurez distintos

Verificación previa confirmó que las 3 fuentes anticipadas por el WBS original (Quality Scorer, semáforo KNN, segmento KMeans) están en estados radicalmente distintos: Quality Scorer completo y listo; KNN/KMeans con modelo entrenado pero sin batch corrido; y M1 (compatibilidad) **sin ningún artifact de producción**, ni siquiera un `.pkl` — solo código de notebook, a diferencia de M2. El explainer de `2.2.4` tampoco existe ni como placeholder.

**Consecuencia:** las 5 tablas se crearon con estructura completa hoy. Solo `valuacion_quality_scorer` recibió datos reales — las 4 restantes quedan vacías, documentado como estado esperado, no error.

## 2. Decisión de fondo — tablas separadas por fuente, no una tabla ancha

Mismo criterio ya aplicado en `1.5.5` (`perfiles_lifestyle`/`conjunto_referencia_m1`): Quality Scorer, KNN y KMeans tienen payloads y ciclos de vida estructuralmente distintos. Se crearon 3 tablas independientes (`valuacion_quality_scorer`, `valuacion_semaforo_knn`, `valuacion_segmento_kmeans`) en vez de una tabla ancha con columnas `NULL` por fuente no cargada.

## 3. Decisiones de diseño específicas

- **`valuacion_semaforo_knn.mae_referencia` y `.multiplo_mae` se guardan por fila**, no en tabla de configuración aparte — congelamiento auditable, mismo criterio que `corregimientos_resueltos_al_materializar` en `1.5.5`.
- **`valuacion_segmento_kmeans.cluster_id` se guarda como entero crudo (0/1), sin interpretación embebida** ("premium"/"económico") — esa etiqueta es prosa post-hoc no codificada en ningún artifact; si se necesita, debe vivir en tabla de metadata separada, nunca congelada como string en cada fila.
- **`scores_compatibilidad.peso_estructurado`/`.peso_semantico` se guardan por fila** (default 0.6/0.4) — M1 no tiene artifact serializado, los pesos son constantes de notebook sin mecanismo de versionado; si se recalibran en el futuro, cada score sigue siendo auditable con el peso real usado.
- **`scores_compatibilidad.explicacion` reservada, nullable** — para el explainer de `2.2.4`, confirmado sin implementación (`WBS_Pendiente_Epicas_2_3_4.md`).
- **`scores_compatibilidad` tiene CHECK compuesto** garantizando que cada score proviene de exactamente un origen: perfil de referencia batch (`perfil_lifestyle`) o sesión de usuario en vivo (`sesion_id`), nunca ambos ni ninguno.
- **`sesiones_consulta.extraccion` se guarda como `jsonb`**, no columnas individuales — preserva fidelidad si el contrato de M3 evoluciona, mismo criterio que `propiedades_raw` en `amenidades`. `confianza` se extrae también como columna propia para permitir análisis de calibración sin deserializar JSON en cada consulta.
- **Los 20 registros de medición final de M3 (`medicion_final_6_2_7_checkpoint.pkl`) NO se cargaron a `sesiones_consulta`** — son consultas de prueba diseñadas para medición (Sección IV-A6 del paper), no tráfico real; cargarlas contaminaría cualquier análisis futuro de tasa de fallback en producción.

## 4. Salvaguarda aplicada — protección explícita del paper ya finalizado

Dado que el paper del equipo ya es versión final, se estableció una regla operativa para esta tarea: **ninguna carga debe alterar ni contradecir un número ya reportado.**

**Verificación aplicada antes de cualquier inserción:** el script de carga comparó media y desviación estándar de las 4 dimensiones de Quality Scorer contra el Cuadro IX del paper, con tolerancia de ±0.01, **deteniéndose antes de importar siquiera el módulo de conexión a Supabase** si hubiera discrepancia. Resultado: coincidencia exacta en las 4 dimensiones (completitud 4.66±0.67, presentación 4.73±0.61, diferenciadores 4.51±0.84, transparencia 3.68±1.81) — sin discrepancia que reportar, tanto en el dry-run como en la ejecución real.

**Hallazgo relacionado, verificado en esta sesión, sin efecto sobre el paper:** el `.pkl` de KNN (`knn_semaforo_precio_6_2_4.pkl`) tiene un `umbral_semaforo=0.1` desactualizado — el notebook recalibra a `±1.5×MAE` después de serializar el pickle, y esa recalibración nunca se volvió a persistir. **El paper (Sección IV-A3) ya reporta el valor correcto y recalibrado** (±1.5×MAE, ±$281,315, coincide exactamente con `mae_knn_test` real del notebook) — confirmando que el paper se escribió leyendo la lógica de producción real, no el metadata desactualizado del pickle. La corrección del `.pkl` queda pendiente como trabajo de infraestructura para el futuro batch `3.1.6`, sin urgencia relacionada con el paper.

## 5. Migración de estructura

`supabase/migrations/20260715040004_scores_valuacion_compatibilidad_sesiones.sql` — aplicada exitosamente. 5 `CREATE TABLE` en orden correcto de dependencias (`sesiones_consulta` antes que `scores_compatibilidad`, que la referencia). `supabase_migrations.schema_migrations` con 6 versiones, sin re-ejecución de migraciones previas.

| Verificación | Resultado |
|---|---|
| 34 columnas totales, 5 tablas, tipos correctos | ✓ |
| `chk_scores_compatibilidad_origen` (XOR perfil/sesión) | ✓ |
| 3 FK hacia `propiedades(listing_id)` | ✓ |
| FK `scores_compatibilidad.sesion_id` → `sesiones_consulta(id)` | ✓ |
| FK `scores_compatibilidad.perfil_lifestyle` → `perfiles_lifestyle(perfil)` | ✓ |
| `CHECK (cluster_id in (0,1))` | ✓ |
| `CHECK (categoria_semaforo in ('verde','amarillo','rojo'))` | ✓ |
| `CHECK (categoria_resultado in (4 valores))` | ✓ |
| `idx_sesiones_consulta_categoria` (btree) | ✓ |
| 19 constraints totales | ✓ |

## 6. Carga de datos — resultado final

Transacción única, verificación de media/std corrida **antes** del commit (mismo patrón de abort-before-commit que en tareas anteriores).

**1,168 filas insertadas en `valuacion_quality_scorer`.** Verificación independiente contra la tabla real (`COUNT(*)` directo, no solo el mensaje del script): 1,168 — coincide exactamente.

`valuacion_semaforo_knn`, `valuacion_segmento_kmeans`, `sesiones_consulta`, `scores_compatibilidad`: permanecen vacías, estado esperado y documentado, no pendiente de esta Acta.

## 7. Decisiones confirmadas por esta ejecución (no reabrir)

- **`scores_valuacion` es en realidad 3 tablas separadas**, no una entidad única — decisión de diseño confirmada, no solo nomenclatura del WBS original.
- **El conteo cargado (1,168) es idéntico al que el paper ya reporta** — no hay divergencia entre lo que la base de datos contiene y lo que el documento académico final describe.
- **El `.pkl` de KNN necesita corrección antes de que el batch `3.1.6` corra** — pendiente de infraestructura, verificado sin impacto sobre resultados ya publicados.

## 8. Pendiente explícito, fuera de alcance de esta Acta

1. Corrección del `.pkl` de KNN (`mae_knn_test` y `multiplo_mae=1.5` persistidos explícitamente) — prerequisito de `3.1.6`, no de esta feature.
2. Implementación real de M1 en producción (`pipeline/`, no solo notebook) — prerequisito para poblar `scores_compatibilidad`.
3. Implementación del explainer (`2.2.4`) — prerequisito para poblar `scores_compatibilidad.explicacion`.
4. Decisión sobre si los 20 registros de medición final de M3 se cargan alguna vez a `sesiones_consulta` con un flag distintivo, o permanecen exclusivamente en su `.pkl` de checkpoint.

## 9. Estado

**Feature 1.5.4: CERRADA.** Estructura completa en las 5 tablas, datos reales cargados donde existían (Quality Scorer), y verificación explícita de que ningún número del paper ya publicado fue alterado o contradicho.

**Estado consolidado de Feature 1.5 tras esta sesión:**

| Tarea | Estado |
|---|---|
| 1.5.1 | ✓ Cerrada (estructura + 1,177 filas de `propiedades`) |
| 1.5.2 | ✓ Cerrada (estructura + 9 filas de `corregimientos`) |
| 1.5.3 | ✓ Cerrada (estructura + 238 filas de `amenidades`) |
| 1.5.4 | ✓ Cerrada (5 tablas, 1,168 filas de `valuacion_quality_scorer`, resto vacío por diseño) |
| 1.5.5 | ✓ Cerrada (estructura + 577 filas de `conjunto_referencia_m1`) |
| 1.5.6 | Bloqueada por Épica 2 (`2.1.3`, embeddings) |

**5 de 6 tareas cerradas.** Solo `1.5.6` permanece pendiente, bloqueada por una dependencia externa a Feature 1.5.
