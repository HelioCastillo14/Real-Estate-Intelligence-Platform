# Feature 1.5.3 — Tabla `amenidades` — Acta de Cierre

**Fecha de ejecución:** 2026-07-15
**Fuente del esquema:** `Ajuste_WBS_1_5_3_Esquema_Amenidades.md`
**Fuente de los datos:** 6 de 7 archivos existentes en `pipeline/data/external/amenidades/` (1 archivo combinado excluido con evidencia, ver §3)

---

## 1. Resultado de la investigación previa — el dato crudo sí persiste

A diferencia de `1.5.5` (ground truth no persistido), aquí **7 archivos reales existen**: 3 JSONL de Google Places (San Francisco, Bella Vista, Costa del Este) y 4 GeoJSON de OSM Overpass (Betania, Parque Lefevre, Pedregal, y un archivo combinado descartado). Esto cambió el carácter de la tarea respecto a lo que el WBS anticipaba — no requirió re-extracción, pero sí reconciliación real antes de cargar.

## 2. Verificación geométrica — regla de CLAUDE.md aplicada sin excepción

`pipeline/zone_health/cruce_espacial_corregimiento.py::asignar_corregimiento()` ya existía, probada (3/3 tests), en uso en `normalizacion_amenidades.py` y `normalizacion_walkability.py` — pero hasta esta sesión solo se había aplicado ad hoc a archivos OSM, no sistemáticamente a los 3 de Google Places (brecha ya anotada en CLAUDE.md). **Se cerró esa brecha:** la función se corrió sobre las 238 filas cargadas, sin excepción de fuente.

**Detección de `fuente` por presencia real de `place_id`, no por nombre de archivo** — validado con el caso ya conocido (1 registro dentro de `amenidades_parque_lefevre_osm.geojson` resultó ser Google Places, migrado de San Francisco, detectado correctamente sin depender del nombre del archivo).

## 3. Decisión de fondo — exclusión del archivo combinado, con evidencia

`amenidades_betania_obarrio_cangrejo_marbella_osm.geojson` (130 features) se excluyó de la carga:

- Ninguna de las 60 claves de `properties` distingue a qué zona corresponde cada punto individualmente — el archivo es una bolsa sin distinción interna, producto de una consulta Overpass con bbox único cubriendo 4 áreas a la vez (confirmado en `LOG_EXTRACCION.md`, sin script de extracción versionado).
- Al aplicar `asignar_corregimiento()` en modo lectura, 123/130 (95%) resolvió a Bella Vista o San Francisco — zonas que ya tienen fuente canónica de mayor calidad (Google Places, descartando OSM explícitamente desde Feature 1.3.7 §4.4). Solo 5 cayeron en Betania, muy por debajo de los 104 del archivo dedicado y re-extraído específicamente para esa zona.

**Consecuencia aceptada:** El Cangrejo, Marbella y Obarrio quedan sin amenidades propias cargadas — no por decisión de diseño, sino porque la extracción real nunca las capturó de forma distinguible por zona. Consistente con que estas 3 zonas ya heredan su Zone Health de Bella Vista sin usar su propia extracción (Feature 1.4.3).

## 4. Hallazgo en ejecución — frontera geográfica real Costa del Este / Parque Lefevre

Al correr `asignar_corregimiento()` sobre las 24 filas de Costa del Este, **13 resolvieron geométricamente a Parque Lefevre**, no a `NULL` como anticipaba el diseño original.

**Confirmado como geografía real, no error de asignación** — `Feature_1_3_7_Extraccion_Amenidades_Acta.md` §5.3 ya documentaba formalmente que una porción del territorio comercialmente conocido como "Costa del Este" cae administrativamente dentro de Parque Lefevre, citando POIs específicos ("Parque costa del este", "The Casco School - Costa del Este") como ejemplos ya identificados. **Los 13 POIs que la carga real produjo incluyen exactamente esos mismos nombres** — confirmación directa de que el hallazgo documentado hace semanas se sostiene con el dato cargado hoy.

**Tratamiento aplicado:** distinto del caso de error de extracción (Parque Lefevre ← San Francisco, 1 fila, ya corregido). Las 13 filas se cargaron con `corregimiento_asignado = 'Parque Lefevre'` (resultado geométrico real) y `zona_etiquetada_origen = 'Costa del Este'` preservado, con `nota_auditoria` citando la Acta 1.3.7 §5.3 explícitamente.

**Consecuencia aceptada, no resuelta en esta Feature:** el Zone Health composite de Parque Lefevre (0.3765, ya cerrado en `1.5.2`) se calculó en Feature 1.4.3 sin estas 13 amenidades — no habían sido cruzadas geométricamente contra ese polígono en ese momento. No se recalculó Zone Health como parte de `1.5.3`. Queda documentado como evidencia disponible para una futura re-auditoría de Feature 1.4 (decisión de gobernanza académica, no técnica).

