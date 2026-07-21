# Gobernanza — REIP_WBS.xlsx vs. cierres de Feature 6.2

1. `REIP_WBS.xlsx` es un snapshot del plan ORIGINAL, escrito antes de que Feature 6.2 ejecutara y
   generara decisiones basadas en datos reales. NUNCA se lee como estado actual del sistema sin
   cruzarlo primero contra el cierre de notebook correspondiente (`Feature_6_2_X_*_Cierre.md`).

2. **Regla de precedencia:** si una tarea del WBS describe algo que contradice lo que un cierre de
   notebook documenta para esa misma área, el cierre de notebook gana — el WBS queda como registro
   histórico de la intención original, no como especificación vigente.

3. Discrepancias entre WBS y lo ejecutado en Feature 6.2:

   - **2.2.3 — Pesos del scorer híbrido de M1**
     - **Estado:** RESUELTA
     - **Fecha:** 2026-07-14
     - **WBS decía:** 0.6 semántico / 0.4 estructurado.
     - **Se ejecutó:** 0.6 estructurado / 0.4 semántico (cerrado en 6.2.3, sin cambios).
     - **Evidencia:** sweep de pesos invertidos,
       `pipeline/models/sweep_pesos_invertidos_2_2_3_wbs_vs_6_2_3.pkl` — la configuración del WBS
       (0.6 semántico/0.4 estructurado) pierde o empata en Precision@3/5/10 sobre los 6 perfiles,
       sin ganar en ninguno. El daño se concentra en `retirado_tranquilidad` e
       `inversionista_renta_corta` (los dos perfiles con lift semántico positivo en 6.2.3);
       `profesional_joven` no mejora ni empeora, confirmando que su problema es de interacción con
       la regla de exclusión por keyword, no de magnitud del peso semántico (consistente con 6.2.3
       §9.3).
     - **Por qué gana la versión ejecutada:** domina o empata en las 3 métricas sobre los 6
       perfiles — no hay evidencia empírica a favor del peso del WBS en ningún caso.
     - Corrección aplicada al texto/intención de la tarea 2.2.3 del WBS, no a `REIP_WBS.xlsx`
       directamente, que queda intacto como registro histórico (regla 2 de este documento).

   - **3.1.1 — Comparables de M2 (Property Valuation Engine)**
     - **Estado:** RESUELTA
     - **Fecha:** 2026-07-14
     - **WBS decía:** comparables vía `ST_Distance` de PostGIS, sobre coordenadas de punto reales
       para las propiedades del catálogo.
     - **Se ejecutó:** comparables por coincidencia de `corregimiento` + `tipo_inmueble`, ordenados
       por similitud de atributos estructurados (m², habitaciones), vía
       `sklearn.neighbors.KNeighborsRegressor` — sin componente geoespacial.
     - **Evidencia:** `Context-MD/Feature 1.2 — Pipeline de scraping _ Acta.md`, §"Decisión 1 —
       Redefinición de 'comparable' para M2" — verificación manual directa confirmó que
       inmopanama.com no expone coordenadas reales, mapa embebido ni iframe en ninguna página de
       detalle; el diseño original de 3.1.1 era inejecutable tal como estaba escrito,
       independientemente de cualquier geocoding externo.
     - **Por qué gana la versión ejecutada:** el diseño del WBS depende de un insumo (coordenadas
       reales) que la fuente de datos nunca tuvo — no es una preferencia de diseño, es la única
       opción ejecutable con los datos reales disponibles. Además simplifica el stack (ya no
       requiere la consulta geoespacial PostGIS+pgvector prevista en 1.5.6 para este componente).
     - Solo corrección de texto de la tarea 3.1.1 en el documento de gobernanza — no bloqueante,
       la arquitectura real ya está en producción desde Feature 1.2.

   - **3.2.2 / 3.2.4 — k de KMeans (segmentación de mercado, M2)**
     - **Estado:** RESUELTA
     - **Fecha:** 2026-07-14
     - **WBS decía:** k=5 clusters.
     - **Se ejecutó:** k=2 clusters.
     - **Evidencia:** `Context-MD/Feature_6_2_5_M2_KMeans_Cierre.md` — k probado de 2 a 10 (método
       del codo + Silhouette); k óptimo=2, Silhouette=0.388. Dos segmentos: compacto/económico
       (662, mediana \$270K/92m²) y grande/premium (380, mediana \$736K/300m²).
     - **Por qué gana la versión ejecutada:** k=2 es el óptimo medido por Silhouette sobre el
       dataset real — k=5 del WBS era una suposición de diseño previa a tener el dato, ya
       reemplazada por una medición formal.
     - Solo corrección de texto ("5 clusters" → "2 clusters") en las tareas 3.2.2/3.2.4 del
       documento de gobernanza — la desviación ya estaba documentada formalmente en el cierre de
       6.2.5, esto solo la refleja aquí.

   - **3.4.1 — Dimensiones del Quality Scorer (M2)**
     - **Estado:** RESUELTA
     - **Fecha:** 2026-07-14
     - **WBS decía:** completitud, especificidad, confiabilidad, utilidad.
     - **Se ejecutó:** completitud informativa, calidad de presentación/redacción,
       diferenciadores/amenidades, transparencia de precio (cerrado en 6.2.6).
     - **Evidencia:** `Context-MD/Feature_6_2_6_M2_QualityScorer_Cierre.md` — las 4 dimensiones
       ejecutadas, con rúbrica explícita 1-5 por dimensión, prompt v2 validado (100% de parseo
       contra el esquema, muestra n=150).
     - **Por qué gana la versión ejecutada:** decisión explícita del usuario (2026-07-14) — se
       mantienen las 4 dimensiones ya cerradas y validadas en 6.2.6 en vez de retomar las del WBS
       original. No es una equivalencia 1:1 verificada entre ambas listas, es una decisión de
       producto que prioriza la versión ya ejecutada y medida sobre la especificación original.
     - Ambas listas quedan documentadas lado a lado arriba para trazabilidad de qué se descartó.

   - **1.5.1 — Condición de Done (esquema completo de la tabla `propiedades`)**
     - **Estado:** RESUELTA
     - **Fecha:** 2026-07-15
     - **WBS decía:** *"Implementar tabla `propiedades` con columna `geom` (Point/PostGIS) y
       `embedding` (vector/pgvector) + índice GiST y HNSW"*, remitiendo a `DOC-05 §4.2` para el
       resto de columnas/tipos/constraints de la tabla.
     - **Se ejecutó (aprobado, no ejecutado contra Supabase todavía):** `DOC-05 §4.2` no existe en
       este repo — búsqueda confirmada sin resultado. La Condición de Done queda formalmente
       reemplazada por el esquema derivado de fuentes reales y verificadas en
       `Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md` (versión final, aprobada 2026-07-15):
       columnas del catálogo real (`pipeline/data/processed/catalogo_residencial_limpio_6_2_1.csv`,
       header leído directamente), `embedding vector(3072)` (Feature 1.5b, ya cerrada), `geom`
       explícitamente documentado como aproximación sintética de visualización (no coordenada
       real), PK `listing_id` (`bigint`, no `listing_url`), Condición de Done separada en
       verificación inmediata (tabla + CHECK de `corregimiento` + índice GiST) vs. diferida
       (índice HNSW, después de 1.5.6), y coordinación cruzada explícita con 1.5.4
       (`scores_valuacion`, FK contra `listing_id`) y 1.5.2 (`corregimientos`, CHECK inmediato +
       FK condicionada al número de filas que defina esa tabla).
     - **Evidencia:** `Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md` §1 (por qué `DOC-05
       §4.2` no puede seguir siendo la fuente de la Condición de Done), §2 (esquema), §3 (PK), §4
       (Condición de Done ajustada), §5/§6/§7 (coordinación cruzada con 1.5b, 1.5.4 y 1.5.2).
     - **Por qué gana la versión ejecutada:** la Condición de Done original depende de una fuente
       que no existe en el repo — tal como estaba escrita, 1.5.1 no se podía cerrar nunca. El
       esquema de reemplazo deriva exclusivamente de fuentes verificables dentro del repo (catálogo
       real, Feature 1.5b ya cerrada, decisiones formales ya cerradas de `CLAUDE.md` sobre `geom`
       sintético y comparables de M2), no de una suposición nueva.
     - Corrección aplicada al texto/intención de la tarea 1.5.1 del WBS, no a `REIP_WBS.xlsx`
       directamente, que queda intacto como registro histórico (regla 2 de este documento). El
       `CREATE TABLE` real contra Supabase sigue sin ejecutarse — acción sobre infraestructura
       compartida, pendiente de confirmación explícita separada en el momento de aplicarlo.

