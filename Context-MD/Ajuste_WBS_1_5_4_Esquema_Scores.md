# Ajuste WBS — Feature 1.5.4: Esquemas de `scores_valuacion`, `scores_compatibilidad`, `sesiones_consulta`

**Fecha:** 2026-07-15
**Estado:** Diseño aprobado — pendiente de ejecución
**Fuente de las decisiones:** `Ajuste_WBS_1_5_1_Esquema_Propiedades.md` §6 (regla de FK vía `listing_id`) + verificación de artifacts reales en esta sesión + `Feature_6_2_7_M3_Orchestration_Cierre.md` + `notebooks/05_m3_nlp_orchestration.ipynb`

---

## 1. Resultado de la investigación — tres fuentes en tres estados muy distintos

| Fuente | Artifact de producción | Estado hoy |
|---|---|---|
| Quality Scorer (M2) | `pipeline/models/quality_scores_produccion_final.pkl/.csv` | **Completo, listo para cargar** — 1,168/1,177 evaluadas |
| Semáforo KNN (M2) | `pipeline/models/knn_semaforo_precio_6_2_4.pkl` | Modelo entrenado, batch (`3.1.6`) no corrido — **nada que cargar hoy** |
| Segmento KMeans (M2) | `pipeline/models/kmeans_segmentacion_6_2_5.pkl` | Modelo entrenado, batch (`3.2.5`) no corrido — **nada que cargar hoy** |
| Compatibilidad (M1) | — | **No existe ningún script de producción**, ni siquiera un `.pkl` — solo código de notebook. El explainer (`2.2.4`) tampoco existe ni como placeholder (confirmado contra `WBS_Pendiente_Epicas_2_3_4.md`) |
| Sesiones (M3) | Contrato Pydantic verificado en `05_m3_nlp_orchestration.ipynb` | Contrato real confirmado, con output de ejemplo — **estructura lista, sin datos de producción cargables hoy** (los 20 registros de medición final son de prueba, no tráfico real) |

**Consecuencia de diseño:** las 3 tablas se crean hoy con estructura completa. Solo `scores_valuacion` (fuente Quality Scorer) recibe datos reales en esta sesión. Las demás quedan vacías, listas para recibir datos cuando sus respectivos batches/scripts existan — mismo patrón ya usado con `embedding`/`geom` en `propiedades`.

## 2. Decisión — tablas separadas por fuente, no una tabla ancha

Confirmado el mismo criterio aplicado en `1.5.5` (`perfiles_lifestyle` separada de `conjunto_referencia_m1`): Quality Scorer, KNN y KMeans tienen **ciclos de vida y payloads estructuralmente distintos** (4 enteros + categórico vs. semáforo categórico + numérico vs. entero de cluster). Forzarlos en una tabla ancha implica columnas `NULL` por diseño para 2 de 3 fuentes en cualquier fila, y lógica de `UPSERT` en vez de `INSERT` cuando los batches futuros corran. Se crean 3 tablas bajo el paraguas conceptual de "valuación", no una.

## 3. Esquema — `scores_valuacion` (3 tablas)

