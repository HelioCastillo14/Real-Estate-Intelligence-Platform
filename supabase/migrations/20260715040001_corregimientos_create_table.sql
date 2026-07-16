-- 1.5.2 — CREATE TABLE corregimientos (esquema aprobado)
-- Fuente de la decisión: Context-MD/Ajuste_WBS_1_5_2_Esquema_Corregimientos.md §3 (diseño
-- aprobado 2026-07-15, pendiente de ejecución).
--
-- NO EJECUTADA CONTRA SUPABASE. Acción sobre infraestructura compartida — requiere confirmación
-- explícita del usuario en el momento de aplicarla (no basta con este archivo existiendo en el
-- repo). Preparada para revisión, no para correr automáticamente. Mismo protocolo que
-- 20260715040000_propiedades_create_table.sql (1.5.1).
--
-- Decisión de fondo (§1): 9 filas, no 5 — las 9 zonas del scope de negocio de REIP, no solo
-- los 5 corregimientos administrativos oficiales. Ver §1 para la justificación completa.
--
-- Requiere la extensión PostGIS ya habilitada (compartida con propiedades.geom).

create table if not exists corregimientos (
    -- Identidad
    nombre                  text primary key,
    es_oficial              boolean not null,
    -- TRUE: San Francisco, Bella Vista, Parque Lefevre, Betania, Pedregal
    -- FALSE: El Cangrejo, Marbella, Obarrio, Costa del Este

    -- Geometría — polígono REAL (shapefile STRI/HDX, Feature 1.3.1, cerrada).
    -- Distinto del geom SINTÉTICO de propiedades — no aplicar esa nota aquí.
    geom                    geometry(Polygon, 4326),
    -- NULL para las 4 zonas no oficiales (heredan visualización del padre en capa de
    -- presentación, vía hereda_de — no se duplica el polígono en esta tabla).

    -- Herencia — self-referencing FK, NULL para corregimientos oficiales Y para
    -- Costa del Este (caso especial: no oficial, sin padre confiable).
    hereda_de               text references corregimientos(nombre),

    -- Zone Health Composite Index (Feature 1.4, cerrada 2026-07-09)
    zone_health_score       numeric,
    -- NULL únicamente para Costa del Este.

    desglose_dimensiones    jsonb,
    -- {"seguridad": ..., "transporte": ..., "amenidades": ..., "walkability": ...}
    -- 4 dimensiones (no 5 — socioeconómico eliminado en 1.4.5, peso redistribuido).
    -- NULL únicamente para Costa del Este.

    estado_zone_health      text not null default 'calculado'
        check (estado_zone_health in ('calculado', 'sin_score_datos_insuficientes')),
    -- 'sin_score_datos_insuficientes' únicamente para Costa del Este.

    no_visualizado          boolean not null default false,
    -- TRUE únicamente para Pedregal. Distinto de estado_zone_health: Pedregal SÍ
    -- tiene composite calculado, solo se excluye de la visualización de frontend
    -- (Feature 5.x). No confundir con el caso de Costa del Este.

    motivo_visualizacion    text
    -- Poblado solo cuando no_visualizado = TRUE. Texto libre, sin CHECK a propósito
    -- — mismo criterio que enriquecimiento_error_detalle en propiedades (1.5.1): no
    -- es un conjunto cerrado de valores, es explicación de caso. Fuente real (JSON
    -- de origen) documenta que la exclusión de Pedregal sigue PENDIENTE DE
    -- VALIDACIÓN FORMAL del consejo académico — a diferencia de la exclusión de
    -- KNN/KMeans, que sí tuvo esa validación (Acta de 1.2, sesión 2026-07-08).
);

comment on column corregimientos.hereda_de is
    'Self-referencing FK. NULL para los 5 corregimientos oficiales Y para Costa del '
    'Este (caso especial sin padre confiable). Para las 3 zonas restantes no '
    'oficiales (El Cangrejo, Marbella, Obarrio), apunta a Bella Vista. Ver es_oficial '
    'para distinguir "oficial" de "no oficial sin herencia". Fuente: Feature 1.4 §7.';

comment on column corregimientos.geom is
    'Polígono REAL (shapefile STRI/HDX, Feature 1.3.1). NULL para las 4 zonas no '
    'oficiales — la resolución de qué polígono mostrar para una zona heredada vive '
    'en la capa de presentación (Épica 5), no se duplica el polígono aquí. '
    'Distinto del geom sintético de propiedades — no aplicar esa nota en esta tabla.';

comment on column corregimientos.estado_zone_health is
    'calculado: la zona tiene composite y desglose, propio o heredado. '
    'sin_score_datos_insuficientes: únicamente Costa del Este — 4 de 5 dimensiones '
    'originales carecen de datos reales y no hay padre confiable del cual heredar.';

comment on column corregimientos.motivo_visualizacion is
    'Explicación de por qué no_visualizado = TRUE, texto libre sin CHECK. Único '
    'caso actual: Pedregal (cobertura de amenidades insuficiente, 12 POIs vs. '
    '32-52 promedio del resto de zonas). NOTA DE GOBERNANZA: esta exclusión sigue '
    'pendiente de validación formal con el consejo académico — a diferencia de la '
    'exclusión de KNN/KMeans, que sí la tuvo (Acta de 1.2, sesión 2026-07-08).';

-- Índice GiST sobre geom — mismo criterio que idx_propiedades_geom (1.5.1). Solo 5 de 9 filas
-- tendrán geom no nulo (corregimientos oficiales), pero el índice no requiere volumen mínimo.
create index if not exists idx_corregimientos_geom
    on corregimientos using gist (geom);
