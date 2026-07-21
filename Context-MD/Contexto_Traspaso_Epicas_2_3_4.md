# Contexto de Traspaso — Épicas 2.0, 3.0 y 4.0 (post-cierre de Feature 1.5)

**Fecha:** 2026-07-15
**Propósito:** retomar la implementación de Épicas 2, 3 y 4 en una sesión nueva de Claude Code, con el contexto necesario sin haber estado en la sesión donde se cerró Feature 1.5.

---

## 0. Qué acaba de pasar — resumen de la sesión anterior

Feature 1.5 (esquema de base de datos, Supabase/PostgreSQL/PostGIS/pgvector) quedó cerrada al 83% (5 de 6 tareas) el 2026-07-15, en una sesión de arquitectura/verificación (no Claude Code). **8 tablas creadas, 6 migraciones aplicadas, ~3,180 filas cargadas con datos reales**, cada una con verificación de trazabilidad contra su fuente. Ver `Ajuste_WBS_1_5_2_Esquema_Corregimientos.md`, `Ajuste_WBS_1_5_3_Esquema_Amenidades.md`, `Ajuste_WBS_1_5_4_Esquema_Scores.md`, `Ajuste_WBS_1_5_5_Esquema_ConjuntoReferenciaM1.md` y sus respectivas Actas de cierre (`Feature_1_5_X_..._Cierre.md`) para el detalle completo de cada decisión.

**Documento de trabajo principal para retomar:** `WBS_Pendiente_Epicas_2_3_4.md` (versión 2026-07-15, actualizada) — reemplaza la versión del 2026-07-14, que tenía `1.5.1` como bloqueante activo (ya no lo es).

---

## 1. Estado real de la base de datos hoy — verificado, no asumido

| Tabla | Filas | Estado |
|---|---|---|
| `propiedades` | 1,177 | Estructura completa. **`embedding` y `geom` en NULL en las 1,177 filas** — pendiente Épica 2 (embedding) y trabajo separado (geom sintético vía `ST_GeneratePoints`, no cubierto en este documento) |
| `corregimientos` | 9 | Completa — 5 oficiales con polígono real, 4 no oficiales con `geom=NULL` + `hereda_de` |
| `amenidades` | 238 | Completa — 6 zonas cubiertas (El Cangrejo/Marbella/Obarrio sin amenidades propias, limitación de datos documentada) |
| `perfiles_lifestyle` | 6 | Completa |
| `conjunto_referencia_m1` | 577 | Completa — snapshot congelado, no recalcula dinámicamente |
| `valuacion_quality_scorer` | 1,168 | Completa, verificada contra Cuadro IX/X del paper (coincidencia exacta) |
| `valuacion_semaforo_knn` | 0 | **Tabla existe, vacía** — esperando batch `3.1.6` (ver §3, bloqueante activo) |
| `valuacion_segmento_kmeans` | 0 | **Tabla existe, vacía** — esperando batch `3.2.5` |
| `scores_compatibilidad` | 0 | **Tabla existe, vacía** — esperando implementación real de M1 en producción (no existe ni como script, solo notebook) |
| `sesiones_consulta` | 0 | **Tabla existe, vacía** — esperando `4.3.1` (endpoint real) |

**No asumir que "tabla vacía" significa "bloqueada por esquema" — en todos los casos de arriba, el esquema ya está listo y verificado. Lo que falta es exclusivamente el código de aplicación/batch que la puebla.**

## 2. Conexión a Supabase — ya configurada, reutilizar el patrón

- `DATABASE_URL` en `.env` (raíz del repo) apunta al **connection pooler** de Supabase (`aws-0-us-east-1.pooler.supabase.com:5432`, modo *session*), no al host directo — el host directo solo resuelve IPv6 y este entorno no tiene salida IPv6. **No revertir esto.**
- Todos los scripts de carga de la sesión anterior (`pipeline/scripts/cargar_*.py`) usan `psycopg2` + `load_dotenv()` + transacción única (`with conn:`) + SQL parametrizado. **Replicar este patrón para cualquier script nuevo** (ej. `cargar_semaforo_knn.py`, `cargar_segmento_kmeans.py`).
- Regla operativa sin excepción: **ninguna migración ni carga se ejecuta contra Supabase sin confirmación explícita del usuario en el momento** — es infraestructura compartida. Todos los scripts previos dejan la llamada de ejecución real comentada por defecto (`# cargar(df)`), con un dry-run que imprime resumen antes de conectar.
- `supabase db push` aplica migraciones por timestamp; `supabase migration list` muestra qué está aplicado vs. pendiente. 6 migraciones ya aplicadas (`20260715032111` hasta `20260715040004`) — cualquier migración nueva de Épica 2/3/4 debe usar timestamp posterior.