```sql
create table if not exists valuacion_quality_scorer (
    listing_id                    bigint primary key references propiedades(listing_id),
    modelo                        text not null,
    -- gemini-3.5-flash | gemini-3.1-flash-lite — preservar cuál evaluó cada fila,
    -- no colapsar (ya decidido en Escalamiento_QualityScorer_Produccion_Cierre.md).
    completitud_informativa       smallint not null check (completitud_informativa between 1 and 5),
    calidad_presentacion          smallint not null check (calidad_presentacion between 1 and 5),
    diferenciadores_amenidades    smallint not null check (diferenciadores_amenidades between 1 and 5),
    transparencia_precio          smallint not null check (transparencia_precio between 1 and 5),
    fecha_carga                   timestamp not null default now()
);

comment on column valuacion_quality_scorer.transparencia_precio is
    'Distribución bimodal documentada (27% en score=1, 64% en score=5) — causa real: '
    'el precio existe como dato estructurado pero no se menciona en el texto del '
    'anuncio. Nota pendiente de UX: aclarar en frontend que un score bajo aquí no '
    'implica un precio sospechoso. Ver Escalamiento_QualityScorer_Produccion_Cierre.md §3.1.';

create table if not exists valuacion_semaforo_knn (
    listing_id           bigint primary key references propiedades(listing_id),
    precio_predicho       numeric not null,
    categoria_semaforo    text not null check (categoria_semaforo in ('verde', 'amarillo', 'rojo')),
    mae_referencia        numeric not null,
    multiplo_mae          numeric not null default 1.5,
    fecha_carga           timestamp not null default now()
);
-- Vacía hasta que el batch 3.1.6 corra. mae_referencia y multiplo_mae se guardan POR FILA
-- (no en una tabla de configuración aparte) para que cada score sea auditable de forma
-- autosuficiente incluso si el umbral se recalibra en el futuro — mismo criterio de
-- congelamiento ya aplicado en 1.5.5 con corregimientos_resueltos_al_materializar.

create table if not exists valuacion_segmento_kmeans (
    listing_id      bigint primary key references propiedades(listing_id),
    cluster_id       smallint not null check (cluster_id in (0, 1)),
    fecha_carga      timestamp not null default now()
);
comment on column valuacion_segmento_kmeans.cluster_id is
    'Entero crudo del modelo (0/1), SIN interpretación embebida ("premium"/"económico") '
    '— esa interpretación no está codificada en ningún artifact del proyecto, es prosa '
    'post-hoc. Si se necesita una etiqueta legible, debe vivir en una tabla de metadata '
    'separada (cluster_id -> nombre, fecha_asignada), nunca como string en esta tabla, '
    'para no congelar una interpretación que podría invalidarse si KMeans se recalcula.';
-- Vacía hasta que el batch 3.2.5 corra.
```

## 4. Esquema — `scores_compatibilidad` (M1)

```sql
create table if not exists scores_compatibilidad (
    id                    bigserial primary key,
    listing_id            bigint not null references propiedades(listing_id),
    perfil_lifestyle       text references perfiles_lifestyle(perfil),
    -- NULL cuando el score proviene de una sesión de búsqueda ad-hoc (M3), no de uno
    -- de los 6 perfiles de referencia de 6.2.3.
    sesion_id              bigint references sesiones_consulta(id),
    -- NULL cuando el score proviene de una evaluación batch contra perfiles_lifestyle,
    -- no de una consulta de usuario en vivo.

    score_final            numeric not null,
    score_estructurado     numeric not null,
    score_semantico        numeric not null,
    peso_estructurado      numeric not null default 0.6,
    peso_semantico         numeric not null default 0.4,
    -- Guardado POR FILA, no asumido fijo permanentemente — M1 no tiene ningún artifact
    -- serializado en producción (a diferencia de KNN/KMeans), los pesos son constantes
    -- de notebook (PESO_ESTRUCTURADO/PESO_SEMANTICO) sin mecanismo de versionado. Si
    -- se recalibran en el futuro, cada score sigue siendo auditable con el peso real
    -- que se usó al calcularlo.

    explicacion             text,
    -- Reservado para el explainer de 2.2.4 (criterios cumplidos/no cumplidos) — NO
    -- existe ninguna implementación todavía, ni siquiera placeholder (confirmado
    -- contra WBS_Pendiente_Epicas_2_3_4.md). Columna nullable, lista para cuando
    -- exista la lógica, no forzada a poblarse hoy.

    fecha_calculo           timestamp not null default now(),

    constraint chk_scores_compatibilidad_origen check (
        (perfil_lifestyle is not null and sesion_id is null) or
        (perfil_lifestyle is null and sesion_id is not null)
    )
    -- Un score viene de UN origen: perfil de referencia batch, o sesión de usuario en
    -- vivo — nunca ambos, nunca ninguno.
);
```

**Vacía hoy** — no existe ningún script de producción de M1 que calcule esto, ni siquiera para los 6 perfiles de `conjunto_referencia_m1` (el Precision@k de `6.2.3` se calculó en notebook, sin persistir los scores individuales, solo las métricas agregadas).

## 5. Esquema — `sesiones_consulta` (M3)

