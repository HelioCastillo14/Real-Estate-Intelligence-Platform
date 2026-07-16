# Feature 1.5.5 — Tablas `perfiles_lifestyle` y `conjunto_referencia_m1` — Acta de Cierre

**Fecha de ejecución:** 2026-07-15
**Fuente del esquema:** `Ajuste_WBS_1_5_5_Esquema_ConjuntoReferenciaM1.md`
**Fuente de los datos:** `pipeline/data/processed/conjunto_referencia_m1_6_2_3.json` (materializado en esta sesión desde `notebooks/01_m1_preference_matching.ipynb`, Feature 6.2.3, cerrada 2026-07-13)

---

## 1. Contexto — discrepancia de formato resuelta

El WBS original (`2.3.1`) especificaba 15-25 pares perfil-propiedad con ranking conocido por construcción. Lo que `6.2.3` construyó y validó (Precision@k aprobado, CP-2) son 6 perfiles de lifestyle con reglas estructuradas + criterio cualitativo, cada uno matched contra un conjunto de propiedades — formato distinto, nunca resuelto formalmente hasta esta sesión.

**Se adoptó el formato real** (perfil + reglas + relación N:M), no reconstrucción en pares. Justificación: más barato, más fiel a la evidencia ya aprobada, consistente con el patrón de M3.

## 2. Hallazgo crítico — ground truth no persistido, materializado en esta sesión

Los `listing_id` del ground truth de `6.2.3` nunca se guardaron en disco — vivían solo en memoria del notebook (`ground_truth_final`), recalculados en cada ejecución. Solo los conteos agregados (43-199 por perfil) sobrevivieron como output guardado.

**Decisión tomada:** congelar el ground truth (no recalcularlo dinámicamente), para preservar la validez comparativa del Precision@k ya aprobado en `6.2.3` — un ground truth que se mueve con el catálogo invalidaría retroactivamente cualquier evaluación futura de esa métrica.

**Ejecución:** se extrajo la lógica exacta de las celdas 2/5/7/8/11 del notebook (sin reinterpretación) a `pipeline/scripts/materializar_ground_truth_m1.py`, ejecutado una vez contra `catalogo_residencial_limpio_6_2_1.csv`, produciendo `pipeline/data/processed/conjunto_referencia_m1_6_2_3.json` con hash SHA-256 del catálogo fuente para trazabilidad de versión.

**Verificación de fidelidad:** los conteos finales coincidieron exactamente con los ya reportados y aprobados en `Feature_6_2_3_M1_Preference_Matching_Cierre.md` — sin discrepancia en ningún perfil.

| Perfil | n_solo_estructural | n_ground_truth |
|---|---|---|
| familia_con_ninos | 109 | 49 |
| profesional_joven | 236 | 153 |
| pareja_presupuesto_medio | 168 | 60 |
| inversionista_renta_corta | 257 | 199 |
| retirado_tranquilidad | 62 | 43 |
| presupuesto_ajustado_sin_auto | 169 | 73 |

## 3. Caso especial resuelto — criterio dinámico de `pareja_presupuesto_medio`

Este perfil usa un criterio dinámico (`zone_health_composite >= 0.5`), no una lista fija de corregimientos como los otros 5. Para no dejar este perfil con trazabilidad más débil que el resto (dependiente de que `corregimientos.zone_health_score` no cambie en el futuro), se resolvió y congeló explícitamente la lista de zonas que cumplían el criterio al momento de materializar, calculada de forma independiente contra `zone_health_composite_1_4_6.json`:

**Zonas resueltas (composite ≥ 0.5):** Bella Vista, Betania, El Cangrejo, Marbella, Obarrio, San Francisco (6 de 9). Excluidas: Parque Lefevre (0.376), Pedregal (0.108), Costa del Este (sin score, no por no alcanzar umbral).

**Verificación cruzada:** esta lista coincidió exactamente con la lista estática ya presente en `reglas_estructurales.corregimientos` del JSON original del notebook — confirma que el cálculo dinámico reproduce fielmente lo que `6.2.3` usó, aunque sugiere que la implementación original del notebook probablemente ya usaba una lista estática pese a la etiqueta "dinámico" en la documentación de intención.

## 4. Esquema — dos tablas

`perfiles_lifestyle` (reglas, estables) separada de `conjunto_referencia_m1` (membresía congelada, relación N:M hacia `propiedades`) — evita forzar ambas en una tabla ancha y permite FK real e integridad referencial garantizada por Postgres, no solo por el código de aplicación.

### 4.1 Migración de estructura

`supabase/migrations/20260715040002_perfiles_lifestyle_y_conjunto_referencia_m1.sql` — aplicada exitosamente. Verificado orden correcto dentro del archivo (`perfiles_lifestyle` antes que `conjunto_referencia_m1`, requerido por la FK entre ambas).

| Constraint | Verificado |
|---|---|
| `perfiles_lifestyle_pkey` — `PRIMARY KEY (perfil)` | ✓ |
| `conjunto_referencia_m1_pkey` — `PRIMARY KEY (perfil, listing_id)` | ✓ |
| `conjunto_referencia_m1_perfil_fkey` — FK → `perfiles_lifestyle(perfil)` | ✓ |
| `conjunto_referencia_m1_listing_id_fkey` — FK → `propiedades(listing_id)` | ✓ |
| `conjunto_referencia_m1_flag_sintetico_check` — `CHECK (flag_sintetico = true)` | ✓ |