## 3. Bloqueantes reales activos — leer antes de empezar cualquier tarea

### 3.1 `2.1.3` — decisión de scope ya tomada, no reabrir

**Calcular embeddings para las 1,177 filas completas de `propiedades`, NO limitarse a las 1,110 que `pipeline/models/embeddings_catalogo_6_2_3_raw.pkl` ya tiene precalculadas.**

El pickle de `6.2.3` excluye 67 filas (53 `zona_no_determinada` + 14 `precio_no_evaluable`) por un filtro de validez específico del ground truth de M1 — ese filtro es responsabilidad de la lógica de evaluación de M1 en tiempo de consulta, no debe heredarse a la existencia del embedding en la tabla maestra (M3 también consume esta columna, sin esa restricción). Las 1,110 ya calculadas se reutilizan directo; solo hay que calcular las 67 restantes. Ver Anexo A de `WBS_Pendiente_Epicas_2_3_4.md` para la justificación completa.

### 3.2 `3.1.3` / `3.1.6` — pickle de KNN desactualizado, corregir antes de cargar

`pipeline/models/knn_semaforo_precio_6_2_4.pkl` tiene `umbral_semaforo: 0.1` (±10%) serializado en la sección 8 del notebook — pero la producción real usa `±1.5×MAE` (sección 9 del notebook, nunca vuelto a persistir en el pickle).

**Antes de correr el batch de `3.1.6`:** re-serializar el `.pkl` con `mae_knn_test` ($187,543) y `multiplo_mae` (1.5) explícitos. Si se carga el batch sin corregir esto, la distribución resultante **no va a coincidir** con la ya reportada y aprobada en el paper (82.3% amarillo / 9.1% verde / 8.6% rojo, umbral ±$281,315).

**Verificado sin impacto en el paper ya publicado** — el paper usa el valor correcto porque se escribió leyendo el notebook, no el pickle. Este hallazgo es puramente de infraestructura futura.

### 3.3 El paper del equipo ya es versión final — regla de oro para toda esta épica

**Cualquier carga de datos, corrección de artifact, o recálculo debe verificarse contra los números ya publicados en el paper (`REIP-Paper-HCastillo-JCopri-AMontoya-DRivas.pdf`) antes de ejecutarse contra Supabase.** Si un resultado nuevo no coincide con lo que el paper ya reporta, **detenerse y preguntar antes de insertar**, no después. Esto ya se aplicó exitosamente en la sesión anterior (verificación de medias/std de Quality Scorer contra Cuadro IX, umbral de semáforo contra Sección IV-A3) — replicar ese patrón para cualquier carga nueva relacionada con M1/M2/M3.

**Cifras clave ya publicadas, para referencia rápida sin tener que releer el paper completo:**
- MAE KNN: $165,707 (CV) / $187,543 (test) — 33.4% del precio promedio
- MAE Random Forest: $132,388 (CV) / $149,270 (test) — 26.6%, 20.4% mejor que KNN, no desplegado en producción
- Semáforo: 82.3% amarillo (n=172) / 9.1% verde (n=19) / 8.6% rojo (n=18), umbral ±$281,315 (±1.5×MAE test)
- KMeans: k=2, Silhouette=0.388, cluster 0 (n=662, económico) / cluster 1 (n=380, premium) — **sin nombre de cluster persistido en ningún artifact**, solo interpretación de prosa
- Quality Scorer: n=1,168, completitud 4.66±0.67, presentación 4.73±0.61, diferenciadores 4.51±0.84, transparencia 3.68±1.81
- Precision@k de M1 (6 perfiles): ver Cuadro III/IV del paper — efecto heterogéneo, `profesional_joven` con 0.000 en las 3 métricas (degradación diagnosticada, no error)
- M3: 50% éxito, 20% fallback cobertura, 5% fallback fuera de tema, 25% fallback ambigüedad (n=20, conjunto adversarial, no tasa de producción)

