-- 1.5.5 — CREATE TABLE perfiles_lifestyle y conjunto_referencia_m1 (esquema aprobado)
-- Fuente de la decisión: Context-MD/Ajuste_WBS_1_5_5_Esquema_ConjuntoReferenciaM1.md §2 (diseño
-- aprobado 2026-07-15, pendiente de ejecución).
--
-- APLICADA CONTRA SUPABASE — verificado 2026-07-15 (sesión Feature 3.1.6, migración 040006):
-- `supabase migration list` confirma local == remote, `perfiles_lifestyle` con 6 filas y
-- `conjunto_referencia_m1` con 577 filas reales. Esta línea decía "NO EJECUTADA... requiere
-- confirmación" y era falsa — corregida como parte de una auditoría completa de encabezados de
-- migración, ver CLAUDE.md para el resto de hallazgos de esa sesión.
--
-- Decisión de fondo (§1): ground truth de Feature 6.2.3 CONGELADO (no recalculado
-- dinámicamente) — preserva la validez comparativa del Precision@k ya aprobado (CP-2).
-- Dos tablas, no una tabla ancha con array de listing_id (§3): permite FK real hacia
-- propiedades.listing_id y consultas directas "¿en qué perfiles aparece esta propiedad?".
--
-- Requiere que la tabla propiedades (1.5.1) ya exista — conjunto_referencia_m1.listing_id
-- referencia propiedades.listing_id.

create table if not exists perfiles_lifestyle (
    perfil                    text primary key,
    -- familia_con_ninos, profesional_joven, pareja_presupuesto_medio,
    -- inversionista_renta_corta, retirado_tranquilidad, presupuesto_ajustado_sin_auto

    reglas_estructurales      jsonb not null,
    -- {"corregimientos": [...] | "dinamico_zone_health_composite_min": 0.5,
    --  "corregimientos_resueltos_al_materializar": [...],  -- SOLO para perfiles con
    --  criterio dinámico (ver nota abajo)
    --  "price_min": ..., "price_max": ..., "bedrooms_min": ..., "bedrooms_max": ...,
    --  "area_min": ...}
    -- Nota: pareja_presupuesto_medio usa un criterio DINÁMICO (corregimientos con
    -- composite >= 0.5, no una lista fija). Se guarda AMBAS cosas: la regla dinámica
    -- (para que quede claro cómo se derivó) Y la lista resuelta al momento de
    -- materializar (para que el perfil sea auditable sin depender de que
    -- corregimientos.zone_health_score no cambie en el futuro). Sin la lista
    -- resuelta, este único perfil quedaría con trazabilidad más débil que los otros
    -- 5 — rompería la garantía de congelamiento que justifica toda esta tabla.

    criterio_cualitativo      jsonb not null,
    -- {"incluye": [...], "excluye": [...]} sobre `descripcion`, aplicado junto con
    -- `descripcion_fuente != 'ninguna'`.

    n_solo_estructural        integer not null,
    -- Conteo antes de aplicar el filtro cualitativo — preservado para trazabilidad
    -- del efecto de cada capa de filtro (ya reportado en 6.2.3 §4).

    n_ground_truth            integer not null,
    -- Conteo final (estructural + cualitativo) — debe coincidir con
    -- count(*) de conjunto_referencia_m1 para este perfil (constraint de aplicación,
    -- no de BD — ver §4).

    hash_catalogo_fuente      text not null,
    fecha_materializacion     timestamp not null
    -- Trazabilidad de versión: contra qué snapshot exacto de propiedades se generó
    -- este ground truth. Si el catálogo cambia sustancialmente, este campo permite
    -- confirmar si el ground truth sigue siendo válido o requiere re-materialización.
);

create table if not exists conjunto_referencia_m1 (
    perfil              text not null references perfiles_lifestyle(perfil),
    listing_id          bigint not null references propiedades(listing_id),
    flag_sintetico       boolean not null default true
        check (flag_sintetico = true),
    -- Constraint fijo por diseño (WBS original) — este conjunto nunca se mezcla con
    -- datos de usuario real. TRUE siempre, forzado explícitamente.

    primary key (perfil, listing_id)
);

comment on column perfiles_lifestyle.reglas_estructurales is
    'Filtros estructurales exactos de la celda 7 del notebook 01_m1_preference_matching.ipynb. '
    'Copia literal de la lógica ya cerrada en Feature 6.2.3 — no reinterpretar.';

comment on column perfiles_lifestyle.hash_catalogo_fuente is
    'SHA-256 de catalogo_residencial_limpio_6_2_1.csv al momento de materializar. '
    'Permite confirmar si este ground truth sigue correspondiendo al catálogo vigente.';

comment on table conjunto_referencia_m1 is
    'Ground truth CONGELADO (no recalculado dinámicamente) — preserva la validez '
    'comparativa del Precision@k ya aprobado en Feature 6.2.3 (CP-2). Fuente: '
    'pipeline/data/processed/conjunto_referencia_m1_6_2_3.json.';