4. Ante cualquier tarea nueva del WBS que no aparezca en esta lista: si vas a citarla como base de
   una decisión, verifica primero si existe un cierre de Feature 6.2.x que la contradiga antes de
   asumir que el WBS describe el estado actual.

5. **Recordatorio operativo — 1.5.1, CERRADO por la entrada de la sección 3 (2026-07-15).** Este
   recordatorio quedó abierto mientras 1.5.1 no tenía esquema aprobado; ya no aplica como bloqueo.
   La Condición de Done de **1.5.1** (`REIP_WBS.xlsx`, hoja `1.0 Infraestructura y Datos`:
   *"Implementar tabla `propiedades` con columna `geom` (Point/PostGIS) y `embedding`
   (vector/pgvector) + índice GiST y HNSW"*) queda formalmente reemplazada por
   `Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md` — ver la entrada "1.5.1" en la sección 3.
   La coordinación entre la columna `embedding` (Feature 1.5b,
   `supabase/migrations/20260715032111_propiedades_embedding.sql`) y el `CREATE TABLE` principal ya
   no es una nota abierta suelta: quedó resuelta dentro de §5 del documento de ajuste (Opción A/B),
   y `Context-MD/Nota_Pendiente_Migracion_Embedding_1_5.md` se cierra cuando se ejecute el
   `CREATE TABLE` real y quede registrado cuál opción se usó.

No se toca `REIP_WBS.xlsx` — queda intacto como registro histórico.

---

**Cierre de este documento (2026-07-14):** las 4 discrepancias identificadas entre `REIP_WBS.xlsx`
y lo ejecutado en Feature 6.2 (2.2.3, 3.1.1, 3.2.2/3.2.4, 3.4.1) quedan RESUELTAS, cada una con su
evidencia citada. La regla de precedencia (sección 2) y la regla de verificación de nuevas citas
(sección 4) siguen vigentes para cualquier discrepancia futura que se identifique.

**Actualización (2026-07-15):** se agrega una quinta entrada RESUELTA — **1.5.1**, cuya Condición
de Done original remitía a `DOC-05 §4.2` (documento inexistente en el repo) queda formalmente
reemplazada por `Context-MD/Ajuste_WBS_1_5_1_Esquema_Propiedades.md` (versión final aprobada). El
recordatorio operativo de la sección 5 (coordinación 1.5b/1.5.1), que estaba ABIERTO, se cierra con
esta misma actualización — ver texto revisado de la sección 5. No quedan discrepancias ni
recordatorios pendientes de decisión en este documento a esta fecha. El `CREATE TABLE propiedades`
real contra Supabase sigue sin ejecutarse — pendiente de confirmación explícita separada.