## 4. Decisiones de diseño ya cerradas — no reabrir sin nueva evidencia

- **`propiedades.geom`** es sintético (`ST_GeneratePoints`), nunca insumo de modelo — distinto del `geom` real de `corregimientos`.
- **`corregimientos` tiene 9 filas** (5 oficiales + 4 heredadas por referencia, no duplicación) — `El Cangrejo`/`Marbella`/`Obarrio` heredan de Bella Vista; `Costa del Este` no tiene padre (`hereda_de=NULL`, `estado_zone_health='sin_score_datos_insuficientes'`).
- **`amenidades` no cubre El Cangrejo/Marbella/Obarrio** — el único archivo de origen para esas zonas (`amenidades_betania_obarrio_cangrejo_marbella_osm.geojson`) resultó no distinguible por zona individual, excluido con evidencia.
- **`conjunto_referencia_m1` es un snapshot congelado**, ligado a un hash del catálogo fuente — no se recalcula dinámicamente, preserva la validez del Precision@k ya aprobado (CP-2).
- **`scores_valuacion` son 3 tablas separadas** (`valuacion_quality_scorer`, `valuacion_semaforo_knn`, `valuacion_segmento_kmeans`), no una tabla ancha — ciclos de vida distintos.
- **`valuacion_segmento_kmeans.cluster_id` guarda el entero crudo (0/1)**, sin interpretación textual embebida — cualquier etiqueta ("premium"/"económico") debe vivir en tabla de metadata separada si se formaliza.
- **`scores_compatibilidad.peso_estructurado`/`.peso_semantico` se guardan por fila** (default 0.6/0.4) — M1 no tiene artifact serializado, los pesos son constantes de notebook sin versionado.

## 5. Pendientes de gobernanza — no bloquean código, pero no están resueltos

1. **Validación formal del consejo académico para la exclusión de visualización de Pedregal** — pendiente desde Feature 1.4, visible ahora en `corregimientos.motivo_visualizacion`.
2. **Posible re-auditoría de Zone Health de Parque Lefevre** — se descubrió que 13 amenidades etiquetadas como "Costa del Este" caen geométricamente en el polígono de Parque Lefevre (frontera real, documentada en Feature 1.3.7 §5.3), no incluidas en el composite original de Feature 1.4. No se recalculó — decisión de gobernanza académica, no técnica.
3. **`3.2.4`** — confirmar si el etiquetado informal de los 2 clusters de KMeans requiere revisión formal por ≥2 miembros del equipo.
4. **Registro retroactivo en el WBS** de la carga del catálogo de `propiedades` (1,177 filas) — se ejecutó como prerequisito no planeado de `1.5.5`, sin ID de tarea propio actualmente.

## 6. Cómo trabajar en esta sesión — patrón que funcionó bien, replicarlo

1. **Verificar el artifact/archivo real antes de diseñar cualquier esquema o lógica** — no asumir que la documentación describe con exactitud lo que hay en el archivo. En la sesión anterior esto reveló: un ground truth que nunca se persistió (`1.5.5`), un archivo "combinado" sin distinción interna real (`1.5.3`), un pickle desactualizado (`3.1.3`), y un gap de M1 sin ningún artifact de producción (`1.5.4`).
2. **Dos confirmaciones separadas para cualquier acción contra Supabase**: primero estructura (migración), después datos (carga) — nunca combinadas en un solo paso sin revisión intermedia.
3. **Dry-run que imprime resumen antes de conectar a Supabase**, con la llamada de ejecución real comentada por defecto — patrón ya establecido en todos los scripts de carga existentes.
4. **Verificar contra el paper antes de cargar cualquier número relacionado con M1/M2/M3** — regla de oro de §3.3.
5. **Redactar Acta de cierre por feature/tarea completada**, documentando no solo qué se hizo sino qué hallazgos aparecieron en el camino — los hallazgos "menores" de la sesión anterior (pickle desactualizado, gap de M1) resultaron ser los puntos más valiosos para decisiones futuras.