```sql
create table if not exists sesiones_consulta (
    id                    bigserial primary key,
    consulta_texto         text not null,
    extraccion             jsonb not null,
    -- Contrato Pydantic completo verificado contra 05_m3_nlp_orchestration.ipynb:
    -- es_consulta_inmobiliaria (bool), zona (str|null), zona_mencion_texto (str|null),
    -- tipo_inmueble (str|null), precio_min (float|null), precio_max (float|null),
    -- habitaciones_min (int|null), banos_min (int|null),
    -- caracteristicas_cualitativas (list), confianza (float), razon_confianza (str).
    -- Guardado como jsonb, no columnas individuales — mismo criterio que
    -- propiedades_raw en amenidades: preserva fidelidad si el contrato evoluciona,
    -- sin forzar migraciones de esquema por cada campo nuevo que M3 agregue.

    categoria_resultado    text not null
        check (categoria_resultado in ('exito', 'fallback_fuera_tema', 'fallback_cobertura', 'fallback_ambiguedad')),
    -- 4 categorías reales, confirmadas tanto en clasificar_resultado() como en los
    -- 20 registros de medición final — las 4 aparecen efectivamente, no solo como
    -- valores posibles en el código.

    confianza               numeric not null,
    -- Extraído también como columna propia (no solo dentro de extraccion jsonb) para
    -- permitir análisis directo de calibración del umbral (0.65) sin deserializar
    -- JSON en cada consulta — es el campo que más se va a filtrar/agregar.

    modelo_usado            text not null default 'gemini-3.1-flash-lite',
    -- Distinto del modelo de Quality Scorer — no confundir en consultas futuras.

    fecha_sesion            timestamp not null default now()
);

create index if not exists idx_sesiones_consulta_categoria on sesiones_consulta (categoria_resultado);
```

**Vacía hoy** — los 20 registros de `medicion_final_6_2_7_checkpoint.pkl` son consultas de prueba diseñadas para medición (Sección IV-A6 del paper), no tráfico real de producción. Cargarlos como si fueran sesiones reales contaminaría cualquier análisis futuro de tasa de fallback en producción real — se dejan fuera, documentado como decisión explícita.

## 6. Verificación contra el paper — antes de cualquier carga futura

**Regla explícita para esta feature, dado que el paper ya es versión final:** ninguna carga de datos en estas 3 tablas debe alterar, y ninguna corrección de artifact (ej. el `.pkl` de KNN con `umbral_semaforo` desactualizado) debe aplicarse retroactivamente a ningún número ya reportado. Verificado: el paper (Sección IV-A3) ya usa el umbral correcto (±1.5×MAE, ±$281,315) — coincide exactamente con la lógica real del notebook, no con el valor obsoleto del `.pkl`. La corrección del `.pkl` pendiente (§7) es trabajo de infraestructura para el futuro batch `3.1.6`, sin efecto sobre el paper.

## 7. Checkpoint de cierre de 1.5.4

- [ ] 5 migraciones (`valuacion_quality_scorer`, `valuacion_semaforo_knn`, `valuacion_segmento_kmeans`, `scores_compatibilidad`, `sesiones_consulta`) ejecutadas contra Supabase
- [ ] `valuacion_quality_scorer` cargada con 1,168 filas desde `quality_scores_produccion_final.pkl/.csv`
- [ ] `valuacion_semaforo_knn`, `valuacion_segmento_kmeans`, `scores_compatibilidad`, `sesiones_consulta` creadas y verificadas estructuralmente, permanecen vacías — documentado como estado esperado, no error
- [ ] Verificación cruzada: conteo de `valuacion_quality_scorer` coincide con Cuadro IX/X del paper (n=1,168) — mismo número, no recalculado

## 8. Pendiente explícito, fuera de alcance de 1.5.4

1. Corrección del `.pkl` de KNN (`mae_knn_test` y `multiplo_mae=1.5` no persistidos, solo `umbral_semaforo=0.1` desactualizado) — necesaria antes de que corra el batch `3.1.6`, sin efecto sobre el paper ya escrito.
2. Implementación real del scorer de M1 en producción (`pipeline/`, no solo notebook) — prerequisito real para poblar `scores_compatibilidad`.
3. Implementación del explainer (`2.2.4`) — prerequisito para poblar `scores_compatibilidad.explicacion`.
4. Decisión de si los 20 registros de medición final de M3 se cargan alguna vez a `sesiones_consulta` con un flag distintivo (`es_medicion_prueba`), o si se mantienen exclusivamente en el `.pkl` de checkpoint — no resuelto aquí.