## 5. Migración de estructura

`supabase/migrations/20260715040003_amenidades_create_table.sql` — aplicada exitosamente. `supabase_migrations.schema_migrations` con 5 versiones registradas, sin re-ejecución de migraciones previas.

| Constraint | Verificado |
|---|---|
| `amenidades_pkey` — `PRIMARY KEY (id)` | ✓ |
| `amenidades_categoria_check` — 6 valores exactos | ✓ |
| `amenidades_fuente_check` — `google_places` / `osm_overpass` | ✓ |
| `amenidades_geom_tipo_origen_check` — `point` / `polygon_centroid` | ✓ |
| `amenidades_corregimiento_asignado_fkey` — FK → `corregimientos(nombre)` | ✓ |
| `idx_amenidades_geom` — GiST sobre `geom` | ✓ |

## 6. Carga de datos — resultado final

Transacción única, verificación previa en seco (dry-run) confirmada idéntica al resultado real antes de ejecutar contra Supabase.

| Zona (`zona_etiquetada_origen`) | Filas |
|---|---|
| San Francisco | 30 |
| Bella Vista | 15 |
| Costa del Este | 24 |
| Betania | 104 |
| Parque Lefevre | 53 |
| Pedregal | 12 |
| **Total** | **238** |

- `corregimiento_asignado = NULL`: 11 (todas Costa del Este — fuera de las 5 zonas oficiales, caso esperado).
- `corregimiento_asignado = 'Parque Lefevre'` desde `zona_etiquetada_origen = 'Costa del Este'`: 13 (frontera geográfica real, §4).
- `fuente`: 69 `google_places`, 169 `osm_overpass`.
- `nota_auditoria` poblada: 14 filas (13 de frontera Costa del Este/Parque Lefevre + 1 de error de extracción corregido Parque Lefevre/San Francisco).

**Verificación independiente contra la tabla real** (no solo el mensaje de confirmación del script): 238 filas totales, distribución por zona coincide exactamente. Sin discrepancias.

## 7. Decisiones confirmadas por esta ejecución (no reabrir)

- **`amenidades` cubre 6 zonas, no 9** — El Cangrejo, Marbella, Obarrio sin cobertura propia, documentado como limitación de datos, no de diseño.
- **`corregimiento_asignado` y `zona_etiquetada_origen` se preservan como campos separados**, sin colapsar — necesario porque pueden divergir, con dos casos reales confirmados en esta carga (1 error de extracción, 13 de geografía real).
- **La brecha de auditoría geométrica sobre archivos Google Places, ya anotada en CLAUDE.md, queda cerrada** — `asignar_corregimiento()` corrió sin excepción sobre las 238 filas.
- **El Zone Health de Parque Lefevre no se recalculó** — las 13 amenidades adicionales quedan como evidencia disponible, no aplicada retroactivamente.

## 8. Pendiente explícito, fuera de alcance de esta Acta

1. **Decisión de gobernanza:** ¿se re-audita el Zone Health composite de Parque Lefevre incorporando las 13 amenidades recién descubiertas? No es una decisión técnica — reabre una feature formalmente cerrada (1.4).
2. **Re-extracción dirigida** de El Cangrejo/Marbella/Obarrio si Épica 5 (frontend) requiere amenidades propias para esas zonas — trabajo de pipeline nuevo, no ajuste de esquema.
3. **Vista/consulta que fusione `hospital`+`clinica` en `salud`** para alimentar un futuro recálculo de Zone Health — no construida aquí, el índice actual ya está cerrado y cargado.

## 9. Estado

**Feature 1.5.3: CERRADA.** Estructura y datos verificados sin discrepancias, con dos hallazgos de datos reales documentados (frontera Costa del Este/Parque Lefevre, brecha de auditoría cerrada) en vez de ocultados detrás de un resultado "limpio".

**Estado consolidado de Feature 1.5 tras esta sesión:**

| Tarea | Estado |
|---|---|
| 1.5.1 | ✓ Cerrada (estructura + 1,177 filas de `propiedades`) |
| 1.5.2 | ✓ Cerrada (estructura + 9 filas de `corregimientos`) |
| 1.5.3 | ✓ Cerrada (estructura + 238 filas de `amenidades`) |
| 1.5.4 | Diseño pendiente (tabla ancha vs. separada para `scores_valuacion`) |
| 1.5.5 | ✓ Cerrada (estructura + 577 filas de `conjunto_referencia_m1`, 6 perfiles) |
| 1.5.6 | Bloqueada por Épica 2 (`2.1.3`, embeddings) |

**4 de 6 tareas cerradas.** Solo `1.5.4` queda con decisión de diseño abierta; `1.5.6` permanece bloqueada por dependencia externa a Feature 1.5.