`supabase_migrations.schema_migrations` con 4 versiones registradas, sin duplicados ni re-ejecuciones de migraciones previas.

## 5. Bloqueante encontrado y resuelto en el camino — carga de `propiedades`

Al intentar cargar `conjunto_referencia_m1`, se detectó que `propiedades` (estructura creada en 1.5.1) seguía con **0 filas** — la carga del catálogo real nunca tuvo una tarea formal explícita dentro de Feature 1.5. La FK de `conjunto_referencia_m1.listing_id` hacia `propiedades.listing_id` hacía esta carga un prerequisito real, no solo conveniente.

**Resuelto en la misma sesión:** validación en seco del catálogo (`catalogo_residencial_limpio_6_2_1.csv`, 1,177 filas) contra todos los CHECK/NOT NULL/UNIQUE de la tabla — limpia, sin discrepancias. Carga ejecutada vía `pipeline/scripts/cargar_propiedades.py`: **1,177 filas insertadas**, `embedding`/`geom` NULL explícito (fuera de alcance de hoy), `imagenes` NULL en 1 fila (`listing_id 137025`, fallo de red ya documentado en 1.5.1).

**Nota de gobernanza:** esta carga no tiene ID de tarea propio en el WBS actual de Feature 1.5 — quedó ejecutada como prerequisito de 1.5.5. Vale la pena decidir formalmente dónde se registra esta tarea (¿retroactivamente en 1.5.1, o como ítem nuevo?) para que el WBS refleje con precisión qué se hizo y cuándo.

## 6. Carga de datos — verificación de cobertura y resultado final

**Verificación previa de cobertura:** 577 pares `(perfil, listing_id)` corresponden a 378 `listing_id` distintos (overlap real entre perfiles — ej. `profesional_joven` e `inversionista_renta_corta` comparten propiedades, consistente con la interacción ya diagnosticada en `6.2.3` entre el componente semántico y la regla de exclusión por keyword). Los 378 IDs distintos confirmados presentes en `propiedades` antes de cargar — 0 faltantes.

**Resultado de la carga:** transacción única, verificación de conteo por perfil corrida **antes** del commit (abort automático si algo no cuadraba).

| Perfil | `n_ground_truth` | `count_real` | Estado |
|---|---|---|---|
| familia_con_ninos | 49 | 49 | ✓ |
| profesional_joven | 153 | 153 | ✓ |
| pareja_presupuesto_medio | 60 | 60 | ✓ |
| inversionista_renta_corta | 199 | 199 | ✓ |
| retirado_tranquilidad | 43 | 43 | ✓ |
| presupuesto_ajustado_sin_auto | 73 | 73 | ✓ |

**Total insertado en `conjunto_referencia_m1`: 577.** Sin discrepancias.

## 7. Decisiones confirmadas por esta ejecución (no reabrir)

- **`conjunto_referencia_m1` es un snapshot congelado**, no una vista recalculada — ligado a un catálogo específico vía `hash_catalogo_fuente`, preservando la comparabilidad del Precision@k ya aprobado en `6.2.3`.
- **`pareja_presupuesto_medio` tiene su criterio dinámico resuelto y congelado explícitamente** (`corregimientos_resueltos_al_materializar`) — auditable sin depender de que `corregimientos.zone_health_score` no cambie.
- **`flag_sintetico = TRUE` forzado por CHECK** en las 577 filas — este conjunto nunca se mezcla con datos de usuario real, garantizado por Postgres, no solo por convención de código.
- **`propiedades` está cargada con las 1,177 filas del catálogo real**, con `embedding`/`geom` pendientes de pasos posteriores (Épica 2 y `1.5.1` respectivamente).

## 8. Pendiente explícito, fuera de alcance de esta Acta

1. **Overlap de 199 pares entre perfiles (577 → 378 únicos)** — cuantificación numérica del problema ya diagnosticado cualitativamente en `6.2.3` (interacción embedding/keyword de exclusión). Vale la pena citar esta cifra si se documenta esa limitación con más detalle en el paper.
2. **Registrar formalmente en el WBS la carga de `propiedades`** — ejecutada hoy como prerequisito no planeado de `1.5.5`, sin ID de tarea propio actualmente.
3. **Re-materialización futura del ground truth** — si el catálogo cambia sustancialmente, decidir (gobernanza académica, no técnica) si se re-congela o se mantiene como snapshot histórico fijo.

## 9. Estado

**Feature 1.5.5: CERRADA.** Estructura y datos verificados en ambas tablas, sin discrepancias. Como efecto colateral necesario, `propiedades` (1.5.1) queda también con datos reales cargados por primera vez.

**Estado consolidado de Feature 1.5 tras esta sesión:**

| Tarea | Estado |
|---|---|
| 1.5.1 | ✓ Cerrada (estructura + datos, este último no planeado originalmente para hoy) |
| 1.5.2 | ✓ Cerrada (estructura + datos) |
| 1.5.3 | Investigación pendiente |
| 1.5.4 | Diseño pendiente |
| 1.5.5 | ✓ Cerrada (estructura + datos) |
| 1.5.6 | Bloqueada por Épica 2 (`2.1.3`, embeddings) |
