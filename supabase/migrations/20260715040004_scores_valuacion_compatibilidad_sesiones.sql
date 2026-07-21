-- 1.5.4 — CREATE TABLE valuacion_quality_scorer, valuacion_semaforo_knn,
-- valuacion_segmento_kmeans, sesiones_consulta, scores_compatibilidad (esquema aprobado)
-- Fuente de la decisión: Context-MD/Ajuste_WBS_1_5_4_Esquema_Scores.md (diseño aprobado
-- 2026-07-15, pendiente de ejecución).
--
-- APLICADA CONTRA SUPABASE — verificado 2026-07-15 (sesión Feature 3.1.6, migración 040006):
-- `supabase migration list` confirma local == remote, las 5 tablas existen realmente. Esta línea
-- decía "NO EJECUTADA... requiere confirmación" y era falsa — corregida como parte de una
-- auditoría completa de encabezados de migración, ver CLAUDE.md para el resto de hallazgos de
-- esa sesión. `valuacion_semaforo_knn` recibió 2 columnas adicionales
-- (`confianza_reducida`, `n_comparables`) en `20260715040006_valuacion_semaforo_knn_agrega_
-- confianza.sql`, antes de que corriera su primer batch de carga (3.1.6) — este archivo sigue
-- siendo la fuente de las 5 columnas originales, no se reescribe aquí.
--
-- Orden de creación fijado por dependencias de FK: sesiones_consulta debe existir antes que
-- scores_compatibilidad, que la referencia (§4-5 del documento de diseño). Las 3 tablas de
-- valuación (Quality Scorer, KNN, KMeans) van primero porque no dependen entre sí, solo de
-- propiedades(listing_id) (1.5.1, ya creada).
--
-- Estado de datos al momento de esta migración (§1 del documento de diseño): únicamente
-- valuacion_quality_scorer recibe carga real en esta sesión (pipeline/scripts/
-- cargar_valuacion_quality_scorer.py). Las otras 4 tablas quedan vacías — batches/scripts de
-- producción de KNN (3.1.6), KMeans (3.2.5), M1 (2.2.3 en pipeline/) y M3 en tráfico real
-- todavía no existen. Vacías es el estado esperado, no un error.

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
-- Vacía hasta que M3 corra en tráfico real. Los 20 registros de
-- medicion_final_6_2_7_checkpoint.pkl son consultas de prueba, no tráfico de producción —
-- deliberadamente no cargados (documento de diseño §5, pendiente §8.4).

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
-- Vacía hoy — no existe ningún script de producción de M1 que calcule esto, ni siquiera
-- para los 6 perfiles de conjunto_referencia_m1 (el Precision@k de 6.2.3 se calculó en
-- notebook, sin persistir los scores individuales, solo las métricas agregadas).
